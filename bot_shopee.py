import os
import time
import pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys

# ==============================================================================
# CONFIGURAÇÕES (CONSTANTES)
# ==============================================================================
DELAY_PADRAO = 1.5
CAMINHO_PROJETO = os.getcwd()
CAMINHO_PERFIL = os.path.join(CAMINHO_PROJETO, "Perfil_Bot_Shopee")

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
  
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
            campo_select = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_campo)))
        else:
            xpath_campo = f"//div[contains(@class, 'attribute-select-item')][.//div[contains(@class, 'edit-label') and contains(., '{titulo_campo}')]]//div[contains(@class, 'edit-row-right-medium')]"
            campo_select = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_campo)))
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", campo_select)
        time.sleep(1)
        campo_select.click()
        
        # ======================================================================
        # LÓGICA TIPO A: CRIAR NOVO ITEM (Material, Estilo)
        # ======================================================================
        # CORREÇÃO AQUI: Usamos 'in' para verificar se está na lista
        if titulo_campo in ["Material", "Estilo"]:
            try:
                print(f"\n--- INICIANDO FLUXO DE CRIAÇÃO PARA {titulo_campo} ---")
                
                # Passo 1: Clicar em Adicionar
                xpath_add = "//div[contains(text(), 'Adicionar um novo item')] | //span[contains(., 'Adicionar um novo item')]"
                btn_add = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_add)))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn_add)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn_add)
                
                time.sleep(1) 

                # Passo 2: Digitar no input dentro da UL
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

                # Passo 3: Confirmar (Botão dentro da UL)
                xpath_confirmar = "//ul//button"
                btn_confirmar = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_confirmar)))
                driver.execute_script("arguments[0].click();", btn_confirmar)
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
                input_busca = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath_busca)))

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
                opcao_final = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_opcao)))
                opcao_final.click()
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
        

# ==============================================================================
# FUNÇÕES DO BOT (MÓDULOS)
# ==============================================================================
def iniciar_driver():
    """Configura e retorna o driver do Chrome com o perfil carregado."""
    print("🚗 Iniciando Driver...")
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={CAMINHO_PERFIL}")
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")
    
    # Importante: Retornar o driver para quem chamou!
    driver = uc.Chrome(options=options, version_main=144)
    return driver

def preencher_dados_basicos(driver, caminho_imagem, nome_produto):
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
            print("Imagem enviada.")
            time.sleep(DELAY_PADRAO)
        else:
            print(f"ERRO: Imagem não existe no caminho: {caminho_imagem}")
    except Exception as e:
        print(f"Erro no upload da imagem: {e}")

    # 1.2 Nome
    try:
        print("Preenchendo nome...")
        xpath_nome = "//input[@placeholder='Nome da Marca + Tipo do Produto + Atributos-chave (Materiais, Cores, Tamanho, Modelo)']"
        campo_nome = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_nome)))
        campo_nome.click()
        campo_nome.clear()
        campo_nome.send_keys(f"Miniatura RPG Taberna e Goblins {nome_produto} - Resina 3D")
    except Exception as e:
        print(f"Erro no nome: {e}")
    
    # 1.3 Botão Próximo
    print("Avançando para próxima tela...")
    time.sleep(DELAY_PADRAO) 
    xpath_botao = "//button[contains(., 'Next Step') or contains(., 'Próximo')]"
    
    try:
        botao_avancar = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_botao)))
        botao_avancar.click()
    except:
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, xpath_botao))

    print("Tela 1 finalizada.")

def selecionar_categoria(driver):
    """
    PASSO 2: Pesquisa a categoria e clica na hierarquia.
    """
    print("\n--- PASSO 2: CATEGORIA ---")
    wait = WebDriverWait(driver, 10)
    
    termo_alvo = "Figuras de Ação"
    hierarquia_para_clicar = ["Hobbies e Coleções", "Itens Colecionáveis", "Figuras de Ação"]

    try:
        wait_curto = WebDriverWait(driver, DELAY_PADRAO)  

        # Abrir seletor
        print("Abrindo seletor...")
        botao_categoria = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'product-category-box') or contains(@class, 'shopee-product-category-input')]")
        ))
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", botao_categoria)
        botao_categoria.click()
        time.sleep(DELAY_PADRAO) 

        # Verificar sugestão
        print(f"Verificando se '{termo_alvo}' já apareceu como sugestão...")
        sugestao_encontrada = False
        try:
            xpath_sugestao = f"//li[contains(., '{termo_alvo}')]"
            item_sugestao = wait_curto.until(EC.element_to_be_clickable((By.XPATH, xpath_sugestao)))
            item_sugestao.click()
            print("SUGESTÃO DA SHOPEE ENCONTRADA E CLICADA!")
            sugestao_encontrada = True
        except:
            print("Sugestão não encontrada. Iniciando busca manual...")
            sugestao_encontrada = False 

        # Busca Manual se não achou sugestão
        if not sugestao_encontrada:

            print(f"Digitando '{termo_alvo}' no input...")
            input_busca = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//input[contains(@placeholder, 'Insira ao menos')]")
            ))
            input_busca.click()
            input_busca.clear()
            input_busca.send_keys(termo_alvo)

            time.sleep(DELAY_PADRAO*2) 

            # B. Loop na Hierarquia
            print("Navegando pelas colunas filtradas...")
            for item_nome in hierarquia_para_clicar:
                print(f"   -> Procurando: {item_nome}")
                
                # XPath Híbrido: LI ou DIV Option
                xpath_item = f"//li[contains(., '{item_nome}')]"
                
                opcao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_item)))
                opcao.click()
                time.sleep(DELAY_PADRAO) # Pausa entre colunas

        # Confirmando Categoria
        print("Finalizando Categoria...")
        try:
            btn_confirmar = WebDriverWait(driver, 2).until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Confirmar')]")
            ))
            btn_confirmar.click()
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
        time.sleep(DELAY_PADRAO)

def colar_descricao(driver):
    pass


# ==============================================================================
# ORQUESTRADOR (MAIN)
# ==============================================================================
if __name__ == "__main__":
    
    NOME_DO_DIA = 'Anathema'
    FOTO_DO_DIA = os.path.abspath(f"images/processadas/Bite the bullet/{NOME_DO_DIA}.jpg")
    
    # Iniciando
    driver = iniciar_driver()
    
    try:
        print("Acessando Shopee...")
        time.sleep(5)
    
        preencher_dados_basicos(driver, FOTO_DO_DIA, NOME_DO_DIA)
        
        selecionar_categoria(driver)
        
        preencher_atributos(driver, 
                            marca="Taberna e Goblins", 
                            material="Resin", 
                            peso="30g", 
                            estilo="Fantasy", 
                            quantidade=1)
        
        colar_descricao(driver)
        
        print("\n✅ PROCESSO FINALIZADO COM SUCESSO!")

    except Exception as e:
        print(f"\n❌ ERRO FATAL NO MAIN: {e}")
        
    finally:
        print("\n🏁 Encerrando execução...")
        input("Pressione ENTER para fechar o navegador...")
        driver.quit()