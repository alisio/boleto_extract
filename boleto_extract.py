"""
Este script processa arquivos de comprovantes de pagamento, extrai informações relevantes usando OCR e
um modelo de linguagem natural, e renomeia os arquivos com base na data do pagamento e valor pago.

Bibliotecas usadas:
- PyMuPDF para manipulação de arquivos PDF
- pytesseract e Pillow para OCR em imagens
- openai para interação com o modelo de linguagem natural
- pandas para manipulação de dados tabulares
- re para expressões regulares
- os para manipulação de arquivos

Variáveis globais:
- MODELO: O modelo de linguagem a ser usado
- PROMPT: Prompt usado para extrair informações dos comprovantes

Funções:
- listar_arquivos: Lista arquivos válidos em um diretório
- extract_content: Extrai o conteúdo de um arquivo (PDF ou imagem)
- extract_text_from_pdf: Extrai texto de um arquivo PDF
- extract_text_from_image: Extrai texto de uma imagem
- enviar_para_llm: Envia texto para um modelo de linguagem e retorna a resposta
- carregar_base_contas: Carrega e normaliza o CSV de códigos de contas
- normalizar_codigos: Normaliza a lista de códigos do CSV
- classifica_boleto: Classifica o boleto com base nos códigos presentes no dataframe

Pre requisitos:
    pymupdf>=1.26.0      # PDF processing (fitz)
    pytesseract>=0.3.10  # OCR functionality
    pillow>=10.0.0       # Image processing
    pandas>=2.0.0        # Data manipulation
    openai>=1.0.0        # LLM client
"""

import os
import re
import sys
import time
import hashlib
import json
import ast
import argparse
import logging
import logging.handlers
from datetime import datetime
import fitz   # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
from openai import OpenAI
from pathlib import Path
import csv
import tempfile
import atexit
import shutil
from filelock import FileLock, Timeout as FileLockTimeout


# Configuração de logging
BOLETO_LOG_FILE = os.getenv('BOLETO_LOG_FILE', 'boleto_extract.log')
BOLETO_LOG_MAX_MB = int(os.getenv('BOLETO_LOG_MAX_MB', '50'))
BOLETO_LOG_BACKUPS = int(os.getenv('BOLETO_LOG_BACKUPS', '3'))

_log_dir = os.path.dirname(BOLETO_LOG_FILE)
if _log_dir:
    os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            BOLETO_LOG_FILE,
            maxBytes=BOLETO_LOG_MAX_MB * 1024 * 1024,
            backupCount=BOLETO_LOG_BACKUPS
        )
    ]
)
logger = logging.getLogger(__name__)

# Lista global de arquivos temporários para limpeza
_temp_files = []
_temp_dirs = []

def limpar_arquivos_temporarios():
    """Limpa todos os arquivos temporários criados durante a execução."""
    for temp_file in _temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Arquivo temporário removido: {temp_file}")
        except Exception as e:
            logger.warning(f"Não foi possível remover arquivo temporário {temp_file}: {e}")
    
    for temp_dir in _temp_dirs:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Diretório temporário removido: {temp_dir}")
        except Exception as e:
            logger.warning(f"Não foi possível remover diretório temporário {temp_dir}: {e}")

# Registrar função de limpeza para executar ao sair
atexit.register(limpar_arquivos_temporarios)


def verificar_dependencias():
    """Verifica se todas as dependências estão disponíveis."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        logger.info("Tesseract OCR encontrado e funcionando")
    except Exception as e:
        raise RuntimeError(f"Tesseract OCR não encontrado ou não funcional: {e}")
    
    try:
        import fitz
        logger.info("PyMuPDF (fitz) disponível")
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) não encontrado. Instale com: pip install pymupdf")
    
    try:
        from openai import OpenAI
        logger.info("OpenAI client disponível")
    except ImportError:
        raise RuntimeError("OpenAI client não encontrado. Instale com: pip install openai")


def obter_configuracao():
    """Obtém configuração de variáveis de ambiente com valores padrão."""
    config = {
        'modelo_llm': os.getenv('BOLETO_MODELO_LLM', 'gemma3:4b'),
        'base_url_llm': os.getenv('BOLETO_BASE_URL_LLM', 'http://localhost:11434/v1'),
        'api_key_llm': os.getenv('BOLETO_API_KEY_LLM', 'ollama'),
        'tesseract_lang': os.getenv('BOLETO_TESSERACT_LANG', 'por'),
        'log_level': os.getenv('BOLETO_LOG_LEVEL', 'INFO'),
        'lock_file': os.getenv('BOLETO_LOCK_FILE', '/tmp/boleto_extract.lock'),
        'stable_timeout': int(os.getenv('BOLETO_STABLE_TIMEOUT', '15')),
        'stable_interval': float(os.getenv('BOLETO_STABLE_INTERVAL', '0.5')),
    }
    
    # Ajustar nível de log
    log_level = getattr(logging, config['log_level'].upper(), logging.INFO)
    logger.setLevel(log_level)
    
    return config


def validar_dataframe(df):
    """Valida se o DataFrame tem as colunas necessárias."""
    required_columns = ['codigos', 'nome_pagamento']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas faltando no CSV: {missing}")
    logger.info(f"DataFrame validado com {len(df)} registros")


def validar_data(data_str):
    """Valida formato de data."""
    try:
        datetime.strptime(data_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


# Variáveis globais - serão configuradas dinamicamente
CONFIG = obter_configuracao()
MODELO = CONFIG['modelo_llm']  # Agora usa a configuração
PROMPT = """
Extrair de um dado texto, utilizando exclusivamente as informações que constam no \
texto fornecido, sem inventar, com o conteúdo comprovantes de pagamento. Siga as instruções abaixo:

