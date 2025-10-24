# Processador de Comprovantes de Pagamento

Este script processa arquivos de comprovantes de pagamento (PDF, JPEG, PNG), extrai informações relevantes usando OCR e um modelo de linguagem natural (LLM), classifica os boletos e renomeia os arquivos com base na data do pagamento, valor pago e classificação.

## Funcionalidades

- Extração de texto de PDFs e imagens usando OCR (Tesseract)
- Processamento de texto com modelos LLM (Ollama, OpenAI, etc.)
- Classificação automática de boletos baseada em códigos do CSV
- Renomeação automática de arquivos no formato: `YYYY-MM-DD-R$VALOR-CLASSIFICACAO.ext`
- Validação robusta de dados extraídos
- Sistema de logging completo
- Modo dry-run para simulação sem modificar arquivos
- Timeout configurável para chamadas ao LLM
- Limpeza automática de recursos temporários
- Relatório detalhado de erros ao final do processamento

## Pré-requisitos

### Dependências Python

Instale as dependências do arquivo requirements.txt:

```bash
pip install -r requirements.txt
```

Ou instale manualmente:

```bash
pip install pymupdf==1.24.9 openai==1.38.0 pandas==2.2.2 Pillow==10.4.0 pytesseract==0.3.10
```

### Tesseract OCR

O Tesseract OCR deve estar instalado no sistema:

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

**Windows:**
Baixe o instalador em: https://github.com/UB-Mannheim/tesseract/wiki

## Configuração

### Variáveis de Ambiente

O script suporta configuração via variáveis de ambiente:

- `BOLETO_MODELO_LLM`: Modelo LLM a usar (padrão: `gemma3:4b`)
- `BOLETO_BASE_URL_LLM`: URL base do servidor LLM (padrão: `http://localhost:11434/v1`)
- `BOLETO_API_KEY_LLM`: Chave API do LLM (padrão: `ollama`)
- `BOLETO_TESSERACT_LANG`: Idioma do Tesseract OCR (padrão: `por`)
- `BOLETO_LOG_LEVEL`: Nível de log - DEBUG, INFO, WARNING, ERROR (padrão: `INFO`)

### Arquivo CSV de Classificação

Crie um arquivo CSV (padrão: `dbcodigocontas.csv`) com as colunas:

- `nome_pagamento`: Nome da classificação do boleto
- `codigos`: Lista de códigos/palavras-chave para identificação (formato JSON ou separado por vírgula)

Exemplo:
```csv
nome_pagamento,codigos
energia,"[""luz"",""eletricidade""]"
agua,"[""saneamento"",""agua""]"
internet,"[""fibra"",""banda larga""]"
```

## Como Usar

### Uso Básico

```bash
python boleto_extract.py
```

Por padrão, processa arquivos no diretório atual usando `./dbcodigocontas.csv`.

### Especificando Diretórios

```bash
python boleto_extract.py --path_arquivos /caminho/dos/pdfs --path_base_contas /caminho/contas.csv
```

### Modo Dry-Run (Simulação)

Execute sem renomear arquivos, apenas simula o processamento:

```bash
python boleto_extract.py --dry-run
```

### Configurando Timeout do LLM

Defina timeout em segundos para chamadas ao LLM (padrão: 60s):

```bash
python boleto_extract.py --timeout 120
```

### Alterando o Modelo LLM

```bash
python boleto_extract.py --modelo llama3.2
```

### Configurando Servidor LLM Customizado

```bash
python boleto_extract.py --base-url-llm https://api.openai.com/v1 --api-key-llm sua_chave_api
```

### Ajustando Nível de Log

```bash
python boleto_extract.py --log-level DEBUG
```

### Exemplo Completo

```bash
python boleto_extract.py \
  --path_arquivos ./comprovantes \
  --path_base_contas ./classificacao.csv \
  --modelo gpt-4 \
  --timeout 90 \
  --log-level INFO \
  --dry-run
```

## Argumentos da Linha de Comando

| Argumento | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `--path_arquivos` | string | `./` | Diretório contendo os arquivos a processar |
| `--path_base_contas` | string | `./dbcodigocontas.csv` | Caminho do CSV com códigos de classificação |
| `--modelo` | string | `gemma3:4b` | Modelo LLM a usar |
| `--base-url-llm` | string | `http://localhost:11434/v1` | URL base do servidor LLM |
| `--api-key-llm` | string | `ollama` | Chave API do LLM |
| `--tesseract-lang` | string | `por` | Idioma do Tesseract OCR |
| `--timeout` | int | `60` | Timeout em segundos para chamadas ao LLM |
| `--log-level` | choice | `INFO` | Nível de log (DEBUG/INFO/WARNING/ERROR) |
| `--dry-run` | flag | `false` | Executa sem renomear arquivos |

## Formato de Saída

Os arquivos são renomeados no formato:

```
YYYY-MM-DD-R$VALOR-CLASSIFICACAO.extensao
```

Exemplos:
- `2023-02-17-R$10799.10-energia.pdf`
- `2020-08-20-R$41.00-agua.jpg`
- `2024-10-15-R$150.50-naoidentificado.png`

## Arquivos Processados

O script processa apenas arquivos que:
- Tenham extensão `.pdf`, `.jpg`, `.jpeg` ou `.png`
- NÃO comecem com data no formato `YYYY-MM-DD` (evita reprocessamento)
- NÃO contenham "naoidentificado" no nome

## Logging

O script gera dois tipos de log:
- **Console**: Saída em tempo real
- **Arquivo**: `boleto_extract.log` no diretório de execução

### Resumo de Erros

Ao final do processamento, exibe um resumo completo de todos os arquivos que falharam, incluindo:
- Nome do arquivo
- Descrição detalhada do erro
- Stack trace para erros inesperados

## Tratamento de Erros

O script valida:
- Existência e permissões de diretórios e arquivos
- Dependências do sistema (Tesseract, bibliotecas Python)
- Formato e conteúdo do CSV de classificação
- Estrutura de dados extraídos (data, valor)
- Resposta do LLM (timeout, formato JSON)
- Dimensões de imagens e número de páginas em PDFs

Erros não são silenciosamente ignorados - todos são registrados e reportados ao final.

## Estrutura do Projeto

```
boleto_extract/
├── boleto_extract.py        # Script principal
├── requirements.txt          # Dependências Python
├── dbcodigocontas.csv       # Arquivo de classificação (exemplo)
├── boleto_extract.log       # Log de execução (gerado)
└── README.md                # Este arquivo
```

## Solução de Problemas

### Tesseract não encontrado

```
RuntimeError: Tesseract OCR não encontrado ou não funcional
```

Instale o Tesseract conforme instruções na seção Pré-requisitos.

### Timeout do LLM

```
Erro ao comunicar com LLM: timeout
```

Aumente o timeout: `--timeout 120`

### JSON inválido do LLM

```
Erro ao decodificar JSON
```

O modelo pode estar retornando formato incorreto. Tente outro modelo ou ajuste o prompt.

### Nenhum conteúdo extraído

Verifique a qualidade da imagem ou PDF. Use `--log-level DEBUG` para mais detalhes.

## Licença

Este projeto é fornecido como está, sem garantias.