import os
import time
import json
import keyboard  
import sys
import re
import pyperclip
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


# ==============================================================================
# CONFIGURAÇÕES (CONSTANTES)
# ==============================================================================
DELAY_PADRAO = 0.5
CAMINHO_PROJETO = os.getcwd()
CAMINHO_PERFIL = os.path.join(CAMINHO_PROJETO, "Perfil_Bot_Shopee")
ARQUIVO_MAPA = "mapa_global.json"

ARQUIVO_HISTORICO = "logs/history.json"

# ==============================================================================
# FUNÇÕES DE CONTROLE
# ==============================================================================

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
 
def carregar_historico():
    if not os.path.exists(ARQUIVO_HISTORICO):
        return []
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def salvar_no_historico(nome_produto):
    historico = carregar_historico()
    if nome_produto not in historico:
        historico.append(nome_produto)
        # Garante que a pasta logs existe
        os.makedirs(os.path.dirname(ARQUIVO_HISTORICO), exist_ok=True)
        with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=4, ensure_ascii=False)

# ==============================================================================
# FUNÇÕES ESPECIALIZADAS (PRIVADAS)
# ==============================================================================

def _preencher_input_quantidade(driver, valor):
    try:
        xpath_qtd = "//div[contains(@class, 'attribute-select-item')][.//div[contains(., 'Quantidade')]]//input"
        input_qtd = espera_input(driver, xpath_qtd)
        input_qtd.send_keys(str(valor))

        print(f"✅ Quantidade definida: {valor}")
        
    except Exception as e:
        print(f"⚠️ Erro no input normal, tentando JS para Quantidade: {e}")
        try:
            input_qtd = driver.find_element(By.XPATH, xpath_qtd)
            driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));", 
                input_qtd, str(valor)
            )
        except:
            pass

def _abrir_dropdown(driver, titulo_campo):
    if titulo_campo == "Marca":
        xpath = f"//*[contains(text(), '{titulo_campo}')]/following::div[contains(@class, 'attribute-select-item')][1]"
    else:
        xpath = f"//div[contains(@class, 'attribute-select-item')][.//div[contains(., '{titulo_campo}')]]//div[contains(@class, 'edit-row-right-medium')]"
    
    return espera_click(driver, xpath)

def _selecionar_ou_criar_customizado(driver, valor):
    """
    Para Material/Estilo
    """
    try:
        xpath_add = "//div[contains(text(), 'Adicionar um novo item')] | //span[contains(., 'Adicionar um novo item')]"
        espera_click(driver, xpath_add)
        
        xpath_novo_input = "//ul//div[contains(@class, 'eds-option-add__input')]//input"
        input_novo = espera_input(driver, xpath_novo_input)
        input_novo.send_keys(valor)
        dormir(0.5)
        
        xpath_confirmar = "//ul//div[contains(@class, 'eds-option-add__input')]//button[contains(@class, 'eds-option-add__add-confirm-icon')]"
        dormir(0.2)
        espera_click(driver, xpath_confirmar)
        print(f"✅ Novo item criado e selecionado: {valor}")
        
    except Exception as e:
        print(f"❌ Erro ao criar item customizado '{valor}': {e}")

def _selecionar_padrao(driver, valor):
    """Para Marca, Peso, etc."""
    try:
        try:
            xpath_busca = "//input[contains(@placeholder, 'Insira ao menos') or @type='search']"
            input_busca = espera_input(driver, xpath_busca, timeout=3)
            input_busca.send_keys(valor)
            dormir(1)
        except:
            pass
        
        xpath_opcao = f"//div[contains(@class, 'eds-option')][contains(., '{valor}')]"
        espera_click(driver, xpath_opcao)
        print(f"✅ Selecionado: {valor}")    
    
    except Exception as e:
        print(f"❌ Não foi possível selecionar '{valor}'.")

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

    nome_colecao = sanitarizar_nome(produto.get('collection_name', 'Geral'))
    pasta_colecao = os.path.join(os.getcwd(), "data", "processed", nome_colecao)
    
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

def espera_upload(driver, timeout=10): 
    """
    Espera o preview da imagem aparecer.
    Se não aparecer, lança um erro para o Main tratar (pular produto).
    """
    imagem_na_tela = False
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'shopee-image-manager__content')]//img")
            )
        )
        print("✅ Upload confirmado.")
        imagem_na_tela = True
        return imagem_na_tela
        
    except Exception:
        print("❌ Upload demorou demais (Timeout).")

