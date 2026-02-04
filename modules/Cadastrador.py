import os
import time
import json
import keyboard  
import sys
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException


# ==============================================================================
# CONFIGURAÇÕES (CONSTANTES)
# ==============================================================================
DELAY_PADRAO = 0.5
CAMINHO_PROJETO = os.getcwd()
CAMINHO_PERFIL = os.path.join(CAMINHO_PROJETO, "Perfil_Bot_Shopee")
ARQUIVO_MAPA = "mapa_global.json"

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def sanitarizar_nome(nome):
    """Remove caracteres proibidos (Igual ao Processador)"""
    return re.sub(r'[<>:"/\\|?*]', '', nome).strip()

def encontrar_imagem_no_disco(produto, variacao, imagem_obj):
    """
    Tenta encontrar a imagem processada usando o processed_path OU calculando o nome.
    """
    # 1. Tenta pelo caminho gravado no JSON (Cenário Ideal)
    caminho_json = imagem_obj.get('processed_path')
    if caminho_json and os.path.exists(caminho_json):
        return os.path.abspath(caminho_json)

    # 2. Se falhou, vamos calcular onde o Processador deveria ter salvado
    # Base: ./images/processadas / NomeColecao
    nome_colecao = sanitarizar_nome(produto.get('collection_name', 'Geral'))
    pasta_colecao = os.path.join(os.getcwd(), "images", "processadas", nome_colecao)
    
    # Se a pasta da coleção nem existe, aborta
    if not os.path.exists(pasta_colecao):
        return None

    # Recalcula o nome do arquivo (Mesma lógica do Organizador/Processador)
    nome_prod_safe = sanitarizar_nome(produto['product_name'])
    nome_var_safe = sanitarizar_nome(variacao['variation_name'])
    tipo_visao = imagem_obj['view_type']
    
    # Lógica de Nomenclatura
    if nome_var_safe.lower() in ["padrão", "padrao", "default", "standard"]:
        nome_arquivo = f"{nome_prod_safe} - {tipo_visao}.jpg"
    else:
        nome_arquivo = f"{nome_prod_safe} - {nome_var_safe} - {tipo_visao}.jpg"
        
    caminho_calculado = os.path.join(pasta_colecao, nome_arquivo)
    
    if os.path.exists(caminho_calculado):
        return caminho_calculado
        
    return None

def verificar_parada():
    """Verifica se a tecla de emergência (ESC) foi pressionada."""
    if keyboard.is_pressed('esc'):
        print("\n\n🛑 PARADA DE EMERGÊNCIA ACIONADA PELO USUÁRIO!")
        sys.exit(0)

def dormir(segundos):
    """Substituto inteligente para time.sleep que checa o ESC."""
    fim = time.time() + segundos
    while time.time() < fim:
        verificar_parada()
        time.sleep(0.1)

