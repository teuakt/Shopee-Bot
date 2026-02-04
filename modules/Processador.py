from PIL import Image, ImageEnhance, ImageStat, ImageOps
import os
import re
import json

# CONFIGURAÇÕES GERAIS

PASTA_ENTRADA = "./images/originais"
PASTA_SAIDA = "./images/processadas"
CAMINHO_LOGO = "./resources/logo.png"
TAMANHO_MAXIMO = 1024

# FUNÇÕES AUXILIARES

def verificar_area_ocupada(imagem_base, x, y, largura_logo, altura_logo, limiar_sensibilidade=50):
    """Verifica se a área onde o logo vai ficar já tem muita informação, se sim, retorna True."""
    box = (x, y, x + largura_logo, y + (altura_logo * 0.7))
    recorte = imagem_base.crop(box).convert("L")
    estatisticas = ImageStat.Stat(recorte)
    min_val, max_val = estatisticas.extrema[0]
    return (max_val - min_val) > limiar_sensibilidade

def tornar_quadrada(imagem_original, cor_fundo=(255, 255, 255)):
    """ Cria um fundo quadrado e centraliza a imagem, mantendo sempre a proporção 1:1, independente
        da imagem."""

    largura, altura = imagem_original.size
    novo_tamanho = max(largura, altura)

    imagem_final = Image.new("RGB", (novo_tamanho, novo_tamanho), cor_fundo)
    
    # Centralização
    pos_x = (novo_tamanho - largura) // 2
    pos_y = (novo_tamanho - altura) // 2
    
    # Usa a próprima imagem como máscara se houver transparência
    if imagem_original.mode == 'RGBA':
        imagem_final.paste(imagem_original, (pos_x, pos_y), imagem_original)
    else:
        imagem_final.paste(imagem_original, (pos_x, pos_y))
    
    return imagem_final

def sanitarizar_nome(nome):
    """Remove caracteres proibidos pelo Windows/Linux"""
    return re.sub(r'[<>:"/\\|?*]', '', nome).strip()

# O PROCESSADOR 

def processar_imagem_unica(caminho_entrada, caminho_saida_completo, usar_logo=True):
    if os.path.exists(caminho_saida_completo):
        print(f" -> Já existe: {os.path.basename(caminho_saida_completo)}")
        return

    try:
        img = Image.open(caminho_entrada)
        img = ImageOps.exif_transpose(img)
        
        # Conversão para RGBA para lidar com transparência
        if img.mode != 'RGBA' and img.mode != 'RGB':
            img = img.convert('RGBA')
            
        img = tornar_quadrada(img)
        
        # Redimensiona para o tamanho máximo
        img.thumbnail((TAMANHO_MAXIMO, TAMANHO_MAXIMO), Image.Resampling.LANCZOS)
        
        # Aplicação de logo
        if usar_logo and os.path.exists(CAMINHO_LOGO):
            img = img.convert("RGBA")
            logo = Image.open(CAMINHO_LOGO).convert("RGBA")

            # Redimensiona o Logo proporcionalmente
            largura_base = img.width
            proporcao = (largura_base * 0.25) / float(logo.width)
            altura_nova = int((float(logo.height) * float(proporcao)))
            logo = logo.resize((int(largura_base * 0.25), altura_nova), Image.Resampling.LANCZOS)
            
            # Transparência do Logo
            alpha = logo.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(0.8)
            logo.putalpha(alpha)

            # Lógica de Posição
            lw, lh = logo.size
            margem = 30
            pos1_x = largura_base - lw - margem
            pos1_y = margem 
            
            # Se tiver ocupado na direita, joga para esquerda
            if verificar_area_ocupada(img, pos1_x, pos1_y, lw, lh):
                pos2_x = margem
                pos2_y = 160
                img.paste(logo, (pos2_x, pos2_y), logo)
            else:
                img.paste(logo, (pos1_x, pos1_y), logo)

        # Conversão para RGB
        if not os.path.exists(caminho_saida_completo):
            os.makedirs(os.path.dirname(caminho_saida_completo), exist_ok=True)

        img.convert("RGB").save(caminho_saida_completo, "JPEG", quality=85, optimize=True)
        print(f"Sucesso: {os.path.basename(caminho_saida_completo)}")

    except Exception as e:
        print(f"Erro em {os.path.basename(caminho_entrada)}: {e}")

def executar_pipeline(json_dados):
    print(f"🚀 Iniciando processamento em massa...")
    
    erros = 0
    sucessos = 0

    for produto in json_dados:
        # Pega a Coleção direto do JSON (Sua Fonte da Verdade)
        nome_colecao_origem = produto.get('collection_name', '').strip()
        nome_produto = sanitarizar_nome(produto['product_name'])
        
        for variacao in produto['variations']:
            nome_variacao = sanitarizar_nome(variacao['variation_name'])
            
            for imagem_info in variacao['images']:
                # PROBLEMA ANTIGO: imagem_info['filename'] vinha como "Colecao/Arquivo.jpg"
                # SOLUÇÃO: Usamos os.path.basename para pegar só "Arquivo.jpg"
                arquivo_bruto = imagem_info['filename']
                nome_arquivo_puro = os.path.basename(arquivo_bruto) 

                # MONTAGEM DIRETA DO CAMINHO (Sem "localizar_arquivo")
                # Caminho = ./images/originais / NomeColecao / NomeArquivo.jpg
                caminho_origem = os.path.join(PASTA_ENTRADA, nome_colecao_origem, nome_arquivo_puro)
                
                # Definindo nome final
                tipo_visao = imagem_info['view_type']
                if nome_variacao.lower() in ["padrão", "padrao", "default", "standard"]:
                    novo_nome = f"{nome_produto} - {tipo_visao}.jpg"
                else:
                    novo_nome = f"{nome_produto} - {nome_variacao} - {tipo_visao}.jpg"

                # Define destino: ./images/processadas / NomeColecao / NovoNome.jpg
                pasta_destino_colecao = os.path.join(PASTA_SAIDA, sanitarizar_nome(nome_colecao_origem))
                caminho_destino = os.path.join(pasta_destino_colecao, novo_nome)

                # Verifica existência
                if os.path.exists(caminho_origem):
                    processar_imagem_unica(caminho_origem, caminho_destino)
                    sucessos += 1
                else:
                    # Tentativa de fallback: às vezes o nome da coleção no JSON vem um pouco diferente da pasta
                    print(f"⚠️ Arquivo não encontrado: {caminho_origem}")
                    print(f"   (Buscado em: {nome_colecao_origem} -> {nome_arquivo_puro})")
                    erros += 1

    print(f"\n🏁 Relatório Final: {sucessos} processados, {erros} erros.")
 
 
# Testes
if __name__ == "__main__":
    if not os.path.exists(PASTA_ENTRADA):
        print(f"Erro: A pasta {PASTA_ENTRADA} não existe.")
    else:
        try:
            with open("mapa_global.json", "r", encoding="utf-8") as f:
                dados = json.load(f)
            executar_pipeline(dados)
        except FileNotFoundError:
            print("❌ Arquivo 'mapa_global.json' não encontrado. Rode o organizador primeiro.")