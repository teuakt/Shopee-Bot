from PIL import Image, ImageEnhance, ImageStat, ImageOps
import os
import re
import json

# CONFIGURAÇÕES GERAIS

PASTA_ENTRADA = "./app/input"
PASTA_SAIDA = "./app/processed"
CAMINHO_LOGO = "./assets/logo.png"
TAMANHO_MAXIMO = 1024

# FUNÇÕES AUXILIARES
def sanitarizar_nome(nome):
    """Remove caracteres proibidos pelo Windows/Linux"""
    return re.sub(r'[<>:"/\\|?*]', '', nome).strip()

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
    print(f"🚀 Iniciando processamento obediente...")
    
    for produto in json_dados:
        # A coleção continua vindo do JSON
        nome_colecao_safe = sanitarizar_nome(produto.get('collection_name', 'Geral'))
        
        # Cria a pasta da coleção no destino
        pasta_destino_colecao = os.path.join(PASTA_SAIDA, nome_colecao_safe)
        
        for variacao in produto['variations']:
            for imagem_info in variacao['images']:
                
                # 1. ONDE ESTÁ? (Origem)
                nome_arquivo_origem = os.path.basename(imagem_info['filename'])
                caminho_origem = os.path.join(PASTA_ENTRADA, nome_colecao_safe, nome_arquivo_origem)
                
                # 2. PARA ONDE VAI? (Destino baseado no Organizador)
                # O Processador não calcula mais nada, só lê 'target_filename'
                novo_nome = imagem_info.get('target_filename')
                
                if not novo_nome:
                    print(f"⚠️ Erro: JSON sem 'target_filename' para {nome_arquivo_origem}")
                    continue

                caminho_destino = os.path.join(pasta_destino_colecao, novo_nome)
                
                # 3. Executa
                if os.path.exists(caminho_origem):
                    sucesso = processar_imagem_unica(caminho_origem, caminho_destino) # Sua função visual
                    
                    # Se deu certo, atualizamos o path final para o Bot saber
                    if sucesso: # Assumindo que sua função retorna algo, ou verificamos exists depois
                        imagem_info['processed_path'] = caminho_destino
                else:
                    print(f"⚠️ Origem não encontrada: {caminho_origem}")

 
 
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