def esperar_upload_ou_matar(driver, timeout=10): 
    """
    Espera o preview da imagem aparecer.
    Se não aparecer, lança um erro para o Main tratar (pular produto).
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'shopee-image-manager__content')]//img")
            )
        )
        print("✅ Upload confirmado.")
        return True
        
    except Exception:
        print("❌ Upload demorou demais (Timeout).")
        raise Exception("Falha no Upload da Imagem (Timeout)")

def preencher_atributo_dinamico(driver, titulo_campo, valor_para_selecionar):
    verificar_parada()
    wait = WebDriverWait(driver, 10)
    print(f"\n--- Preenchendo: {titulo_campo} -> {valor_para_selecionar} ---")

    try:
        # 1. ENCONTRA O CAMPO E CLICA PARA ABRIR O DROPDOWN
        # (Essa parte de abrir o campo parece estar correta para todos os casos de select)
        if titulo_campo == "Quantidade":
            try:
                # 1. O SEU XPATH (Que acha a linha certa) + O FINAL CORRETO (//input)
                # Adicionei //input no final para entrar na div e pegar o campo de texto
                xpath_qtd = f"//div[contains(@class, 'attribute-select-item')][.//div[contains(@class, 'edit-label') and contains(., '{titulo_campo}')]]//input"
                
                input_qtd = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_qtd)))
                
                # Scroll para garantir foco
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", input_qtd)
                dormir(0.5)

                # 2. LIMPAR E DIGITAR
                # Inputs numéricos as vezes bugam com .clear(), então clicamos primeiro
                input_qtd.click()
                
                # Tenta limpar com teclas (Ctrl+A -> Delete) é mais garantido que .clear() em React
                from selenium.webdriver.common.keys import Keys
                input_qtd.send_keys(Keys.CONTROL + "a")
                input_qtd.send_keys(Keys.BACK_SPACE)
                
                # Digita o valor
                input_qtd.send_keys(str(valor_para_selecionar))
                
                print(f"✅ {titulo_campo} preenchido com '{valor_para_selecionar}'!")
                return # Sai da função

            except Exception as e:
                print(f"❌ Erro ao digitar quantidade: {e}")
                # PLANO B: Se falhar o send_keys, força via JavaScript
                try:
                    print("   -> Tentando forçar via JavaScript...")
                    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));", input_qtd, str(valor_para_selecionar))
                    print("   -> JS funcionou!")
                    return
                except:
                    pass
                return
        if titulo_campo == "Marca":
            xpath_campo = f"//*[contains(text(), '{titulo_campo}')]/following::div[contains(@class, 'attribute-select-item')][1]"
            campo_select = espera_click(driver, xpath_campo)
        else:
            xpath_campo = f"//div[contains(@class, 'attribute-select-item')][.//div[contains(@class, 'edit-label') and contains(., '{titulo_campo}')]]//div[contains(@class, 'edit-row-right-medium')]"
            campo_select = espera_click(driver, xpath_campo)
        dormir(1) 
        

        # Lógica especifica para Material e Estilo
        if titulo_campo in ["Material", "Estilo"]:
            try:
                print(f"\n--- INICIANDO FLUXO DE CRIAÇÃO PARA {titulo_campo} ---")
                
                # Clicar em Adicionar
                xpath_add = "//div[contains(text(), 'Adicionar um novo item')] | //span[contains(., 'Adicionar um novo item')]"
                btn_add = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_add)))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn_add)
                dormir(1)
                driver.execute_script("arguments[0].click();", btn_add)
                
                dormir(1) 

                # Digitar no input dentro da UL
                xpath_input = "//ul//input[@placeholder='Inserir' or @placeholder='Enter' or @placeholder='Please Input']"
                input_novo = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_input)))
                
                input_novo.click()
                try:
                    input_novo.clear()
                except:
                    pass
                input_novo.send_keys(valor_para_selecionar)
                print(f"✅ Texto '{valor_para_selecionar}' enviado!")

                dormir(1)

                # Confirmar 
                xpath_confirmar = "//ul//button"
                espera_click(driver, xpath_confirmar)
                dormir(DELAY_PADRAO)
                print("✅ Item criado e selecionado!")

            except Exception as e:
                print(f"\n❌ ERRO NO FLUXO DE CRIAÇÃO: {e}")

        # ======================================================================
        # LÓGICA TIPO B: SELECIONAR EXISTENTE (Marca, Peso, etc)
        # ======================================================================
        else:
            print(f"\n--- INICIANDO FLUXO DE SELEÇÃO PADRÃO PARA {titulo_campo} ---")
            
            # Tenta digitar na busca (se houver) para filtrar a lista
            try:
                xpath_busca = "//input[contains(@placeholder, 'Insira ao menos') or @type='search']"
                # Timeout curto aqui, pois nem todo select tem campo de busca
                input_busca = espera_click(driver, xpath_busca, timeout=3)

                print(f"   -> Filtrando por '{valor_para_selecionar}'...")
                input_busca.click()
                input_busca.clear()
                input_busca.send_keys(valor_para_selecionar)
                dormir(1.5) # Tempo para a lista filtrar
            except:
                print("   -> Campo de busca não encontrado, procurando direto na lista.")

            # Seleciona opção na lista
            # O contains(text()) as vezes falha com espaços, o contains(.,) é mais robusto
            xpath_opcao = f"//div[contains(., '{valor_para_selecionar}') and contains(@class, 'eds-option')]"
            
            # Se não achar, pode ser que o texto esteja exato
            try:
                espera_click(driver, xpath_opcao)
                print(f"✅ {titulo_campo} selecionado com sucesso!")
            except:
                print(f"❌ Não encontrei a opção '{valor_para_selecionar}' na lista.")

        dormir(0.5)

    except Exception as e:
        print(f"⚠️ Erro fatal ao tentar preencher {titulo_campo}: {e}")

def carregar_texto_descricao():
    try:
        caminho_arquivo = os.path.join(os.getcwd(), "resources", "descricao.txt")
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            return arquivo.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em {caminho_arquivo}")
        return None

def espera_click(driver, xpath, timeout=10, scroll=True):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    if scroll:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", el
        )

    verificar_parada()

    el.click()
    return el

def espera_input(driver, xpath, timeout=10):
    el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].click();", el)
    
    verificar_parada()

    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.BACK_SPACE)
    return el

def limpar_input(el):
    el.click()
    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.BACK_SPACE)
       
def ordenar_por_prioridade_visual(lista_caminhos):
    """
    Reordena a lista de imagens para que a 'Capa' seja sempre Front/Main/Fullbody.
    """
    # Definição de prioridades (Menor número = Aparece primeiro)
    termos_prioridade = {
        "front": 0,
        "frente": 0,
        "main": 0,
        "full": 1,      
        "standard": 2, 
        "padrao": 2,
        "padrão": 2,
        "side": 5,
        "lateral": 5,
        "angle": 6,
        "detail": 8,
        "back": 9,      # Costas geralmente é a última que queremos ver
        "costas": 9,
        "top": 9
    }

    def calcular_score(caminho):
        nome_arquivo = os.path.basename(caminho).lower()
        
        for termo, score in termos_prioridade.items():
            # Verifica se o termo está no nome do arquivo (ex: "orc - front.jpg")
            if termo in nome_arquivo:
                return score
        
        return 10 # Se não achar nada, vai pro final da fila

    # O Python ordena baseado no retorno da função 'key'
    return sorted(lista_caminhos, key=calcular_score)

# ==============================================================================
# LÓGICA DE PREENCHIMENTO DO BOT
# ==============================================================================

def iniciar_driver(headless=False):
    """Configura o driver com otimizações de performance SEGURAS."""
    print("Iniciando Driver (Modo Performance)...")
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={CAMINHO_PERFIL}")
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")
    options.add_argument("--window-size=1080,720") 
    
    # --- OTIMIZAÇÃO POR PREFS ---
    prefs = {
        
        # Manter IMAGENS ativadas
        "profile.managed_default_content_settings.images": 1,
        "profile.default_content_setting_values.images": 1,
        
        # Bloquear coisas inúteis que gastam RAM
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
        
        # Tenta forçar o navegador a não renderizar animações de acessibilidade
        "accessibility.animation_policy": 2 
    }
    options.add_experimental_option("prefs", prefs)
    # ---------------------------------------------------------------

    # --- Otimização do Processo ---
    options.add_argument("--disable-smooth-scrolling")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-default-browser-check")
    
    # Para evitar crash no upload
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    if headless:
        print("👻 Modo Invisível (Headless) Ativado!")
        options.add_argument("--headless=new") 
   

    driver = uc.Chrome(options=options, version_main=144)
    driver.set_window_size(1080, 720)
        
    return driver

def preencher_dados_basicos(driver, lista_caminhos, nome_produto):
    print("\n--- PASSO 1: IMAGENS (GALERIA) ---")
    wait = WebDriverWait(driver, 10)
    
    # Filtra apenas caminhos que existem e limita a 9 (limite Shopee)
    imagens_validas = [p for p in lista_caminhos if os.path.exists(p)][:9]
    
    if not imagens_validas:
        raise Exception("Nenhuma imagem válida encontrada para upload!")

    print(f"Enviando {len(imagens_validas)} imagens para a galeria...")
    
    try:
        # Truque: Enviar todos os caminhos de uma vez separados por \n
        string_caminhos = "\n".join(imagens_validas)
        
        campo_upload = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        campo_upload.send_keys(string_caminhos)
        esperar_upload_ou_matar(driver, timeout=10)
        # Espera visual simples para garantir upload
        dormir(3 + len(imagens_validas)) 
        print("✅ Galeria preenchida.")

    except Exception as e:
        print(f"❌ Erro na galeria: {e}")
        raise e

    # Preenche Nome
    xpath_nome = "//input[@placeholder='Nome da Marca + Tipo do Produto + Atributos-chave (Materiais, Cores, Tamanho, Modelo)']"
    try:
        espera_input(driver, xpath_nome).send_keys(nome_produto[:120]) # Limite 120 chars
        print("✅ Nome preenchido.")
    except Exception as e:
        print(f"❌ Erro no nome: {e}")

    print("Avançando...")
    try:
        espera_click(driver, "//button[contains(., 'Next Step') or contains(., 'Próximo')]")
    except:
        print("Botão próximo não encontrado, tentando JS...")

def selecionar_categoria(driver):
    """
    Pesquisa a categoria e clica na hierarquia.
    """
    print("\n--- CATEGORIA ---")
    wait = WebDriverWait(driver, 10)
    
    termo_alvo = "Figuras de Ação"
    hierarquia_para_clicar = ["Hobbies e Coleções", "Itens Colecionáveis", "Figuras de Ação"]
    xpath_categoria = "//div[contains(@class, 'product-category-box') or contains(@class, 'shopee-product-category-input')]"
    try:
        # Abrir seletor
        print("Abrindo seletor...")
        espera_click(driver, xpath_categoria, timeout=1)

        # Verificar sugestão
        print(f"Verificando se '{termo_alvo}' já apareceu como sugestão...")
        sugestao_encontrada = False
        try:
            xpath_sugestao = f"//li[contains(., '{termo_alvo}')]"
            espera_click(driver, xpath_sugestao)
            print("SUGESTÃO DA SHOPEE ENCONTRADA E CLICADA!")
            sugestao_encontrada = True
        except:
            print("Sugestão não encontrada. Iniciando busca manual...")
            sugestao_encontrada = False 

        # Busca Manual se não achou sugestão
        if not sugestao_encontrada:
            xpath_input_busca = "//input[contains(@placeholder, 'Insira ao menos')]"

            print(f"Digitando '{termo_alvo}' no input...")
            input_busca = espera_click(driver, xpath_input_busca)
            input_busca.send_keys(termo_alvo)

            # Loop na Hierarquia
            print("Navegando pelas colunas filtradas...")
            for item_nome in hierarquia_para_clicar:
                print(f"   -> Procurando: {item_nome}")
                xpath_item = f"//li[contains(., '{item_nome}')]"    
                espera_click(driver, xpath_item)
                print(f"   -> '{item_nome}' clicado.")

        # Confirmando Categoria
        print("Finalizando Categoria...")
        try:
            xpath_btn_confirmar = "//button[contains(., 'Confirmar')]"
            espera_click(driver, xpath_btn_confirmar)
        except:
            pass 
            
        print("Categoria definida!")    

    except Exception as e:
        print(f"Erro na Categoria: {e}")
        input("Pressione ENTER para continuar manualmente...")

def preencher_atributos(driver, marca, material, peso, estilo, quantidade):
    """
    PASSO 3: Preenche atributos técnicos (Marca, Peso, etc).
    """
    print("\n--- PASSO 3: ATRIBUTOS ---")
    wait = WebDriverWait(driver, 10)

    campos = {"Material": material, "Marca": marca, "Peso do Produto": peso, 
              "Estilo": estilo, "Quantidade": quantidade}
    
    for campo, valor in campos.items():
        print(f"Preparando para preencher: {campo}")
        preencher_atributo_dinamico(driver, campo, valor)

def colar_descricao(driver):
    """
    Insere a descrição diretamente no editor Rich Text via JS.
    """
    print("DESCRIÇÃO")

    texto_descricao = carregar_texto_descricao()
    if not texto_descricao:
        print("⚠️ Texto da descrição vazio.")
        return

    try:
        xpath_editor = "//div[@contenteditable='true']"
        campo_descricao = espera_click(driver, xpath_editor)

        html = texto_descricao.replace("\n", "<br>")

        driver.execute_script("""
            arguments[0].innerHTML = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, campo_descricao, html)

        print("✅ Descrição inserida com sucesso (JS).")

    except Exception as e:
        print(f"❌ Erro ao inserir descrição: {e}")