def preencher_atributo_dinamico(driver, titulo_campo, valor_para_selecionar):
    print(f"\n--- Preenchendo: {titulo_campo} -> {valor_para_selecionar} ---")

    try:
        if titulo_campo == "Quantidade":
            _preencher_input_quantidade(driver, valor_para_selecionar)
            return
        
        _abrir_dropdown(driver, titulo_campo)
        dormir(0.5)

        if titulo_campo in ["Material", "Estilo"]:
            _selecionar_ou_criar_customizado(driver, valor_para_selecionar)
        else:
            _selecionar_padrao(driver, valor_para_selecionar)

    except Exception as e:
        print(f"🔥 Erro crítico em '{titulo_campo}': {e}")
    """
    Controlador principal que decide qual estratégia usar baseada no campo.
    """
    wait = WebDriverWait(driver, 10)
    print(f"\n--- Preenchendo: {titulo_campo} -> {valor_para_selecionar} ---")

    try:
        if titulo_campo == "Quantidade":
            _preencher_input_quantidade(driver, wait, valor_para_selecionar)
            return

        _abrir_dropdown(driver, wait, titulo_campo)
        dormir(0.5)

        if titulo_campo in ["Material", "Estilo"]:
            # Estes permitem criar itens novos
            _selecionar_ou_criar_customizado(driver, wait, valor_para_selecionar)
        else:
            # Estes exigem seleção de lista existente (Marca, Peso)
            _selecionar_padrao(driver, wait, valor_para_selecionar)

    except Exception as e:
        print(f"🔥 Erro crítico em '{titulo_campo}': {e}")

def carregar_texto_descricao():
    try:
        caminho_arquivo = os.path.join(os.getcwd(), "assets", "descricao.txt")
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            return arquivo.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em {caminho_arquivo}")
        return None
          
def ordenar_por_prioridade_visual(lista_caminhos):
    """
    Reordena a lista de imagens para que a 'Capa' seja sempre Front/Main/Fullbody.
    """
    # Definição de prioridades
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
    print("Iniciando Driver...")
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
    
    # Preenchendo imagens
    imagens_validas = [p for p in lista_caminhos if os.path.exists(p)][:9]
    if not imagens_validas:
        raise Exception("Nenhuma imagem válida encontrada!")

    string_caminhos = "\n".join(imagens_validas)
    
    max_tentativas = 3
    sucesso_upload = False

    for tentativa in range(1, max_tentativas + 1):
        try:
            print(f"Tentativa de Upload {tentativa}/{max_tentativas}...")
            campo_upload = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
            
            driver.execute_script("arguments[0].value = '';", campo_upload)
            dormir(1)
            
            campo_upload.send_keys(string_caminhos)
            
            dormir(2 + len(imagens_validas))
            
            if espera_upload(driver, timeout=5):
                print("✅ Galeria preenchida.")
                sucesso_upload = True
                break
            else:
                print("⚠️ Falha na verificação visual. Tentando novamente...")
        
        except Exception as e:
            print(f"❌ Erro na tentativa {tentativa}: {e}")
            dormir(2)

    if not sucesso_upload:
        raise Exception("Falha crítica no upload da galeria após tentativas.")

    # Preenche Nome
    xpath_nome = "//input[@placeholder='Nome da Marca + Tipo do Produto + Atributos-chave (Materiais, Cores, Tamanho, Modelo)']"
    try:
        espera_input(driver, xpath_nome).send_keys(nome_produto[:120])
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
    sugestao1_encontrada = False
    termo_alvo1 = "Hobbies e Coleções > Itens Colecionáveis > Figuras de Ação"
    xpath_sugestao1 =  f"//div[contains(@class, 'category-select-radio') and contains(., '{termo_alvo1}')]"
    try:
        print(f"Verificando se '{termo_alvo1}' já apareceu como sugestão...")
        espera_click(driver, xpath_sugestao1, timeout=5)
        print("SUGESTÃO DA SHOPEE ENCONTRADA E CLICADA!")
        sugestao1_encontrada = True
    except:
        print("Sugestão não encontrada. Iniciando busca manual...")
        sugestao1_encontrada = False   
    if not sugestao1_encontrada:
        termo_alvo2 = "Figuras de Ação"
        hierarquia_para_clicar = ["Hobbies e Coleções", "Itens Colecionáveis", "Figuras de Ação"]
        xpath_categoria = "//div[contains(@class, 'product-category-box') or contains(@class, 'shopee-product-category-input')]"
        try:
            # Abrir seletor
            print("Abrindo seletor...")
            espera_click(driver, xpath_categoria, timeout=1)
    
            # Verificar sugestão
            print(f"Verificando se '{termo_alvo2}' já apareceu como sugestão...")
            sugestao2_encontrada = False
            try:
                xpath_sugestao2 = f"//li[contains(., '{termo_alvo2}')]"
                espera_click(driver, xpath_sugestao2)
                print("SUGESTÃO DA SHOPEE ENCONTRADA E CLICADA!")
                sugestao2_encontrada = True
            except:
                print("Sugestão não encontrada. Iniciando busca manual...")
                sugestao2_encontrada = False 
    
            # Busca Manual se não achou sugestão
            if not sugestao2_encontrada:
                xpath_input_busca = "//input[contains(@placeholder, 'Insira ao menos')]"
    
                print(f"Digitando '{termo_alvo2}' no input...")
                input_busca = espera_click(driver, xpath_input_busca)
                input_busca.send_keys(termo_alvo2)
    
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
    campos = {"Material": material, "Marca": marca, "Peso do Produto": peso, 
              "Estilo": estilo, "Quantidade": quantidade}
    for campo, valor in campos.items():
        print(f"Preparando para preencher: {campo}")
        preencher_atributo_dinamico(driver, campo, valor)

