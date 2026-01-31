from PIL import Image, ImageEnhance, ImageStat, ImageOps
import os
import re

# ==============================================================================
# CONFIGURAÇÕES GERAIS
# ==============================================================================
PASTA_ENTRADA = "images/originais"
PASTA_SAIDA = "images/processadas"
CAMINHO_LOGO = "images/logo.png"
TAMANHO_MAXIMO = 1024  # Resolução alvo (ex: 1024x1024)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS (FERRAMENTAS)
# ==============================================================================

def limpar_e_formatar_nome(nome_arquivo_sujo):
    """Limpa caracteres estranhos e formata o nome para ficar bonito."""
    nome = os.path.splitext(nome_arquivo_sujo)[0]
    if "-D-" in nome:
        nome = nome.split("-D-")[0]
    nome = nome.replace("_", " ")
    nome = re.sub(r'(?<!^)(?=[A-Z])', ' ', nome)
    return nome

def verificar_area_ocupada(imagem_base, x, y, largura_logo, altura_logo, limiar_sensibilidade=50):
    """Verifica se a área onde o logo vai ficar já tem muita informação (contraste)."""
    box = (x, y, x + largura_logo, y + (altura_logo * 0.7))
    recorte = imagem_base.crop(box).convert("L")
    estatisticas = ImageStat.Stat(recorte)
    min_val, max_val = estatisticas.extrema[0]
    return (max_val - min_val) > limiar_sensibilidade

def tornar_quadrada(imagem_original, cor_fundo=(255, 255, 255)):
    """
    Cria um fundo quadrado e centraliza a imagem.
    CORREÇÃO: Suporta transparência colando corretamente sobre o branco.
    """
    largura, altura = imagem_original.size
    novo_tamanho = max(largura, altura)
    
    # 1. Cria o fundo branco
    imagem_final = Image.new("RGB", (novo_tamanho, novo_tamanho), cor_fundo)
    
    # 2. Calcula centro
    pos_x = (novo_tamanho - largura) // 2
    pos_y = (novo_tamanho - altura) // 2
    
    # 3. Cola a imagem original
    # SE a imagem tiver transparência (RGBA), usamos ela mesma como máscara
    if imagem_original.mode == 'RGBA':
        imagem_final.paste(imagem_original, (pos_x, pos_y), imagem_original)
    else:
        imagem_final.paste(imagem_original, (pos_x, pos_y))
    
    return imagem_final

# ==============================================================================
# O PROCESSADOR (A LINHA DE MONTAGEM)
# ==============================================================================

def processar_unica_imagem(caminho_entrada, caminho_saida, usar_logo=True):
    try:
        # 1. Abre e corrige rotação (ex: fotos de celular de cabeça pra baixo)
        img = Image.open(caminho_entrada)
        img = ImageOps.exif_transpose(img)
        
        # 2. Torna Quadrada (Isso já resolve o fundo transparente virando branco)
        # Convertemos para RGBA antes se for P (paleta) para garantir máscara correta
        if img.mode != 'RGBA' and img.mode != 'RGB':
            img = img.convert('RGBA')
            
        img = tornar_quadrada(img)
        
        # 3. REDIMENSIONA (OTIMIZAÇÃO DE TAMANHO) - AQUI ESTÁ O QUE VOCÊ QUERIA
        # Fazemos isso ANTES de botar o logo, para o logo ficar proporcional ao tamanho final
        img.thumbnail((TAMANHO_MAXIMO, TAMANHO_MAXIMO), Image.Resampling.LANCZOS)
        
        # 4. Aplica Marca D'água (Se solicitada e se o arquivo existir)
        if usar_logo and os.path.exists(CAMINHO_LOGO):
            img = img.convert("RGBA") # Precisa ser RGBA para camadas
            logo = Image.open(CAMINHO_LOGO).convert("RGBA")

            # Redimensiona Logo (25% da largura da imagem final)
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
            pos1_y = margem # Canto Superior Direito
            
            # Se tiver ocupado na direita, joga para esquerda
            if verificar_area_ocupada(img, pos1_x, pos1_y, lw, lh):
                pos2_x = margem
                pos2_y = 160
                img.paste(logo, (pos2_x, pos2_y), logo)
            else:
                img.paste(logo, (pos1_x, pos1_y), logo)

        # 5. Salva Final (Otimização de Bytes)
        # Convertemos para RGB final (remove canal alpha pois JPG não suporta)
        if not os.path.exists(os.path.dirname(caminho_saida)):
            os.makedirs(os.path.dirname(caminho_saida))

        img.convert("RGB").save(caminho_saida, "JPEG", quality=85, optimize=True)
        print(f"✅ Sucesso: {os.path.basename(caminho_saida)}")
        return True

    except Exception as e:
        print(f"❌ Erro em {os.path.basename(caminho_entrada)}: {e}")
        return False

def processar_toda_pasta():
    print(f"🚀 Iniciando processamento em massa de: {PASTA_ENTRADA}")
    for root, dirs, files in os.walk(PASTA_ENTRADA):
        
        # Cria a estrutura de pastas no destino
        caminho_relativo = os.path.relpath(root, PASTA_ENTRADA)
        pasta_destino_atual = os.path.join(PASTA_SAIDA, caminho_relativo)
        
        if not os.path.exists(pasta_destino_atual):
            os.makedirs(pasta_destino_atual)

        for arquivo in files:
            if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                caminho_completo = os.path.join(root, arquivo)
                
                # Gera nome limpo
                nome_limpo = limpar_e_formatar_nome(arquivo) + ".jpg"
                caminho_final = os.path.join(pasta_destino_atual, nome_limpo)
                
                # Evita sobrescrever (cria (1), (2) se necessário)
                # (Pode desativar isso se quiser forçar atualização)
                contador = 1
                temp_path = caminho_final
                while os.path.exists(temp_path):
                     # Dica: Descomente abaixo se quiser pular arquivos já feitos
                     # print(f"Pulando {arquivo} pois já existe."); break 
                     temp_path = os.path.join(pasta_destino_atual, f"{limpar_e_formatar_nome(arquivo)} {contador}.jpg")
                     contador += 1
                
                # Se decidiu processar:
                if contador == 1 or not os.path.exists(temp_path):
                     processar_unica_imagem(caminho_completo, temp_path)

# ==============================================================================
# ÁREA DE TESTES (MAIN)
# ==============================================================================
if __name__ == "__main__":
    # MODO 1: PROCESSAR TUDO (Normalmente comentado enquanto testa)
    # processar_toda_pasta()

    # MODO 2: TESTE ÚNICO (Para você validar o resize)
    print("🧪 Modo de Teste Unitário Ativado")
    
    # Defina aqui uma imagem que você TEM certeza que existe no seu PC agora
    # Dica: Use barras normais / mesmo no Windows, o Python entende.
    arquivo_teste = "images/originais/Unchained Dinasty/Shizuka_ShadowRonin_Main.jpg" 
    saida_teste = "images/teste_saida/resultado_teste.jpg"

    if os.path.exists(arquivo_teste):
        processar_unica_imagem(arquivo_teste, saida_teste)
        print("\nVerifique a pasta 'images/teste_saida'.")
        print("1. O tamanho do arquivo deve ser pequeno (Kb).")
        print("2. A resolução deve ser 1024x1024.")
        print("3. Se era PNG transparente, o fundo deve estar branco.")
    else:
        print(f"⚠️ Arquivo de teste não encontrado: {arquivo_teste}")
        print("Edite a variável 'arquivo_teste' no final do script.")