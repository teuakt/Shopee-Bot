import os
import sys
import time
import json
from colorama import init, Fore, Style

from app import Organizador
from app import Processador
from app import Cadastrador

# Configurações
PASTA_ORIGINAIS = "./data/input"
ARQUIVO_MAPA = "mapa_global.json"

# Inicializa cores (funciona no CMD do Windows)
init(autoreset=True)

def organizar():
    print(f"\n{Fore.CYAN}=== PASSO 1: ORGANIZAÇÃO & IA ==={Style.RESET_ALL}")
    print(f"Lendo imagens de: {PASTA_ORIGINAIS}")
    
    if not os.path.exists(PASTA_ORIGINAIS):
        print(f"{Fore.RED}❌ Pasta 'data/input' não encontrada!{Style.RESET_ALL}")
        return None

    # Chama a função do Organizador que gera o JSON
    dados = Organizador.gerar_mapa_unificado(PASTA_ORIGINAIS, ARQUIVO_MAPA)
    
    if dados:
        print(f"{Fore.GREEN}✅ Mapa gerado com {len(dados)} produtos!{Style.RESET_ALL}")
        return dados
    else:
        print(f"{Fore.RED}❌ Falha ao gerar mapa.{Style.RESET_ALL}")
        return None

def processar():
    print(f"\n{Fore.CYAN}=== PASSO 2: PROCESSAMENTO DE IMAGENS ==={Style.RESET_ALL}")
    
    if not os.path.exists(ARQUIVO_MAPA):
        print(f"{Fore.YELLOW}⚠️ Arquivo '{ARQUIVO_MAPA}' não encontrado.{Style.RESET_ALL}")
        print("Rodando o Passo 1 automaticamente...")
        dados = organizar()
        if not dados: return
    else:
        with open(ARQUIVO_MAPA, "r", encoding="utf-8") as f:
            dados = json.load(f)

    # Chama o pipeline do Processador
    Processador.executar_pipeline(dados)
    print(f"{Fore.GREEN}✅ Imagens processadas e prontas!{Style.RESET_ALL}")

def cadastrar():
    print(f"\n{Fore.CYAN}=== PASSO 3: CADASTRO NA SHOPEE ==={Style.RESET_ALL}")
    
    if not os.path.exists(ARQUIVO_MAPA):
        print(f"{Fore.RED}❌ Mapa não encontrado. Rode o passo 1 e 2 primeiro.{Style.RESET_ALL}")
        return

    print("\nComo deseja rodar o navegador?")
    print("1.  Modo VISÍVEL (Ideal para acompanhar ou fazer login)")
    print("2.  Modo INVISÍVEL (Headless - Roda em 2º plano)")
    
    escolha = input(f"{Fore.WHITE}Escolha (1 ou 2): {Style.RESET_ALL}").strip()
    
    modo_invisivel = False
    if escolha == "2":
        modo_invisivel = True
        print(f"\n{Fore.YELLOW}⚠️  AVISO: No modo invisível você NÃO consegue fazer login manual.")
        print(f"Certifique-se de já ter rodado o modo Visível uma vez para salvar sua sessão.{Style.RESET_ALL}")
        print("Iniciando em 3 segundos...")
        time.sleep(3)

    print(f"\n{Fore.GREEN}🚀 Iniciando o Robô...{Style.RESET_ALL}")
    
    try:
        Cadastrador.executar_bot(headless=modo_invisivel)
    except Exception as e:
        print(f"{Fore.RED}❌ Ocorreu um erro fatal no bot: {e}{Style.RESET_ALL}")

def menu_principal():
    while True:
        print(f"\n{Fore.YELLOW}{'='*40}")
        print(f"   🤖  AUTOMAÇÃO SHOPEE v2.0")
        print(f"{'='*40}{Style.RESET_ALL}")
        print("1. 🧠  Organizar (Ler Originais + Gemini AI)")
        print("2. 🎨  Processar (Recortar + Logo + Padronizar)")
        print("3. 🚀  Cadastrar (Bot Selenium)")
        print(f"{Fore.BLUE}4. ⚡  RODAR TUDO (Pipeline Completo){Style.RESET_ALL}")
        print("0. ❌  Sair")
        
        opcao = input(f"\n{Fore.WHITE}Escolha uma opção: {Style.RESET_ALL}").strip()

        if opcao == "1":
            organizar()
            input("\nEnter para voltar...")
        
        elif opcao == "2":
            processar()
            input("\nEnter para voltar...")
        
        elif opcao == "3":
            cadastrar()
            # O Cadastrador já tem seu próprio 'Enter para sair'
        
        elif opcao == "4":
            print(f"\n{Fore.MAGENTA}🚀 INICIANDO MODO TURBO...{Style.RESET_ALL}")
            dados = organizar()
            if dados:
                processar()
                resp = input("\nIniciar o cadastro agora? (S/N): ").lower()
                if resp == 's':
                    cadastrar()
        
        elif opcao == "0":
            print("Até logo!")
            break
        
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\nPrograma encerrado.")