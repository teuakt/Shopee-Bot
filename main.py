import os
import shutil
import time
from tqdm import tqdm  
import keyboard  
import sys

def verificar_parada():
    """Verifica se a tecla de emergência (ESC) foi pressionada."""
    if keyboard.is_pressed('esc'):
        print("\n\n🛑 PARADA DE EMERGÊNCIA ACIONADA PELO USUÁRIO!")
        print("Finalizando processos com segurança...")
        sys.exit(0)

# --- IMPORTS DOS SEUS MÓDULOS ---
from bot_shopee import iniciar_driver, cadastrar_produto_completo

try:
    from processador_de_imagens import processar_unica_imagem 
except ImportError:
    def processar_imagem(entrada, saida):
        time.sleep(1)
        shutil.copy(entrada, saida)
        return True

# CONFIGURAÇÃO DE PASTAS 
BASE_DIR = os.getcwd()
DIR_RAW = os.path.join(BASE_DIR, "images", "originais")
DIR_PROC = os.path.join(BASE_DIR, "images", "processadas")
DIR_DONE = os.path.join(BASE_DIR, "images", "enviadas")

def garantir_pastas():
    for pasta in [DIR_RAW, DIR_PROC, DIR_DONE]:
        os.makedirs(pasta, exist_ok=True)

def fluxo_processamento():
    """Lê da pasta ORIGINAIS e salva na PROCESSADAS"""
    garantir_pastas()
    
    lista_tarefas = []
    
    # Varre a pasta de originais procurando subpastas
    for raiz, pastas, arquivos in os.walk(DIR_RAW):
        if raiz == DIR_RAW: continue # Pula arquivos soltos na raiz (opcional)
        
        nome_colecao = os.path.basename(raiz)
        imagens = [f for f in arquivos if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        for imagem in imagens:
            caminho_origem = os.path.join(raiz, imagem)
            lista_tarefas.append((caminho_origem, imagem, nome_colecao))

    if not lista_tarefas:
        print("⚠️  Nenhuma imagem encontrada nas subpastas de 'originais'.")
        return False

    print(f"\n🎨 Iniciando processamento de {len(lista_tarefas)} imagens...")

    with tqdm(total=len(lista_tarefas), desc="Processando", unit="img", colour="blue") as barra:
        for caminho_origem, nome_arquivo, nome_colecao in lista_tarefas:
            
            verificar_parada()
            
            pasta_destino = os.path.join(DIR_PROC, nome_colecao)
            os.makedirs(pasta_destino, exist_ok=True)
            
            try:
                caminho_final = processar_unica_imagem(caminho_origem, pasta_destino)
                
                if caminho_final:
                    novo_nome = os.path.basename(caminho_final)
                    tqdm.write(f"  ✅ Processado: {nome_colecao}/{novo_nome}")
                else:
                    tqdm.write(f"  ⚠️ Ignorado (Extensão inválida): {nome_arquivo}")

            except Exception as e:
                tqdm.write(f"  ❌ Erro em {nome_arquivo}: {e}")
            
            barra.update(1)
            
    print(f"\n✨ Processamento finalizado!")
    return True

def fluxo_cadastro():
    """Lê da pasta PROCESSADAS, cadastra na Shopee e move para ENVIADAS"""
    garantir_pastas()
    print(f"\nniciando varredura em: {DIR_PROC}")
    
    # Lista para guardar o trabalho a ser feito
    # Formato: (caminho_completo_imagem, nome_arquivo, nome_colecao)
    lista_tarefas = []

    # VARREDURA
    for raiz, pastas, arquivos in os.walk(DIR_PROC):
        # Se estivermos na raiz exata (images/processadas), pulamos, 
        # pois queremos apenas as subpastas (Coleções)
        if raiz == DIR_PROC:
            continue
            
        # O nome da pasta atual é o nome da coleção
        nome_colecao = os.path.basename(raiz)
        
        # Filtra imagens
        imagens = [f for f in arquivos if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        for imagem in imagens:
            caminho_completo = os.path.join(raiz, imagem)
            lista_tarefas.append((caminho_completo, imagem, nome_colecao))

    if not lista_tarefas:
        print("⚠️  Nenhuma imagem encontrada nas subpastas de 'processadas'.")
        return

    print(f"Encontrados {len(lista_tarefas)} produtos em diversas coleções.")
    
    # Inicia driver
    driver = iniciar_driver()
    
    try:
        driver.get("https://seller.shopee.com.br/portal/product/new")
        print("\nGARANTA QUE JA ESTEJA LOGADO NA CONTA DA SHOPEE SELLER! COMEÇANDO...")

        # Loop com Barra de Progresso
        with tqdm(total=len(lista_tarefas), desc="Cadastrando", unit="prod", colour="green") as barra:
            for caminho_img, nome_arquivo, nome_colecao in lista_tarefas:
                
                verificar_parada()

                nome_produto = os.path.splitext(nome_arquivo)[0]
                tqdm.write(f"\n➡️  Iniciando: {nome_produto} | Coleção: {nome_colecao}")

                try:
                    # CHAMA O BOT
                    cadastrar_produto_completo(driver, caminho_img, nome_produto, nome_colecao)
                    
                    # --- MOVER PARA ENVIADAS ---
                    pasta_destino_colecao = os.path.join(DIR_DONE, nome_colecao)
                    os.makedirs(pasta_destino_colecao, exist_ok=True)
                    
                    destino_final = os.path.join(pasta_destino_colecao, nome_arquivo)
                    shutil.move(caminho_img, destino_final)
                    
                    tqdm.write(f"  ✅ Sucesso! Movido para: enviadas/{nome_colecao}")

                except Exception as e:
                    tqdm.write(f"  ❌ Falha ao cadastrar {nome_produto}: {e}")
                
                barra.update(1)

    except KeyboardInterrupt:
        print("\n🛑 Parado pelo usuário.")
    finally:
        print("\n🏁 Sessão de cadastro encerrada.")

def menu_principal():
    while True:
        print("\n" + "="*40)
        print("      MENU PRINCIPAL - Automação Loja Shopee")
        print("="*40)
        print("1. Processar Imagens (Originais -> Processadas)")
        print("2. Cadastrar Produtos (Processadas -> Shopee)")
        print("3. ❌ Sair")
        
        opcao = input("\nEscolha uma opção (1-3): ").strip()

        if opcao == "1":
            tem_arquivos = fluxo_processamento()
            if tem_arquivos:
                resp = input("\nDesceja CADASTRAR os produtos processados agora? (s/n): ").lower()
                if resp == 's':
                    fluxo_cadastro()
        
        elif opcao == "2":
            fluxo_cadastro()
            
        elif opcao == "3":
            print("Saindo... Até mais!")
            break
            
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\nEncerrando programa...")
