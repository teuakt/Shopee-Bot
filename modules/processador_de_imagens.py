from PIL import Image, ImageEnhance, ImageStat, ImageOps
import os
import re


# CONFIGURAÇÕES GERAIS

PASTA_ENTRADA = "./images/originais"
PASTA_SAIDA = "./images/processadas"
CAMINHO_LOGO = "./images/logo.png"
TAMANHO_MAXIMO = 1024 

# FUNÇÕES UTILITÁRIAS

def limpar_e_formatar_nome(nome_arquivo_sujo):
    """Limpa caracteres estranhos e formata o nome para padronizado, 
       facilitando a identificação de produtos."""
    nome = os.path.splitext(nome_arquivo_sujo)[0]
    if "-D-" in nome:
        nome = nome.split("-D-")[0]
    nome = nome.replace("_", " ")
    nome = re.sub(r'(?<!^)(?=[A-Z])', ' ', nome)
    return nome

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

def processar_unica_imagem(caminho_entrada, pasta_destino, usar_logo=True):
    # Filtro de Extensão 
    if not caminho_entrada.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return None 

    # Prepara o nome limpo e caminho final
    nome_original = os.path.basename(caminho_entrada)
    nome_limpo = limpar_e_formatar_nome(nome_original) + ".jpg"
    
    caminho_saida_final = os.path.join(pasta_destino, nome_limpo)

    # Verifica Duplicata 
    if os.path.exists(caminho_saida_final):
        print(f"  -> Pulando {nome_limpo} (Já existe).")
        return caminho_saida_final
    
    try:
        # Abre a imagem e corrige caso haja rotação via EXIF
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
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino)

        img.convert("RGB").save(caminho_saida_final, "JPEG", quality=85, optimize=True)
        print(f"Sucesso: {os.path.basename(pasta_destino)}")
        return caminho_saida_final

    except Exception as e:
        print(f"Erro em {os.path.basename(caminho_entrada)}: {e}")
        return None 


# Testes
if __name__ == "__main__":
    # Processar tudo

    # Teste unitário em uma imagem específica
    print("🧪 Modo de Teste Unitário Ativado")
    
    # Path da pasta de teste
    pasta_entrada_teste = "./images/processadas/Bite the bullet/" 
    pasta_saida_teste = "./images/teste_saida/"
    processar_unica_imagem(os.path.join(pasta_entrada_teste, "Anathema.jpg"), os.path.join(pasta_saida_teste, "teste_saida.jpg"))
    

    if os.path.exists(pasta_entrada_teste):
        for f in os.listdir(pasta_entrada_teste):
            arquivo_teste = os.path.join(pasta_entrada_teste, f)
            saida_teste = os.path.join(pasta_saida_teste, limpar_e_formatar_nome(f) + ".jpg")
            processar_unica_imagem(arquivo_teste, saida_teste)
    else:
        print(f"Pasta de teste não encontrada: {pasta_entrada_teste}")
        print("Edite a variável 'pasta_entrada_teste' no final do script.")