def preencher_informacoes_finais(driver):
    """
    Sessoes: Informações de Vendas, Envio e finalização do produto.
    """
    print("\n--- INFORMAÇÕES FINAIS ---")
    wait = WebDriverWait(driver, 10)

    try:
        # Sessão Informações de vendas:
        
        print(" -> Verificando informações de venda...")
        
        # Clicando no botão de adicionar variações
        xpath_variacoes = "//div[contains(@class, 'variation-add-button')]//button"
        espera_click(driver, xpath_variacoes)

        # Encontrando o input de variação
        xpath_input_variacao = "//div[contains(@class, 'variation-edit-main')]//input"
        espera_input(driver, xpath_input_variacao).send_keys("Primed?")

        # Input de opções
        xpath_input_opcao1 = "(//div[contains(@class,'option-container')]//input[@placeholder='Inserir'])[1]"
        espera_input(driver, xpath_input_opcao1).send_keys("Sim")
        xpath_input_opcao2 = "(//div[contains(@class,'option-container')]//input[@placeholder='Inserir'])[2]"
        espera_input(driver, xpath_input_opcao2).send_keys("Não")

        # Preços de opcoes
        print(" Definindo preços das variações...")
        xpath_preco_opcao1 = "(//div[contains(@class,'variation-model-table-body')]//div[contains(@class, 'table-cell-wrapper')][1]//input[contains(@placeholder, 'Inserir')])[1]"
        espera_input(driver, xpath_preco_opcao1).send_keys("99,90")
        xpath_preco_opcao2 = "(//div[contains(@class,'variation-model-table-body')]//div[contains(@class, 'table-cell-wrapper')][2]//input[contains(@placeholder, 'Inserir')])[1]"
        espera_input(driver, xpath_preco_opcao2).send_keys("109,90")

        # Estoque de opcoes
        print(" Definindo estoques das variações...")
        xpath_estoque_opcao1 = "(//div[contains(@class,'variation-model-table-body')]//div[contains(@class, 'table-cell-wrapper')][1]//input[contains(@placeholder, 'Inserir')])[2]"
        espera_input(driver, xpath_estoque_opcao1).send_keys("500")
        xpath_estoque_opcao2 = "(//div[contains(@class,'variation-model-table-body')]//div[contains(@class, 'table-cell-wrapper')][2]//input[contains(@placeholder, 'Inserir')])[2]"
        espera_input(driver, xpath_estoque_opcao2).send_keys("500")


    except Exception as e:
        print(f"❌ Erro na sessão de variações: {e}")
    
    try:
        # Sessão Envio
        print(" Preenchendo Frete, peso e dimensões")
        
        # Peso
        xpath_peso = "//div[contains(@data-product-edit-field-unique-id, 'weight')]//input[contains(@placeholder, 'Inserir')]"
        input_peso = espera_input(driver, xpath_peso)
        input_peso.send_keys("0,1")

        # Dimensões
        dimensoes = ["dimension.width", "dimension.length", "dimension.height"]
        dimensoesPlaceholder = ["Largura", "Comprimento", "Altura"]
        for dim in dimensoes:
            # Procura input pelo placeholder exato
            xpath_dim = f"//div[@data-product-edit-field-unique-id='{dim}']//input[contains(@placeholder, '{dimensoesPlaceholder[dimensoes.index(dim)]}')]"
            input_dim = espera_input(driver, xpath_dim)
            input_dim.send_keys("10")
            dormir(0.3)

        dormir(1.5)

        # Click swith de retirada
        try:
            xpath_switch_base = "//div[contains(@class,'logistics-item-ui-t1')][.//div[contains(normalize-space(.), 'Retirada')]]//div[contains(@class,'eds-switch')]"
            
            switch_el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_switch_base)))
            
            classes_do_elemento = switch_el.get_attribute("class")
            
            if "eds-switch--open" in classes_do_elemento:
                print(" -> Switch Retirada estava ATIVADO. Desativando...")
                switch_el.click()
                dormir(0.5) 
                
        except Exception as e:
            print(f"Não foi possível verificar o switch de Retirada: {e}")

        # SOB ENCOMENDA 
        print("Configurando Pré-Encomenda")
        
        # Encontrando o botão "Sim" para Pré-encomenda
        try:
            xpath_sim = "//div[@data-product-edit-field-unique-id='preOrder']//label[.//span[normalize-space()='Sim']]"
            btn_sim = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_sim    )))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block : 'center'});", btn_sim)
            dormir(DELAY_PADRAO)
            btn_sim.click()
            print("Pré-encomenda ativada.")

        except Exception as e:
            print(f"Erro ao clicar em Sim: {e}")

        # Definindo 7 dias para pré-encomenda
        print(" -> Definindo 7 dias...")
        dormir(DELAY_PADRAO + 1)
        xpath_dias = "//div[contains(@class, 'pre-order-input')]//input[contains(@placeholder, '0')]"
        input_dias = espera_input(driver, xpath_dias)
        input_dias.send_keys("7")

        dormir(DELAY_PADRAO)
    except Exception as e:
        print(f"❌ Erro na sessão de envio: {e}")


