from PIL import Image, ImageEnhance, ImageStat, ImageOps
import os
import re

# --- CONFIGURAÇÕES ---
PASTA_ENTRADA = "images/originais"
PASTA_SAIDA = "images/processadas"
CAMINHO_LOGO = "images/logo.png"

def otimizar_imagem(caminho_entrada, caminho_saida):
    """
    Redimensiona a imagem para no máximo 1024px e aplica compressão JPEG.
    """
    try:
        # 1. Abre a imagem
        with Image.open(caminho_entrada) as img:
            
            # 2. Converte para RGB (Obrigatório se a original for PNG com fundo transparente)
            # Se não fizer isso, o JPEG quebra porque não suporta transparência (Alpha Channel)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 3. Redimensiona mantendo a proporção (Thumbnail)
            # O método .thumbnail() é inteligente: ele só diminui se for maior que o limite.
            # Se a imagem for 500x500, ele não mexe. Se for 2500x2500, ele reduz pra 1024x1024.
            # Se for retangular (ex: 2000x1000), vira 1024x512. Ele nunca estica/deforma.
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # 4. Salva com Otimização
            # quality=85: O ponto ideal. Abaixo disso começa a ficar feio, acima disso não muda nada no olho humano.
            # optimize=True: O algoritmo gasta um tempinho extra pra achar a melhor compressão.
            img.save(caminho_saida, "JPEG", quality=85, optimize=True)
            
            print(f"✅ Imagem otimizada salva em: {caminho_saida}")
            
    except Exception as e:
        print(f"❌ Erro ao processar {caminho_entrada}: {e}")



# --- FUNÇÃO NOVA: PADRONIZAÇÃO QUADRADA ---
def tornar_quadrada(imagem_original, cor_fundo=(255, 255, 255)):
    """
    Cria um fundo quadrado branco e centraliza a imagem nele.
    Evita cortes e distorções em fotos verticais ou horizontais.
    """
    largura, altura = imagem_original.size
    
    # Define o tamanho do quadrado (o maior lado vence)
    novo_tamanho = max(largura, altura)
    
    # Cria uma tela em branco (RGB)
    imagem_final = Image.new("RGB", (novo_tamanho, novo_tamanho), cor_fundo)
    
    # Calcula a posição para colar no centro (Centralização)
    pos_x = (novo_tamanho - largura) // 2
    pos_y = (novo_tamanho - altura) // 2
    
    # Cola a imagem original sobre o fundo branco
    imagem_final.paste(imagem_original, (pos_x, pos_y))
    
    return imagem_final

# --- FUNÇÃO: SENSOR DE ESTACIONAMENTO (INTELIGÊNCIA VISUAL) ---
def verificar_area_ocupada(imagem_base, x, y, largura_logo, altura_logo, limiar_sensibilidade=50):
    box = (x, y, x + largura_logo, y + (altura_logo * 0.7))
    recorte = imagem_base.crop(box).convert("L")
    estatisticas = ImageStat.Stat(recorte)
    min_val, max_val = estatisticas.extrema[0]
    return (max_val - min_val) > limiar_sensibilidade

# --- FUNÇÃO: LIMPEZA DE NOME ---
def limpar_e_formatar_nome(nome_arquivo_sujo):
    nome = os.path.splitext(nome_arquivo_sujo)[0]
    if "-D-" in nome:
        nome = nome.split("-D-")[0]
    nome = nome.replace("_", " ")
    nome = re.sub(r'(?<!^)(?=[A-Z])', ' ', nome)
    return nome

# --- FUNÇÃO PRINCIPAL DE PROCESSAMENTO ---
def aplicar_marca_dagua_inteligente(caminho_imagem, caminho_logo, caminho_salvar):
    try:
        # 1. Abre a imagem original
        imagem = Image.open(caminho_imagem)
        
        # 2. Correção de Rotação (Importante para fotos de celular)
        imagem = ImageOps.exif_transpose(imagem)
        
        # 3. APLICA A PADRONIZAÇÃO QUADRADA (Aqui está a mágica!)
        # Convertemos para RGB antes para garantir que o fundo branco funcione bem
        imagem = tornar_quadrada(imagem.convert("RGB"), cor_fundo=(255, 255, 255))
        
        # Agora converte para RGBA para aceitar o logo transparente
        imagem = imagem.convert("RGBA")

        # 4. Prepara o Logo
        logo = Image.open(caminho_logo).convert("RGBA")

        # Redimensionar Logo (25% da largura da imagem JÁ quadrada)
        largura_base = imagem.width
        proporcao = (largura_base * 0.25) / float(logo.width)
        altura_nova = int((float(logo.height) * float(proporcao)))
        logo = logo.resize((int(largura_base * 0.25), altura_nova))
        
        lw, lh = logo.size
        alpha = logo.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.8)
        logo.putalpha(alpha)

        # 5. Lógica de Posição
        margem = 30
        margemEsq = 160
        
        # Canto Superior Direito (Padrão)
        pos1_x = largura_base - lw - margem
        pos1_y = margem
        
        # Checa se o canto direito está ocupado (sensor de contraste)
        # Nota: Como a imagem agora tem bordas brancas se for retangular,
        # o sensor vai ler o branco como "livre", o que é ótimo!
        if verificar_area_ocupada(imagem, pos1_x, pos1_y, lw, lh):
             # Se ocupado, move para Esquerda (descendo um pouco)
            pos2_x = margem
            pos2_y = margemEsq
            imagem.paste(logo, (pos2_x, pos2_y), logo)
        else:
            # Se livre, mantém na Direita
            imagem.paste(logo, (pos1_x, pos1_y), logo)

        # 6. Salva
        imagem.convert("RGB").save(caminho_salvar, "JPEG", quality=95)
        return True
    
    except Exception as e:
        print(f"   [ERRO] Falha em {caminho_imagem}: {e}")
        return False

# --- GERENTE DE ARQUIVOS (Mantive igual, com suporte a subpastas) ---
def processar_imagens():
    print("Iniciando processamento com PADRONIZAÇÃO 1:1...")
    for root, dirs, files in os.walk(PASTA_ENTRADA):
        
        caminho_relativo = os.path.relpath(root, PASTA_ENTRADA)
        pasta_destino_atual = os.path.join(PASTA_SAIDA, caminho_relativo)
        
        if not os.path.exists(pasta_destino_atual):
            os.makedirs(pasta_destino_atual)

        for arquivo in files:
            if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                caminho_completo_original = os.path.join(root, arquivo)
                
                nome_limpo = limpar_e_formatar_nome(arquivo)
                nome_final = f"{nome_limpo}.jpg"
                caminho_salvar = os.path.join(pasta_destino_atual, nome_final)
                
                contador = 1
                while os.path.exists(caminho_salvar):
                    nome_final = f"{nome_limpo} {contador}.jpg"
                    caminho_salvar = os.path.join(pasta_destino_atual, nome_final)
                    contador += 1

                print(f"Processando: {arquivo} -> Quadrada + Logo")
                aplicar_marca_dagua_inteligente(caminho_completo_original, CAMINHO_LOGO, caminho_salvar)

if __name__ == "__main__":
    if not os.path.exists(PASTA_ENTRADA):
        os.makedirs(PASTA_ENTRADA)
        print(f"Pasta '{PASTA_ENTRADA}' criada.")
    else:
        processar_imagens()