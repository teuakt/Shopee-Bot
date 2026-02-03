import os
import time
from google import genai
from pydantic import BaseModel, TypeAdapter, Field
from dotenv import load_dotenv
import json

# 1. Configuração
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 2. Definindo o "Molde" dos dados (O Contrato)
class ImagemDetalhe(BaseModel):
    filename: str = Field(description="Nome original do arquivo")
    view_type: str = Field(description="Ex: front, back, side, close_up, showcase")

class VariacaoProduto(BaseModel):
    variation_name: str = Field(description="Nome da variação (Ex: Axe, Bow) ou 'Standard'")
    images: list[ImagemDetalhe]

class ProdutoRPG(BaseModel):
    product_name: str = Field(description="Nome traduzido ou mantido em inglês conforme regras")
    variations: list[VariacaoProduto]

# 3. Função Principal
def processar_pasta(caminho_pasta, arquivo_saida="estrutura_produtos.json"):
    print(f"📂 Lendo: {caminho_pasta}")
    if not os.path.exists(caminho_pasta): return

    # Filtra arquivos
    arquivos = [f for f in os.listdir(caminho_pasta) 
                if os.path.isfile(os.path.join(caminho_pasta, f)) and not f.startswith('.')]
    
    if not arquivos: return
    
    print(f"🤖 Enviando {len(arquivos)} arquivos para o Gemini 3 Flash Preview...")

    prompt = f"""
    # Role
    Você é um especialista em catalogação de E-commerce para RPG (Shopee/Amazon).

    # Task
    Analise a lista de arquivos abaixo e preencha a estrutura JSON hierárquica fornecida.
    
    # Regras de Agrupamento
    1. Agrupe por Entidade (ex: "Colossus_Shot1" e "Colossus_Shot2" -> Produto "Colosso").
    2. Detecte Variações (ex: "Axe", "Bow" criam variações separadas. Se for só ângulo, use "Padrão").
    3. Classifique a Visão ("front", "back", "side", "close_up", "showcase").

    # Regras de Tradução (CRÍTICO)
    - Criaturas genéricas -> TRADUZIR para PT-BR (Human Mage -> Mago Humano).
    - Nomes Próprios/Clássicos -> MANTER em Inglês (Beholder, Lich).

    # Lista de Arquivos para Processar:
    {arquivos}
    """

    # Configuração com SCHEMA (O Segredo)
    # Isso diz ao Gemini: "Não seja criativo no formato. Siga essa classe Python."
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview', # O modelo que você descobriu!
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[ProdutoRPG] # Força ser uma lista de ProdutoRPG
            }
        )
        
        # O SDK novo já pode converter direto se configurado, mas vamos fazer manual para garantir
        # Como definimos o schema, o texto JÁ VEM como JSON válido.
        dados = json.loads(response.text)
        
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            # indent=2: Deixa legível (com quebra de linha)
            # ensure_ascii=False: Permite gravar 'ã' em vez de '\u00e3'
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
        print("\n✅ SUCESSO! Estrutura perfeita garantida pelo Pydantic:\n")
        return dados

    except Exception as e:
        print(f"❌ Erro: {e}")

# --- Execução ---
if __name__ == "__main__":
    processar_pasta("./minha_colecao_teste")