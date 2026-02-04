import os
import json
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- MODELOS (Mantemos os mesmos, são ótimos) ---
class ImagemDetalhe(BaseModel):
    filename: str = Field(description="Nome EXATO do arquivo original (incluindo extensão)")
    view_type: str = Field(description="Visão (front, back, side, detail)")

class VariacaoProduto(BaseModel):
    variation_name: str = Field(description="Nome da variação ou 'Padrão'")
    images: list[ImagemDetalhe]

class ProdutoRPG(BaseModel):
    collection_name: str = Field(description="Nome da coleção extraído da parte antes da barra '/'")
    product_name: str = Field(description="Nome do produto traduzido/processado")
    variations: list[VariacaoProduto]

# --- FUNÇÃO ÚNICA DE PROCESSAMENTO ---
def gerar_mapa_unificado(pasta_raiz_originais, arquivo_saida="mapa_global.json"):
    print(f"🚀 Escaneando TODAS as coleções em: {pasta_raiz_originais}")
    
    # 1. Agregação de Arquivos (Flattening)
    lista_arquivos_com_caminho = []
    
    pastas_colecoes = [d for d in os.listdir(pasta_raiz_originais) 
                       if os.path.isdir(os.path.join(pasta_raiz_originais, d))]

    if not pastas_colecoes:
        print("⚠️ Nenhuma pasta encontrada.")
        return

    for nome_colecao in pastas_colecoes:
        caminho_colecao = os.path.join(pasta_raiz_originais, nome_colecao)
        arquivos = [f for f in os.listdir(caminho_colecao) 
                    if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
        
        # Aqui criamos o formato "Colecao/Arquivo.jpg"
        for arq in arquivos:
            lista_arquivos_com_caminho.append(f"{nome_colecao}/{arq}")

    total_arquivos = len(lista_arquivos_com_caminho)
    if total_arquivos == 0:
        print("⚠️ Nenhum arquivo de imagem encontrado.")
        return

    print(f"📦 Payload preparado: {total_arquivos} arquivos de {len(pastas_colecoes)} coleções.")
    print(f"🤖 Enviando TUDO para o Gemini (Batch Request)...")

    # 2. O Prompt Unificado
    prompt = f"""
    # Role
    Você é um especialista em catalogação de E-commerce para RPG (Shopee/Amazon).

    # Task
    Analise a lista de arquivos abaixo e preencha a estrutura JSON hierárquica fornecida.
    
    # Regras de Extração (CRÍTICO)
    1. O texto ANTES da primeira barra "/" é o 'collection_name'.
    2. O texto DEPOIS da barra é o arquivo a ser analisado.

    # Regras de Agrupamento
    1. Separe por Coleção (ex: "BB - IM/Beholder", Coleção = BB - IM).
    2. Agrupe por Produto (ex: "Colossus_Shot1" e "Colossus_Shot2" -> Produto "Colosso").
    3. Detecte Variações (ex: "Axe", "Bow" criam variações separadas. Se for só ângulo, use "Padrão").
    4. Classifique a Visão (ex: "front", "back", "side", "close_up", "showcase").
    5. Algumas possuem, como um dos ultimos nomes, palavras como 'Black' ou 'Red' que indicam 
    variações de cor de fundo, o que nao é relevante.
  
    # Regras de Tradução (CRÍTICO)
    - Criaturas genéricas -> TRADUZIR para PT-BR (Human Mage -> Mago Humano).
    - Nomes Próprios/Clássicos -> MANTER em Inglês (Beholder, Lich).
    - Exemplos: "Dragon" = "Dragão", "Dwarf" = "Anão", "Elf" = "Elfo", "Owlbear" = "Urso-Coruja", etc.
    - Use sempre nomes comuns em RPG de mesa, como livros do d&d e etc.
    - Se estiver em dúvida, mantenha o nome em Inglês.
    - Separe nomes compostos com hífen (ex: "Dragonborn" = "Dracônico", 'Owlbear' = "Urso-Coruja"). 

    # Lista de Arquivos para Processar:
    {json.dumps(lista_arquivos_com_caminho, indent=2)}
    """

    try:
        # Chamada ÚNICA
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[ProdutoRPG]
            }
        )
        
        dados = json.loads(response.text)
        
        # 3. Salvar
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
            
        print(f"\n🌎 MAPA GLOBAL GERADO!")
        print(f"Produtos identificados: {len(dados)}")
        print(f"Salvo em: {arquivo_saida}")
        return dados

    except Exception as e:
        print(f"❌ Erro Fatal no Batch: {e}")
        return []

if __name__ == "__main__":
    gerar_mapa_unificado("./images/originais")