def preencher_envio_e_salvar(driver):
    print("\n--- ENVIO E SALVAMENTO ---")
    wait = WebDriverWait(driver, 10)

    try:
        # Peso e Dimensões (Mantido do seu código, apenas resumido)
        xpath_peso = "//div[contains(@data-product-edit-field-unique-id, 'weight')]//input"
        espera_input(driver, xpath_peso).send_keys("0.2") # 200g

        dimensoes = ["width", "length", "height"]
        for dim in dimensoes:
            xpath_dim = f"//div[contains(@data-product-edit-field-unique-id, 'dimension.{dim}')]//input"
            espera_input(driver, xpath_dim).send_keys("10")
        
        # Pré-Encomenda (Mantido)
        xpath_sim = "//label[.//span[normalize-space()='Sim']]"
        try:
            espera_click(driver, xpath_sim, timeout=3).click()
            xpath_dias = "//div[contains(@class, 'pre-order-input')]//input"
            espera_input(driver, xpath_dias).send_keys("7")
        except:
            print("Não consegui ativar pré-encomenda (ou já estava).")

        # SALVAR
        print(" -> Salvando Rascunho...")
        xpath_salvar = "//button[.//span[contains(normalize-space(.), 'Salvar e Não Publicar')]]"
        espera_click(driver, xpath_salvar)
        
        # Modal confirmação (as vezes aparece, as vezes não)
        try:
            xpath_confirm_modal = "//div[contains(@class,'eds-modal')]//button[contains(., 'Salvar')]"
            espera_click(driver, xpath_confirm_modal, timeout=3)
        except:
            pass

        print("✅ Produto salvo!")

    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")