1. Data do pagamento
2. Valor pago
3. Utilize a técnica chain of thoughts reasoning
4. O conteúdo do comprovante será colocado entre quatro backticks
5. A resposta deve ser em formato JSON, com as chaves data_pagamento, contendo a data em formato \
'yyyy-mm-aa' e valor_pagamento, contendo o valor pago em formato ponto flutuante. A resposta deve conter somente o JSON, mais nada.
6. Caso não seja possível extrair as informações, responda apenas 'erro'

Exemplo de resposta1:

{{
  "data_pagamento": "2023-02-17",
  "valor_pagamento": 10799.10
}}

Exemplo de resposta 2:

{{
    "data_pagamento": "2020-08-20",
    "valor_pagamento": 41.00
}}

Conteúdo do comprovante:
"""


def carregar_base_contas(path_csv):
    """Carrega o CSV de contas preservando listas na coluna 'codigos'."""
    registros = []
    try:
        with open(path_csv, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)
            if header is None:
                raise ValueError("Arquivo CSV vazio.")
            header_normalizado = [col.strip().lower() for col in header]
            if 'nome_pagamento' not in header_normalizado or 'codigos' not in header_normalizado:
                raise ValueError("CSV deve conter as colunas 'nome_pagamento' e 'codigos'.")
            idx_nome = header_normalizado.index('nome_pagamento')
            idx_codigos = header_normalizado.index('codigos')

            for linha_num, row in enumerate(reader, start=2):
                if not row or all(not str(campo).strip() for campo in row):
                    continue
                if len(row) <= idx_codigos:
                    logger.warning(f"Linha {linha_num}: coluna 'codigos' ausente ou vazia")
                    continue

                nome = row[idx_nome].strip()
                codigos_fragmentos = row[idx_codigos:]
                codigos_texto = ','.join(fragment.strip() for fragment in codigos_fragmentos if fragment is not None).strip()

                if not nome or not codigos_texto:
                    logger.warning(f"Linha {linha_num}: dados insuficientes para carregar registro")
                    continue

                registros.append({'nome_pagamento': nome, 'codigos': codigos_texto})

    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Erro ao ler CSV {path_csv}: {e}")
        raise

    if not registros:
        raise ValueError("Nenhum registro válido encontrado no CSV.")

    df = pd.DataFrame(registros, columns=['nome_pagamento', 'codigos'])
    logger.info(f"CSV carregado com {len(df)} registros antes da validação")
    return df


# Sufixo usado para marcar imagens processadas
SUFIXO_PROCESSADO = ".processed"


def listar_arquivos(diretorio, reclassificar=False):
    """Lista arquivos válidos em um diretório, filtrando por data no nome e extensões permitidas."""
    regex_data = re.compile(r'^\d{4}-\d{2}-\d{2}')
    arquivos_validos = []

    try:
        arquivos_dir = os.listdir(diretorio)
        logger.info(f"Encontrados {len(arquivos_dir)} arquivos no diretório {diretorio}")
    except OSError as e:
        logger.error(f"Erro ao listar diretório {diretorio}: {e}")
        raise

    for arquivo in arquivos_dir:
        # Ignorar arquivos já processados (com sufixo .processed)
        if SUFIXO_PROCESSADO in arquivo:
            logger.debug(f"Arquivo ignorado (já processado): {arquivo}")
            continue
        
        # Ignorar arquivos legados com prefixo convertido_ (de versões anteriores)
        if arquivo.lower().startswith('convertido_'):
            logger.debug(f"Arquivo ignorado (legado convertido_): {arquivo}")
            continue

        if arquivo.lower().endswith(('.pdf', '.jpeg', '.jpg', '.png')) and 'erro_criptografado' not in arquivo.lower():
            ja_datado = bool(regex_data.match(arquivo))
            eh_naoidentificado = 'naoidentificado' in arquivo.lower()
            if ja_datado and not (reclassificar and eh_naoidentificado):
                continue
            arquivos_validos.append(arquivo)

    logger.info(f"Encontrados {len(arquivos_validos)} arquivos válidos para processamento (reclassificar: {reclassificar})")
    return arquivos_validos


def extract_content(file_path):
    """Extrai o conteúdo de um arquivo (PDF ou imagem) com base em sua extensão."""
    ext = os.path.splitext(file_path)[-1].lower()
    
    logger.info(f"Extraindo conteúdo do arquivo: {file_path}")
    
    try:
        if ext == '.pdf':
            return extract_text_from_pdf(file_path)
        elif ext in ['.jpg', '.jpeg', '.png']:
            return extract_text_from_image(file_path)
        else:
            raise ValueError(f"Formato de arquivo não suportado: {ext}. Use PDF, JPG, JPEG ou PNG.")
    except Exception as e:
        logger.error(f"Erro ao extrair conteúdo de {file_path}: {e}")
        raise


def extract_text_from_pdf(pdf_path):
    """Extrai texto de um arquivo PDF (texto embutido ou OCR para PDFs escaneados)."""
    text = ""
    
    # Validação de entrada
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")
    
    if not os.path.isfile(pdf_path):
        raise ValueError(f"Caminho não é um arquivo: {pdf_path}")
    
    try:
        with fitz.open(pdf_path) as doc:
            logger.debug(f"PDF aberto com {len(doc)} páginas")
            
            if doc.needs_pass or doc.is_encrypted:
                logger.debug(f"PDF criptografado detectado, tentando autenticar: {pdf_path}")
                if doc.authenticate(""):
                    logger.debug("PDF autenticado com senha vazia")
                else:
                    raise ValueError(f"PDF criptografado (senha necessária): {pdf_path}")
            
            if len(doc) == 0:
                raise ValueError(f"PDF vazio (0 páginas): {pdf_path}")
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                text += page_text
                logger.debug(f"Página {page_num + 1}: {len(page_text)} caracteres extraídos")
            
            # Se texto extraído for vazio, tentar OCR (PDF escaneado)
            if not text.strip():
                logger.info("Texto vazio - tentando OCR para PDF escaneado...")
                text = ""
                for page_num, page in enumerate(doc):
                    # Renderizar página como imagem
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_data = pix.tobytes("png")
                    
                    # OCR na imagem
                    from io import BytesIO
                    img = Image.open(BytesIO(img_data))
                    page_text = pytesseract.image_to_string(img, lang=CONFIG['tesseract_lang'])
                    text += page_text
                    logger.debug(f"Página {page_num + 1} OCR: {len(page_text)} caracteres")
        
        logger.info(f"Texto extraído do PDF: {len(text)} caracteres totais.")
        return text
    except Exception as e:
        logger.error(f"Erro ao processar PDF {pdf_path}: {e}")
        raise


def extract_text_from_image(image_path):
    """Extrai texto de uma imagem usando OCR."""
    # Validação de entrada
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Arquivo de imagem não encontrado: {image_path}")
    
    if not os.path.isfile(image_path):
        raise ValueError(f"Caminho não é um arquivo: {image_path}")
    
    try:
        image = Image.open(image_path)
        logger.debug(f"Imagem carregada: {image.size}")
        
        # Validar dimensões da imagem
        if image.size[0] == 0 or image.size[1] == 0:
            raise ValueError(f"Imagem com dimensões inválidas: {image.size}")
        
        text = pytesseract.image_to_string(image, lang=CONFIG['tesseract_lang'])
        logger.info(f"OCR concluído: {len(text)} caracteres extraídos de {image_path}")
        
        # Fechar imagem para liberar recurso
        image.close()
        
        return text
    except Exception as e:
        logger.error(f"Erro no OCR da imagem {image_path}: {e}")
        raise


def converter_imagem_para_pdf(imagem_path, destino_pdf):
    """Converte uma imagem (PNG/JPG) para PDF."""
    try:
        with Image.open(imagem_path) as img:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(destino_pdf, 'PDF', resolution=100.0)
        logger.info(f"Imagem convertida para PDF: {imagem_path} -> {destino_pdf}")
        return True
    except Exception as e:
        logger.error(f"Erro ao converter imagem para PDF: {e}")
        raise


def enviar_para_llm(texto, prompt, modelo=None, timeout=60):
    """Envia texto para um modelo de linguagem e retorna a resposta formatada."""
    if modelo is None:
        modelo = CONFIG['modelo_llm']
    
    # Validação de entrada
    if not texto or not texto.strip():
        raise ValueError("Texto vazio não pode ser enviado ao LLM")
    
    if len(texto) > 100000:  # Limite de 100k caracteres
        logger.warning(f"Texto muito longo ({len(texto)} caracteres), truncando para 100000")
        texto = texto[:100000]
    
    contexto = f"""{prompt}\n\n````\n{texto}\n````\n"""
    
    try:
        client = OpenAI(
            base_url=CONFIG['base_url_llm'],
            api_key=CONFIG['api_key_llm'],
            timeout=timeout,
        )

        logger.info(f"Enviando texto para LLM (modelo: {modelo}, timeout: {timeout}s)")
        logger.debug(f"Tamanho do contexto: {len(contexto)} caracteres")

        resposta = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "user", "content": contexto}
            ]
        )
        
        # Validação da resposta
        if not resposta or not resposta.choices:
            raise ValueError("Resposta vazia do LLM")
        
        resultado = resposta.choices[0].message.content
        
        if not resultado or not resultado.strip():
            raise ValueError("Conteúdo vazio na resposta do LLM")
        
        logger.info("Resposta recebida do LLM e validada")
        logger.debug(f"Resposta LLM: {resultado[:200]}...")
        
        return resultado
    
    except Exception as e:
        logger.error(f"Erro ao comunicar com LLM: {e}")
        raise


def normalizar_codigos(codigos_raw):
    """Converte a coluna 'codigos' em uma lista normalizada de strings."""
    if isinstance(codigos_raw, list):
        elementos = codigos_raw
    else:
        if pd.isna(codigos_raw):
            return []
        try:
            texto = str(codigos_raw).strip()
            if not texto:
                return []
            try:
                elementos = json.loads(texto)
            except json.JSONDecodeError:
                elementos = ast.literal_eval(texto)
            if not isinstance(elementos, (list, tuple)):
                elementos = [elementos]
        except (ValueError, SyntaxError, TypeError) as e:
            logger.warning(f"Não foi possível interpretar códigos '{codigos_raw}': {e}")
            elementos = []
    return [str(item).strip().lower() for item in elementos if str(item).strip()]


def classifica_boleto(texto, dataframe):
    """Classifica o boleto com base nos códigos presentes no dataframe."""
    texto_lower = texto.lower()
    
    for index, row in dataframe.iterrows():
        try:
            nome = str(row['nome_pagamento']) if pd.notna(row['nome_pagamento']) else 'naoidentificado'
            codigos = row['codigos'] if isinstance(row['codigos'], list) else []
            
            if codigos and all(codigo in texto_lower for codigo in codigos):
                logger.info(f"Boleto classificado como: {nome} (códigos: {', '.join(codigos)})")
                return nome
                
        except KeyError as e:
            logger.error(f"Coluna não encontrada no DataFrame: {e}")
            raise
        except Exception as e:
            logger.warning(f"Erro ao processar linha {index} do DataFrame: {e}")
            continue
    
    logger.info("Boleto não identificado - nenhum código encontrado")
    return 'naoidentificado'


def validar_diretorio(diretorio):
    """Valida se o diretório existe e é acessível."""
    path = Path(diretorio)
    
    if not path.exists():
        logger.error(f"Diretório não encontrado: {diretorio}")
        raise FileNotFoundError(f"Diretório não encontrado: {diretorio}")
    
    if not path.is_dir():
        logger.error(f"O caminho não é um diretório: {diretorio}")
        raise NotADirectoryError(f"O caminho fornecido não é um diretório: {diretorio}")
    
    logger.info(f"Diretório validado: {diretorio}")


def validar_arquivo(caminho):
    """Valida se o caminho é um arquivo existente com extensão suportada."""
    path = Path(caminho)
    if not path.exists():
        logger.error(f"Arquivo não encontrado: {caminho}")
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    if not path.is_file():
        logger.error(f"O caminho não é um arquivo: {caminho}")
        raise ValueError(f"O caminho fornecido não é um arquivo: {caminho}")
    ext = path.suffix.lower()
    if ext not in ('.pdf', '.jpeg', '.jpg', '.png'):
        raise ValueError(f"Formato de arquivo não suportado: {ext}. Use PDF, JPG, JPEG ou PNG.")
    if 'erro_criptografado' in path.name.lower():
        raise ValueError(f"Arquivo marcado como erro criptografado, ignorado: {caminho}")
    if SUFIXO_PROCESSADO in path.name:
        raise ValueError(f"Arquivo já processado (sufixo {SUFIXO_PROCESSADO}): {caminho}")
    if path.name.lower().startswith('convertido_'):
        raise ValueError(f"Arquivo legado ignorado (convertido_): {caminho}")
    logger.info(f"Arquivo validado: {caminho}")
    return path


def esperar_arquivo_estavel(caminho, timeout=None, intervalo=None):
    """Aguarda arquivo ficar com tamanho/mtime estáveis (evita leitura truncada via incrond).

    Retorna True se estável, False se timeout. timeout=0 desativa espera.
    """
    if timeout is None:
        timeout = CONFIG.get('stable_timeout', 15)
    if intervalo is None:
        intervalo = CONFIG.get('stable_interval', 0.5)
    if timeout is not None and timeout <= 0:
        logger.debug(f"Espera estável desativada (timeout={timeout}) para {caminho}")
        return True
    path = Path(caminho)
    if not path.exists():
        return False
    start = time.monotonic()
    estabilizacoes = 0
    ultimo_tamanho = -1
    ultimo_mtime = -1
    # Precisa de 2 leituras consecutivas iguais
    while True:
        try:
            stat = path.stat()
            tamanho = stat.st_size
            mtime = stat.st_mtime
        except OSError as e:
            logger.warning(f"Não foi possível stat {caminho}: {e}")
            tamanho, mtime = -1, -1
        if tamanho == ultimo_tamanho and mtime == ultimo_mtime and tamanho >= 0:
            estabilizacoes += 1
            if estabilizacoes >= 2:
                logger.info(f"Arquivo estável após {time.monotonic()-start:.1f}s: {caminho} ({tamanho} bytes)")
                return True
        else:
            estabilizacoes = 0
            ultimo_tamanho, ultimo_mtime = tamanho, mtime
        if time.monotonic() - start >= timeout:
            logger.warning(f"Timeout ({timeout}s) aguardando estabilidade de {caminho} (último tamanho={tamanho})")
            return False
        time.sleep(intervalo)


def extrair_json_llm(resposta):
    """Limpa resposta do LLM e extrai dict JSON (reuso entre batch e single-file)."""
    # Remover blocos <think>...</think>
    resposta = re.sub(r'<think>[\s\S]*?</think>', '', resposta, flags=re.IGNORECASE).strip()
    resposta_limpa = resposta.replace('{{', '{').replace('}}', '}')
    resposta_limpa = resposta_limpa.replace('\\"', '"')
    resposta_limpa = re.sub(r'\\_', '_', resposta_limpa)
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", resposta_limpa)
    if match:
        resposta_limpa = match.group(1)
        logger.debug(f"Bloco JSON extraído: {resposta_limpa}")
    else:
        resposta_limpa = resposta_limpa.strip()
        logger.debug("Nenhum bloco JSON encontrado, usando resposta completa")
    if resposta_limpa.strip().lower() == 'erro':
        return None, 'erro'
    try:
        return json.loads(resposta_limpa), None
    except json.JSONDecodeError as e:
        return None, f"Erro ao decodificar JSON: {str(e)} | Resposta: {resposta_limpa[:200]}"


def renomear_arquivo(origem, destino, dry_run=False):
    """Renomeia um arquivo com tratamento de erros."""
    try:
        origem_path = Path(origem)
        destino_path = Path(destino)
        
        if dry_run:
            logger.info(f"[DRY-RUN] Arquivo seria renomeado: {origem} -> {destino_path}")
            return destino_path
        
        if destino_path.exists():
            logger.warning(f"Arquivo de destino já existe: {destino}")
            # Adiciona sufixo para evitar conflito
            contador = 1
            while destino_path.exists():
                nome_base = destino_path.stem
                extensao = destino_path.suffix
                novo_nome = f"{nome_base}_{contador}{extensao}"
                destino_path = destino_path.parent / novo_nome
                contador += 1
            logger.info(f"Renomeando para evitar conflito: {destino_path}")
        
        origem_path.rename(destino_path)
        logger.info(f"Arquivo renomeado: {origem} -> {destino_path}")
        return destino_path
        
    except PermissionError as e:
        logger.error(f"Erro de permissão ao renomear {origem} para {destino}: {e}")
        raise
    except OSError as e:
        logger.error(f"Erro do sistema ao renomear {origem} para {destino}: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao renomear {origem} para {destino}: {e}")
        raise


def _processar_um_arquivo(arquivo_path, df, modelo_atual, timeout, dry_run, reclassificar=False):
    """Processa um único arquivo (extrai, classifica, LLM, renomeia). Retorna (novo_nome ou None, erro ou None)."""
    arquivo = Path(arquivo_path).name
    # Extrair conteúdo
    conteudo = extract_content(arquivo_path)
    if not conteudo.strip():
        return None, f"Nenhum conteúdo extraído de {arquivo}"
    # Classificar
    classificacao = classifica_boleto(conteudo, df)
    # Enviar para LLM
    resposta = enviar_para_llm(conteudo, PROMPT, modelo_atual, timeout=timeout)
    resposta_dict, erro = extrair_json_llm(resposta)
    if erro == 'erro':
        return None, "LLM não conseguiu extrair informações"
    if erro:
        return None, erro
    if resposta_dict is None:
        return None, erro or "Resposta inválida do LLM"
    data_pagamento = str(resposta_dict.get('data_pagamento', '')).strip()
    valor_pagamento = resposta_dict.get('valor_pagamento')
    if not data_pagamento or valor_pagamento is None:
        return None, f"Informações incompletas: data={data_pagamento}, valor={valor_pagamento}"
    if not validar_data(data_pagamento):
        return None, f"Data inválida: {data_pagamento}"
    try:
        valor_float = float(valor_pagamento)
        valor_formatado = f"{valor_float:.2f}"
    except (ValueError, TypeError) as e:
        return None, f"Valor inválido: {valor_pagamento} - {str(e)}"
    extensao_original = Path(arquivo).suffix[1:].lower()
    extensao_saida = 'pdf' if extensao_original in ['png', 'jpg', 'jpeg'] else extensao_original
    if classificacao == 'naoidentificado':
        sufixo_hash = hashlib.sha256(conteudo.encode('utf-8')).hexdigest()[:8]
        novo_nome = f"{data_pagamento}-R${valor_formatado}-naoidentificado-{sufixo_hash}.{extensao_saida}"
    else:
        novo_nome = f"{data_pagamento}-R${valor_formatado}-{classificacao}.{extensao_saida}"
    origem = Path(arquivo_path)
    destino = origem.parent / novo_nome
    if origem.name == novo_nome:
        logger.info(f"{arquivo} já está no formato final")
        return None, None  # sem erro, mas sem renomeio
    if extensao_original in ['png', 'jpg', 'jpeg'] and extensao_saida == 'pdf':
        if dry_run:
            logger.info(f"[DRY-RUN] Converteria {extensao_original} para PDF: {origem} -> {destino}")
        else:
            logger.info(f"Convertendo {extensao_original} para PDF...")
            converter_imagem_para_pdf(origem, destino)
            origem.unlink()
            logger.info(f"Arquivo original removido após conversão: {arquivo}")
    else:
        renomear_arquivo(origem, destino, dry_run=dry_run)
    return novo_nome, None


def main(path_arquivos, path_base_contas, modelo_override=None, dry_run=False, timeout=60, reclassificar=False):
    """Função principal para processar e renomear arquivos de comprovantes de pagamento (batch)."""
    if not path_arquivos:
        raise ValueError("path_arquivos não pode ser vazio")
    if not path_base_contas:
        raise ValueError("path_base_contas não pode ser vazio")
    if timeout <= 0:
        raise ValueError("timeout deve ser maior que zero")
    lock_path = CONFIG.get('lock_file', '/tmp/boleto_extract.lock')
    try:
        with FileLock(lock_path, timeout=0):
            return _main_batch(path_arquivos, path_base_contas, modelo_override, dry_run, timeout, reclassificar)
    except FileLockTimeout:
        logger.warning(f"Outra instância em execução (lock {lock_path}), abortando.")
        sys.exit(0)


def _main_batch(path_arquivos, path_base_contas, modelo_override=None, dry_run=False, timeout=60, reclassificar=False):
    """Implementação interna do batch (já com lock adquirido)."""
    verificar_dependencias()
    validar_diretorio(path_arquivos)
    csv_path = Path(path_base_contas)
    if not csv_path.exists():
        logger.error(f"Arquivo CSV não encontrado: {path_base_contas}")
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {path_base_contas}")
    try:
        df = carregar_base_contas(path_base_contas)
        validar_dataframe(df)
        df['codigos'] = df['codigos'].apply(normalizar_codigos)
    except Exception as e:
        logger.error(f"Erro ao carregar CSV {path_base_contas}: {e}")
        raise
    arquivos = listar_arquivos(path_arquivos, reclassificar=reclassificar)
    if not arquivos:
        logger.warning("Nenhum arquivo válido encontrado para processamento")
        return
    modelo_atual = modelo_override or CONFIG['modelo_llm']
    if dry_run:
        logger.info(f"=== MODO DRY-RUN ATIVADO ===")
        logger.info(f"Nenhum arquivo será realmente renomeado")
        logger.info(f"===========================")
    logger.info(f"Iniciando processamento de {len(arquivos)} arquivos com modelo {modelo_atual}")
    sucessos = 0
    erros = 0
    arquivos_com_erro = []
    arquivos_nao_classificados = []
    for arquivo in arquivos:
        logger.info(f"Processando arquivo: {arquivo}")
        try:
            arquivo_path = Path(path_arquivos) / arquivo
            novo_nome, erro = _processar_um_arquivo(arquivo_path, df, modelo_atual, timeout, dry_run, reclassificar=reclassificar)
            if erro:
                logger.error(f"{erro} de {arquivo}")
                arquivos_com_erro.append({'arquivo': arquivo, 'erro': erro})
                erros += 1
                continue
            if novo_nome is None:
                # já no formato final
                continue
            # need conteudo for hash classification check -> re-classify already done; check naoidentificado
            if 'naoidentificado' in novo_nome:
                arquivos_nao_classificados.append({'original': arquivo, 'novo': novo_nome})
            sucessos += 1
            logger.info(f"✓ {arquivo} processado com sucesso -> {novo_nome}")
        except Exception as e:
            erro_msg = f"Erro inesperado: {str(e)}"
            logger.error(f"✗ {erro_msg} ao processar {arquivo}", exc_info=True)
            arquivos_com_erro.append({'arquivo': arquivo, 'erro': erro_msg})
            erros += 1
            if 'criptografado' in str(e).lower():
                caminho_origem = Path(path_arquivos) / arquivo
                marcado = renomear_arquivo(
                    caminho_origem,
                    caminho_origem.with_name(f"{caminho_origem.stem}-erro_criptografado{caminho_origem.suffix}"),
                    dry_run=dry_run,
                )
                logger.info(f"Arquivo criptografado marcado para inspeção manual: {marcado}")
    logger.info(f"Processamento concluído: {sucessos} sucessos, {erros} erros")
    if arquivos_com_erro:
        logger.error("=" * 60)
        logger.error("RESUMO DE ARQUIVOS COM ERRO:")
        logger.error("=" * 60)
        for item in arquivos_com_erro:
            logger.error(f"  - {item['arquivo']}: {item['erro']}")
        logger.error("=" * 60)
    if arquivos_nao_classificados:
        logger.warning("=" * 60)
        logger.warning(f"NÃO CLASSIFICADOS ({len(arquivos_nao_classificados)}):")
        for item in arquivos_nao_classificados:
            logger.warning(f"  - {item['original']} -> {item['novo']}")
        logger.warning("Dica: atualize dbcodigocontas.csv e rode com --reclassificar")
        logger.warning("=" * 60)


def main_single_file(path_arquivo, path_base_contas, modelo_override=None, dry_run=False, timeout=60, stable_timeout=None):
    """Processa um único arquivo (incrond). Espera estabilidade e usa lock sempre ativo."""
    if not path_arquivo:
        raise ValueError("path_arquivo não pode ser vazio")
    if not path_base_contas:
        raise ValueError("path_base_contas não pode ser vazio")
    if timeout <= 0:
        raise ValueError("timeout deve ser maior que zero")
    if stable_timeout is None:
        stable_timeout = CONFIG.get('stable_timeout', 15)
    lock_path = CONFIG.get('lock_file', '/tmp/boleto_extract.lock')
    try:
        with FileLock(lock_path, timeout=0):
            return _main_single_file(path_arquivo, path_base_contas, modelo_override, dry_run, timeout, stable_timeout)
    except FileLockTimeout:
        logger.warning(f"Outra instância em execução (lock {lock_path}), abortando.")
        sys.exit(0)


def _main_single_file(path_arquivo, path_base_contas, modelo_override=None, dry_run=False, timeout=60, stable_timeout=15):
    verificar_dependencias()
    arquivo_path = validar_arquivo(path_arquivo)
    # Espera arquivo ficar estável (evita PDF truncado)
    esperar_arquivo_estavel(arquivo_path, timeout=stable_timeout)
    csv_path = Path(path_base_contas)
    if not csv_path.exists():
        logger.error(f"Arquivo CSV não encontrado: {path_base_contas}")
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {path_base_contas}")
    df = carregar_base_contas(path_base_contas)
    validar_dataframe(df)
    df['codigos'] = df['codigos'].apply(normalizar_codigos)
    modelo_atual = modelo_override or CONFIG['modelo_llm']
    if dry_run:
        logger.info(f"=== MODO DRY-RUN ATIVADO ===")
    logger.info(f"Processando arquivo único: {arquivo_path} com modelo {modelo_atual}")
    try:
        novo_nome, erro = _processar_um_arquivo(arquivo_path, df, modelo_atual, timeout, dry_run)
        if erro:
            logger.error(f"Falha ao processar {arquivo_path.name}: {erro}")
            raise RuntimeError(erro)
        if novo_nome is None:
            logger.info(f"{arquivo_path.name} já está no formato final, nada a fazer")
            return
        logger.info(f"✓ {arquivo_path.name} -> {novo_nome}")
        if 'naoidentificado' in novo_nome:
            logger.warning(f"Não classificado: {arquivo_path.name} -> {novo_nome} (atualize CSV e use --reclassificar)")
    except Exception as e:
        # Marcar criptografado se for o caso
        if 'criptografado' in str(e).lower():
            marcado = renomear_arquivo(
                arquivo_path,
                arquivo_path.with_name(f"{arquivo_path.stem}-erro_criptografado{arquivo_path.suffix}"),
                dry_run=dry_run,
            )
            logger.info(f"Arquivo criptografado marcado para inspeção manual: {marcado}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Processa comprovantes de pagamento e renomeia os arquivos com base nas informações extraídas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Variáveis de ambiente suportadas:
  BOLETO_MODELO_LLM       Modelo LLM a usar (padrão: llama3.1)
  BOLETO_BASE_URL_LLM     URL base do servidor LLM (padrão: http://localhost:11434/v1)
  BOLETO_API_KEY_LLM      Chave API do LLM (padrão: ollama)
  BOLETO_TESSERACT_LANG   Idioma do Tesseract OCR (padrão: por)
  BOLETO_LOG_LEVEL        Nível de log: DEBUG, INFO, WARNING, ERROR (padrão: INFO)
  BOLETO_LOG_FILE        Caminho do arquivo de log (padrão: boleto_extract.log no diretório de trabalho)
  BOLETO_LOG_MAX_MB      Tamanho máximo do log em MB antes de rotacionar (padrão: 50)
  BOLETO_LOG_BACKUPS     Número de arquivos de log rotacionados a manter (padrão: 3)
  BOLETO_LOCK_FILE       Caminho do lock file (padrão: /tmp/boleto_extract.lock)
  BOLETO_STABLE_TIMEOUT  Timeout de estabilidade para --arquivo em segundos (padrão: 15, 0 desativa)
  BOLETO_STABLE_INTERVAL Intervalo de polling para estabilidade em segundos (padrão: 0.5)

Exemplos:
  python boleto_extract.py --path_arquivos /caminho/dos/pdfs --path_base_contas contas.csv
  python boleto_extract.py --arquivo /caminho/boleto.pdf --path_base_contas contas.csv  # incrond: $@/$#
  python boleto_extract.py --modelo llama3.2 --log-level DEBUG
        """
    )
    
    parser.add_argument(
        '--path_arquivos', 
        default='./', 
        help='Diretório contendo os arquivos a serem processados (padrão: diretório atual)'
    )

    parser.add_argument(
        '--arquivo',
        default=None,
        help='Arquivo único para processamento event-driven (incrond $@/$#). Mutuamente exclusivo com --path_arquivos'
    )
    
    parser.add_argument(
        '--path_base_contas', 
        default='./dbcodigocontas.csv', 
        help='Caminho para o arquivo CSV com códigos de contas (padrão: ./dbcodigocontas.csv)'
    )
    
    parser.add_argument(
        '--modelo', 
        help='Modelo LLM a usar (sobrescreve BOLETO_MODELO_LLM)'
    )
    
    parser.add_argument(
        '--base-url-llm', 
        help='URL base do servidor LLM (sobrescreve BOLETO_BASE_URL_LLM)'
    )
    
    parser.add_argument(
        '--api-key-llm', 
        help='Chave API do LLM (sobrescreve BOLETO_API_KEY_LLM)'
    )
    
    parser.add_argument(
        '--tesseract-lang', 
        help='Idioma do Tesseract OCR (sobrescreve BOLETO_TESSERACT_LANG)'
    )
    
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Nível de log (sobrescreve BOLETO_LOG_LEVEL)'
    )
    
    parser.add_argument(
        '--timeout', 
        type=int,
        default=60,
        help='Timeout em segundos para chamadas ao LLM (padrão: 60)'
    )

    parser.add_argument(
        '--stable-timeout',
        type=int,
        default=None,
        help='Timeout em segundos aguardando arquivo ficar estável para --arquivo (padrão: 15, 0 desativa; sobrescreve BOLETO_STABLE_TIMEOUT)'
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Executa sem renomear arquivos (apenas simula)'
    )

    parser.add_argument(
        '--reclassificar',
        action='store_true',
        help='Reprocessa arquivos não classificados já renomeados (YYYY-MM-DD-...-naoidentificado.*) após atualização do CSV'
    )

    args = parser.parse_args()

    # Validação mutuamente exclusiva --arquivo vs --path_arquivos não-default
    if args.arquivo is not None and args.path_arquivos != './':
        parser.error("--arquivo e --path_arquivos são mutuamente exclusivos (use apenas um)")

    try:
        # Atualizar configuração com argumentos CLI (prioridade sobre env vars)
        if args.modelo:
            CONFIG['modelo_llm'] = args.modelo
        if args.base_url_llm:
            CONFIG['base_url_llm'] = args.base_url_llm
        if args.api_key_llm:
            CONFIG['api_key_llm'] = args.api_key_llm
        if args.tesseract_lang:
            CONFIG['tesseract_lang'] = args.tesseract_lang
        if args.log_level:
            CONFIG['log_level'] = args.log_level
            # Atualizar nível do logger
            log_level = getattr(logging, args.log_level.upper())
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)
        if args.stable_timeout is not None:
            CONFIG['stable_timeout'] = args.stable_timeout

        # Log da configuração final
        logger.info("=== Configuração ===")
        for key, value in CONFIG.items():
            if 'key' in key.lower():
                logger.info(f"{key}: {'*' * len(str(value))}")  # Ocultar chaves
            else:
                logger.info(f"{key}: {value}")
        logger.info("==================")

        if args.arquivo is not None:
            stable_to = args.stable_timeout if args.stable_timeout is not None else CONFIG.get('stable_timeout', 15)
            main_single_file(args.arquivo, args.path_base_contas, args.modelo, dry_run=args.dry_run, timeout=args.timeout, stable_timeout=stable_to)
        else:
            main(args.path_arquivos, args.path_base_contas, args.modelo, dry_run=args.dry_run, timeout=args.timeout, reclassificar=args.reclassificar)
        
    except KeyboardInterrupt:
        logger.info("Processamento interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        raise