def colar_descricao(driver):
    """
    Insere a descrição usando a Área de Transferência (Ctrl+V).
    Método muito mais rápido que previne travamentos do editor React.
    """
    print("\n--- DESCRIÇÃO (MÉTODO TURBO) ---")

    texto_descricao = carregar_texto_descricao()
    if not texto_descricao:
        print("⚠️ Texto da descrição vazio.")
        return

    try:
        wait = WebDriverWait(driver, 10)
        xpath_editor = "//div[@contenteditable='true']"
        
        # 1. Encontra e clica para dar foco
        campo_descricao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_editor)))
        campo_descricao.click()
        dormir(0.5)

        # 2. Limpa o conteúdo atual (Ctrl + A -> Delete)
        # Garante que não vai duplicar se a Shopee tiver carregado algo
        campo_descricao.send_keys(Keys.CONTROL, "a")
        campo_descricao.send_keys(Keys.BACK_SPACE)
        dormir(0.5)

        # 3. Copia o texto para a memória do computador
        pyperclip.copy(texto_descricao)
        
        # 4. Cola (Ctrl + V)
        campo_descricao.send_keys(Keys.CONTROL, "v")
        
        print("✅ Descrição colada instantaneamente!")
        dormir(1) # Tempo para o site processar a colagem

    except Exception as e:
        print(f"❌ Erro no método Clipboard: {e}")
        print("   -> Tentando método alternativo (JS)...")
        
        # Fallback: Se o Ctrl+V falhar, tenta o método antigo via JS
        try:
            html = texto_descricao.replace("\n", "<br>")
            driver.execute_script("""
                arguments[0].innerHTML = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, campo_descricao, html)
            print("   -> Fallback JS funcionou.")
        except Exception as e_js:
            print(f"   ❌ Falha total na descrição: {e_js}")

def preencher_variacoes(driver, produto, variacoes_json):
    """
    Preenche variações dinamicamente baseado no JSON.
    Args:
        driver: O navegador.
        produto: O objeto do produto inteiro (para calcular nomes de imagem).
        variacoes_json: A lista 'variations' do JSON.
    """
    print("\n--- CONFIGURANDO VARIAÇÕES (DINÂMICO) ---")
    try:
        # ATIVAR VARIAÇÕES
        xpath_btn_ativar = "//div[contains(@class, 'variation-add-button')]//button"
        try:
            espera_click(driver, xpath_btn_ativar, timeout=3)
            print(" -> Botão 'Ativar Variações' clicado.")
        except:
            print(" -> Variações já parecem estar ativas (ou botão não encontrado).")
        # --------- Grupo 1 de variacoes - Modelo
        try:
            xpath_grupo1 = "//div[contains(@data-product-edit-field-unique-id, 'tierVariation_0')]"
            try:
                xpath_nome_grupo = f"{xpath_grupo1}//input"
                espera_input(driver, xpath_nome_grupo).send_keys("Modelo")
                dormir(0.5)
            except Exception as e:
                print(f"⚠️ Erro ao nomear grupo: {e}")
            print(f" -> Cadastrando {len(variacoes_json)} opções...")
            for i, variacao in enumerate(variacoes_json):
                nome_opcao = variacao['variation_name']
                xpath_input_opt = f"({xpath_grupo1}//div[contains(@class,'option-container')]//input[@placeholder='Inserir' or @placeholder='Enter'])[{i+1}]"
                try:
                    campo = espera_input(driver, xpath_input_opt)
                    campo.send_keys(nome_opcao)
                    print(f"    Option [{i+1}]: {nome_opcao}")
                except Exception as e:
                    print(f"❌ Erro ao digitar opção '{nome_opcao}': {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Erro ao criar grupo 1 de variações: {e}")
        # --------- Grupo 2 de variacoes - Prime
        try:
            xpath_btn_ativar2 = "//div[contains(@class, 'variation-add-2')]//button"
            try:
                espera_click(driver, xpath_btn_ativar2, timeout=3)
                print(" -> Botão 'Ativar Variações' clicado.")
            except Exception as e:
                print(f" -> Variações já parecem estar ativas (ou botão não encontrado): {e}")
            try:
                xpath_grupo2 = "//div[contains(@data-product-edit-field-unique-id, 'tierVariation_1')]"
                xpath_nome_grupo = f"{xpath_grupo2}//input"
                espera_input(driver, xpath_nome_grupo).send_keys("Prime?")
                dormir(0.5)
            except Exception as e:
                print(f"⚠️ Erro ao nomear grupo: {e}")
            try:
                for i, valor in enumerate(['Sim','Não']):
                    xpath_input_opt2 = f"({xpath_grupo2}//div[contains(@class,'option-container')]//input[@placeholder='Inserir' or @placeholder='Enter'])[{i+1}]"
                    espera_input(driver, xpath_input_opt2).send_keys(valor)
                dormir(0.5)
            except Exception as e:
                print(f"⚠️ Erro ao nomear grupo: {e}")
        except Exception as e:
            print(f"⚠️ Erro ao criar grupo 2 de variações: {e}")
        
        # --------- Preenchimento de Preço/Estoque/Imagens -------------
        print(" -> Aplicando Preço/Estoque em Massa...")
        dormir(1) 
        try:
            # Inputs que ficam no cabeçalho da tabela (Batch Edit)
            xpath_batch_price = "//div[contains(@class, 'batch-edit')]//input[@placeholder='Preço']"
            xpath_batch_stock = "//div[contains(@class, 'batch-edit')]//input[@placeholder='Estoque']"
            xpath_btn_apply = "//div[contains(@class, 'batch-edit')]//button[contains(., 'Aplicar')]" # Pode ser 'Apply to all'

            # Preenche
            driver.find_element(By.XPATH, xpath_batch_price).send_keys("99,90") # Preço Base
            driver.find_element(By.XPATH, xpath_batch_stock).send_keys("500")   # Estoque Base
            
            # Aplica
            driver.find_element(By.XPATH, xpath_btn_apply).click()
            print("✅ Preços aplicados a todas as variações!")
        except Exception as e:
            print(f"❌ Falha no Batch Edit ({e}). Tentando fallback manual para 1º item...")
        
        print(" -> Vinculando imagens (ordenadas) às variações...")
        for i, variacao in enumerate(variacoes_json):
            imagens_da_var = variacao.get('images', [])
            
            if imagens_da_var:
                caminhos_candidatos = []
                for img_obj in imagens_da_var:
                    path = encontrar_imagem_no_disco(produto, variacao, img_obj)
                    if path: 
                        caminhos_candidatos.append(path)
                # APLICA O SCORE DE PRIORIDADE, PARA GARANTIR QUE A IMAGEM SEJA DE FRENTEIRO (FRONT/MAIN)
                if caminhos_candidatos:
                    caminhos_ordenados = ordenar_por_prioridade_visual(caminhos_candidatos)
                    melhor_foto = caminhos_ordenados[0] # Pega a campeã (Front/Main)
                    try:
                        xpath_file = f"(//div[contains(@class, 'variation-model-table-body')]//input[@type='file'])[{i+1}]"
                        driver.find_element(By.XPATH, xpath_file).send_keys(melhor_foto)
                        print(f"    📸 Foto Variação [{i+1}]: {os.path.basename(melhor_foto)}")
                    except Exception as e:
                        print(f"    ⚠️ Falha upload foto variação {i+1}: {e}")
                else:
                    print(f"    ⚠️ Nenhuma foto encontrada no disco para variação: {variacao['variation_name']}")
        print("✅ Variações concluídas.")
    except Exception as e:
        print(f"❌ Erro CRÍTICO na sessão de variações: {e}")
    
def preencher_finalizacoes(driver):
    """
    Sessoes: Informações de Vendas, Envio e finalização do produto.
    """
    print("\n--- INFORMAÇÕES FINAIS ---")
    wait = WebDriverWait(driver, 10)
    try:
        # Sessão Envio
        dormir(1)
        xpath_agrupavel = "//div[contains(@class,'editor-row') and contains(.,'Produto é um item agrupável')]//label[normalize-space()='Sim']"
        xpath_agrupavel = espera_click(driver, xpath_agrupavel)
        dormir(1)
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
    try:
        # SALVAR
        print(" -> Salvando Rascunho...")
        xpath_salvar = "//button[.//span[contains(normalize-space(.), 'Salvar e Não Publicar')]]"
        espera_click(driver, xpath_salvar)
        try:
            xpath_confirm_modal = "//div[contains(@class,'eds-modal')]//button[contains(., 'Salvar e Não Publicar')]"
            espera_click(driver, xpath_confirm_modal, timeout=3)
        except:
            pass
        print("✅ Produto salvo!")
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")

# ==============================================================================
# FUNÇÃO PRINCIPAL (WRAPPER)
# ==============================================================================
def executar_bot(headless=False):
    if not os.path.exists(ARQUIVO_MAPA):
        print("❌ JSON do mapa não encontrado.")
        return

    with open(ARQUIVO_MAPA, "r", encoding="utf-8") as f:
        lista_produtos = json.load(f)

    driver = iniciar_driver(headless=headless)
    driver.get("https://seller.shopee.com.br/portal/product/new")
    print("\n🔑 FAÇA O LOGIN MANUALMENTE SE NECESSÁRIO.")
    input("Pressione ENTER quando estiver logado na Home da Shopee...")
    # ==========================================================
    # Loop para cadastramento de produtos baseado no JSON
    # ==========================================================
    produtos_ja_enviados = carregar_historico()
    print(f"📜 Histórico carregado: {len(produtos_ja_enviados)} produtos já processados.")

    for i, produto in enumerate(lista_produtos):
        try:
            nome = produto['product_name']
            colecao = produto.get('collection_name', 'Geral')
            variacoes = produto.get('variations', [])

            if nome in produtos_ja_enviados:
                print(f"   ⚠️ Produto já processado: {nome}")
                continue

            print(f"\n🚀 PROCESSANDO [{i+1}/{len(lista_produtos)}]: {nome}")
            todas_imagens = []
            
            for v in variacoes:
                for img in v.get('images', []):
                    caminho_real = encontrar_imagem_no_disco(produto, v, img)
                    
                    if caminho_real:
                        todas_imagens.append(caminho_real)
                    else:
                        print(f"   ⚠️ Imagem não achada: {img.get('filename')}")

            todas_imagens = list(dict.fromkeys(todas_imagens))

            todas_imagens = ordenar_por_prioridade_visual(todas_imagens)

            if not todas_imagens:
                print("⚠️ Produto sem imagens encontradas no disco. Pulando.")
                continue 

            print(f"   📸 {len(todas_imagens)} imagens prontas e ordenadas.")
            # ==========================================================
            # FLUXO DE NAVEGAÇÃO
            # ==========================================================
            driver.get("https://seller.shopee.com.br/portal/product/new")
            dormir(3)
            preencher_dados_basicos(driver, todas_imagens, f"{nome} - {colecao} - Miniatura RPG - Impressão Resina 3D")
            selecionar_categoria(driver)
            colar_descricao(driver)
            preencher_atributos(driver, 
                                marca="Taberna e Goblins", 
                                material="Resin", 
                                peso="50g", 
                                estilo="Fantasy", 
                                quantidade=1)

            preencher_variacoes(driver, produto, variacoes)
            preencher_finalizacoes(driver)
            preencher_envio_e_salvar(driver)
            
            print(f"✨ Sucesso: {nome}")
            salvar_no_historico(nome)
            dormir(3)
        except Exception as e:
            print(f"❌ Falha no produto {nome}: {e}")
            dormir(2)
    print("🏁 Fim da fila.")
    input("Enter para sair.")
    driver.quit()

if __name__ == "__main__":
    executar_bot()