# Função Principal

def cadastrar_produto_completo(driver, caminho_imagem, nome_produto, nome_colecao, max_tentativas=3):
    """
    Função Wrapper que chama todos os passos do cadastro.
    """
    print(f"\n🚀 INICIANDO CADASTRO: {nome_produto} (Coleção: {nome_colecao})")
    
    for tentativa in range(1, max_tentativas + 1):
        try:
            print(f"🔄 Tentativa {tentativa} de {max_tentativas}...")

            url_add = "https://seller.shopee.com.br/portal/product/new"
            driver.get(url_add)
            dormir(3) 

            # ==================================================================
            # EXECUÇÃO DO PREENCHIMENTO
            # ==================================================================

            preencher_dados_basicos(driver, caminho_imagem, nome_produto, nome_colecao)
            
            selecionar_categoria(driver)
            
            colar_descricao(driver)

            preencher_atributos(driver, 
                                marca="Taberna e Goblins",  
                                material="Resin",
                                peso="30g",
                                estilo="Fantasy",
                                quantidade=1)
            
            preencher_informacoes_finais(driver)
            
            # ==================================================================
            
            print(f"✨ PRODUTO {nome_produto} FINALIZADO COM SUCESSO!")
            dormir(2) 
            return

        except Exception as e:
            print(f"⚠️  Falha na tentativa {tentativa}: {e}")
            
            if tentativa < max_tentativas:
                print("♻️  Recarregando página para tentar novamente...")
                dormir(2)
            else:
                print(f"❌  Esgotadas as {max_tentativas} tentativas para {nome_produto}.")
                raise e

