import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

# ==============================================================================
# CONFIGURAÇÕES (CONSTANTES)
# ==============================================================================
DELAY_PADRAO = 0.5
CAMINHO_PROJETO = os.getcwd()
CAMINHO_PERFIL = os.path.join(CAMINHO_PROJETO, "Perfil_Bot_Shopee")

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def esperar_upload_ou_matar(driver, timeout=5):
    """
    Espera o preview da imagem aparecer.
    Se não aparecer, mata o script.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'shopee-image-manager__content')]//img")
            )
        )
        print("✅ Upload confirmado.")
        return True
    except:
        print("❌ Upload travado. Reiniciando script.")
        driver.quit()
        os._exit(1)

def preencher_atributo_dinamico(driver, titulo_campo, valor_para_selecionar):
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
                time.sleep(0.5)

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
        time.sleep(1) 
        

        # Lógica especifica para Material e Estilo
        if titulo_campo in ["Material", "Estilo"]:
            try:
                print(f"\n--- INICIANDO FLUXO DE CRIAÇÃO PARA {titulo_campo} ---")
                
                # Clicar em Adicionar
                xpath_add = "//div[contains(text(), 'Adicionar um novo item')] | //span[contains(., 'Adicionar um novo item')]"
                btn_add = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_add)))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn_add)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn_add)
                
                time.sleep(1) 

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

                time.sleep(1)

                # Confirmar 
                xpath_confirmar = "//ul//button"
                espera_click(driver, xpath_confirmar)
                time.sleep(DELAY_PADRAO)
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
                time.sleep(1.5) # Tempo para a lista filtrar
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

        time.sleep(0.5)

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
    el.click()
    return el

def espera_input(driver, xpath, timeout=10):
    el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].click();", el)
    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.BACK_SPACE)
    return el

def limpar_input(el):
    el.click()
    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.BACK_SPACE)
       

# ==============================================================================
# FUNÇÕES DO BOT
# ==============================================================================
def iniciar_driver():
    """Configura e retorna o driver do Chrome com o perfil carregado."""
    print("Iniciando Driver...")
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={CAMINHO_PERFIL}")
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")
    
    # Importante: Retornar o driver para quem chamou!
    driver = uc.Chrome(options=options, version_main=144)
    return driver

def preencher_dados_basicos(driver, caminho_imagem, nome_produto, nome_colecao):
    """
    PASSO 1: Faz upload da foto e preenche o nome do produto.
    """
    print("\n--- PASSO 1: DADOS BÁSICOS ---")
    wait = WebDriverWait(driver, 10)
    
    try:
        if os.path.exists(caminho_imagem):
            print("Procurando campo de upload...")
            campo_upload = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
            campo_upload.send_keys(caminho_imagem)
            esperar_upload_ou_matar(driver, timeout=5)
            print("Imagem enviada.")
        else:
            print(f"ERRO: Imagem não existe no caminho: {caminho_imagem}")
    except Exception as e:
        print(f"Erro no upload da imagem: {e}")

    # Nome
    nome_final = f"Impressão 3D - Miniatura RPG Taberna e Goblins - {nome_colecao} - {nome_produto} - Resina 3D"
    xpath_nome = "//input[@placeholder='Nome da Marca + Tipo do Produto + Atributos-chave (Materiais, Cores, Tamanho, Modelo)']"

    # Tentamos até 3 vezes preencher o nome
    for tentativa in range(3):
        try:
            print(f"Preenchendo nome (Tentativa {tentativa+1})...")
            
            # 1. Busca o elemento (Se deu stale antes, aqui ele pega a nova referência)
            campo_nome = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_nome)))
            
            # 2. Clica e Limpa
            campo_nome.click()
            campo_nome.send_keys(Keys.CONTROL + "a")
            campo_nome.send_keys(Keys.BACK_SPACE)
            
            # 3. Digita
            campo_nome.send_keys(nome_final)
            
            # Se chegou aqui sem erro, sai do loop
            print(f" -> Título preenchido com sucesso.")
            break 
            
        except StaleElementReferenceException:
            print("⚠️ Página atualizou. Tentando campo 'Nome' novamente...")
            time.sleep(2) 
        except Exception as e:
            print(f"❌ Erro genérico no nome: {e}")
            raise e 
    # 1.3 Botão Próximo
    print("Avançando para próxima tela...")
    time.sleep(DELAY_PADRAO) 
    xpath_botao = "//button[contains(., 'Next Step') or contains(., 'Próximo')]"
    
    try:
        # Tenta clicar no botão. Se falhar, tenta via JS
        botao_avancar = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_botao)))
        botao_avancar.click()
    except:
        try:
             driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, xpath_botao))
        except Exception as e:
             raise Exception(f"Botão Próximo não encontrado ou não clicável: {e}")

    print("Tela 1 finalizada.")

def selecionar_categoria(driver):
    """
    PASSO 2: Pesquisa a categoria e clica na hierarquia.
    """
    print("\n--- PASSO 2: CATEGORIA ---")
    wait = WebDriverWait(driver, 10)
    
    termo_alvo = "Figuras de Ação"
    hierarquia_para_clicar = ["Hobbies e Coleções", "Itens Colecionáveis", "Figuras de Ação"]
    xpath_categoria = "//div[contains(@class, 'product-category-box') or contains(@class, 'shopee-product-category-input')]"
    try:
        # Abrir seletor
        print("Abrindo seletor...")
        espera_click(driver, xpath_categoria, timeout=3)

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
            time.sleep(0.3)

        time.sleep(1.5)

        # Click swith de retirada
        try:
            xpath_switch_base = "//div[contains(@class,'logistics-item-ui-t1')][.//div[contains(normalize-space(.), 'Retirada')]]//div[contains(@class,'eds-switch')]"
            
            switch_el = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_switch_base)))
            
            classes_do_elemento = switch_el.get_attribute("class")
            
            if "eds-switch--open" in classes_do_elemento:
                print(" -> Switch Retirada estava ATIVADO. Desativando...")
                switch_el.click()
                time.sleep(0.5) 
                
        except Exception as e:
            print(f"Não foi possível verificar o switch de Retirada: {e}")

        # SOB ENCOMENDA 
        print("Configurando Pré-Encomenda")
        
        # Encontrando o botão "Sim" para Pré-encomenda
        try:
            xpath_sim = "//div[@data-product-edit-field-unique-id='preOrder']//label[.//span[normalize-space()='Sim']]"
            btn_sim = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_sim    )))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block : 'center'});", btn_sim)
            time.sleep(DELAY_PADRAO)
            btn_sim.click()
            print("Pré-encomenda ativada.")

        except Exception as e:
            print(f"Erro ao clicar em Sim: {e}")

        # Definindo 7 dias para pré-encomenda
        print(" -> Definindo 7 dias...")
        time.sleep(DELAY_PADRAO + 1)
        xpath_dias = "//div[contains(@class, 'pre-order-input')]//input[contains(@placeholder, '0')]"
        input_dias = espera_input(driver, xpath_dias)
        input_dias.send_keys("7")

        time.sleep(DELAY_PADRAO)
    except Exception as e:
        print(f"❌ Erro na sessão de envio: {e}")

    try:
        # SALVAR E NÃO PUBLICAR
        print(" -> Salvando...")
        
        # Clicando "Salvar e não publicar" da página
        xpath_salvar = "//div[contains(@class,'product-detail-button-wrapper')]//button[.//span[normalize-space()='Salvar e Não Publicar']]"
        espera_click(driver, xpath_salvar)

        # Clicando "Salvar e não publicar" do modal de confirmação
        xpath_salvar_modal = "//div[contains(@class,'eds-modal__footer')]//button[.//span[normalize-space()='Salvar e Não Publicar']]"
        espera_click(driver, xpath_salvar_modal)
        
        print("✅ Produto salvo no rascunho com sucesso!")

    except Exception as e:
        print(f"❌ Erro na etapa final: {e}")

# No arquivo bot_shopee.py

def cadastrar_produto_completo(driver, caminho_imagem, nome_produto, nome_colecao):
    """
    Função Wrapper que chama todos os passos do cadastro.
    """
    print(f"\n🚀 INICIANDO CADASTRO: {nome_produto} (Coleção: {nome_colecao})")
    
    # NAVEGAÇÃO FORÇADA (Reset de Estado)

    url_add = "https://seller.shopee.com.br/portal/product/new"
    driver.get(url_add)

    preencher_dados_basicos(driver, caminho_imagem, nome_produto, nome_colecao)

    selecionar_categoria(driver)
    
    preencher_atributos(driver, 
                        marca="Taberna e Goblins", 
                        material="Resin", 
                        peso="30g", 
                        estilo="Fantasy", 
                        quantidade=1)
    
    colar_descricao(driver)

    preencher_informacoes_finais(driver)
    
    print(f"✨ PRODUTO {nome_produto} FINALIZADO!")
    time.sleep(2) 

# ==============================================================================
# ORQUESTRADOR (MAIN)
# ==============================================================================
if __name__ == "__main__":
    
    NOME_DO_DIA = 'Beholder'
    FOTO_DO_DIA = os.path.abspath(f"images/teste_saida/Bite the bullet/{NOME_DO_DIA}.jpg")
    NOME_COLECAO = os.path.basename(os.path.dirname(FOTO_DO_DIA))
    # Iniciando
    driver = iniciar_driver()
    
    try:
        print("Acessando Shopee...")
        time.sleep(5)
    
        preencher_dados_basicos(driver, FOTO_DO_DIA, NOME_DO_DIA, NOME_COLECAO)
        
        selecionar_categoria(driver)
        
        preencher_atributos(driver, 
                            marca="Taberna e Goblins", 
                            material="Resin", 
                            peso="30g", 
                            estilo="Fantasy", 
                            quantidade=1)
        
        colar_descricao(driver)
        
        preencher_informacoes_finais(driver)
    
        print("\n✅ PROCESSO FINALIZADO COM SUCESSO!")
    except Exception as e:
        print(f"\n❌ ERRO FATAL NO MAIN: {e}")
        
    finally:
        print("\n🏁 Encerrando execução...")
        input("Pressione ENTER para fechar o navegador...")
        driver.quit()