# ==============================================================================
# PARA TESTES
# ==============================================================================
def executar_bot():
    if not os.path.exists(ARQUIVO_MAPA):
        print("❌ JSON do mapa não encontrado.")
        return

    with open(ARQUIVO_MAPA, "r", encoding="utf-8") as f:
        lista_produtos = json.load(f)

    driver = iniciar_driver()
    driver.get("https://seller.shopee.com.br/portal/product/new")
    print("\n🔑 FAÇA O LOGIN MANUALMENTE SE NECESSÁRIO.")
    input("Pressione ENTER quando estiver logado na Home da Shopee...")

    for i, produto in enumerate(lista_produtos):
        try:
            nome = produto['product_name']
            colecao = produto.get('collection_name', 'Geral')
            variacoes = produto.get('variations', [])
            
            print(f"\n🚀 PROCESSANDO [{i+1}/{len(lista_produtos)}]: {nome}")

            # ==========================================================
            # 1. COLETOR INTELIGENTE DE IMAGENS
            # ==========================================================
            todas_imagens = [] # 1. Começa vazia
            
            # 2. ENCHE A LISTA (O Loop vem primeiro!)
            for v in variacoes:
                for img in v.get('images', []):
                    # Usa o GPS para achar o arquivo físico
                    caminho_real = encontrar_imagem_no_disco(produto, v, img)
                    
                    if caminho_real:
                        todas_imagens.append(caminho_real)
                    else:
                        print(f"   ⚠️ Imagem não achada: {img.get('filename')}")

            # 3. LIMPA (Deduplicação mantendo ordem de inserção)
            todas_imagens = list(dict.fromkeys(todas_imagens))

            # 4. ARRUMA (Aplica a lógica de Front/Main primeiro)
            # Certifique-se que a função ordenar_por_prioridade_visual está definida no arquivo
            todas_imagens = ordenar_por_prioridade_visual(todas_imagens)

            # 5. VERIFICA
            if not todas_imagens:
                print("⚠️ Produto sem imagens encontradas no disco. Pulando.")
                continue 

            print(f"   📸 {len(todas_imagens)} imagens prontas e ordenadas.")

            # ==========================================================
            # 2. FLUXO DE NAVEGAÇÃO
            # ==========================================================
            driver.get("https://seller.shopee.com.br/portal/product/new")
            dormir(3)

            # Tela 1: Imagens e Nome
            # Passamos a LISTA de imagens agora
            preencher_dados_basicos(driver, todas_imagens, f"{nome} - {colecao} - RPG Miniatura 3D")
            
            # Tela 2: O Resto
            #selecionar_categoria(driver)
            #colar_descricao(driver)
           # 
            ## Ajuste os atributos conforme sua necessidade real
            #preencher_atributos(driver, 
            #                    marca="Taberna e Goblins", 
            #                    material="Resin", 
            #                    peso="50g", 
            #                    estilo="Fantasy", 
            #                    quantidade=1)
           # 
            ## Variações Dinâmicas (Se existirem)
            #if variacoes:
            #    # Nota: Certifique-se que 'preencher_variacoes_dinamicas' 
            #    # também use 'encontrar_imagem_no_disco' internamente se for subir foto por variação
            #    preencher_variacoes_dinamicas(driver, variacoes)
           # 
            #finalizar_envio(driver)
            
            print(f"✨ Sucesso: {nome}")
            dormir(3)

        except Exception as e:
            print(f"❌ Falha no produto {nome}: {e}")
            dormir(2)

    print("🏁 Fim da fila.")
    input("Enter para sair.")
    driver.quit()

if __name__ == "__main__":
    executar_bot()