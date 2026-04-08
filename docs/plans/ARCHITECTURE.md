# Arquitetura da Solução: Processador de Comprovantes de Pagamento

**Versão:** 1.0  
**Data:** 2026-04-08  
**Autor:** Engenharia Reversa via Análise de Código

---

## 1. Visão Geral da Solução

### 1.1 Propósito

O **Boleto Extract** é uma solução de IA que automatiza o processamento de comprovantes de pagamento (PDFs e imagens), extraindo informações estruturadas (data e valor) via OCR + LLM, classificando-os com base em regras predefinidas, e renomeando os arquivos de forma padronizada.

### 1.2 Problema Resolvido

- **Desorganização de comprovantes:** Arquivos de pagamento recebidos com nomes genéricos
- **Extração manual:** Necessidade de abrir cada arquivo para identificar data/valor
- **Classificação inconsistente:** Categorização manual sujeita a erros

### 1.3 Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BOLETO EXTRACT PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   ENTRADA   │───▶│  EXTRAÇÃO    │───▶│    LLM      │───▶│   SAÍDA     │ │
│  │             │    │              │    │             │    │             │ │
│  │ • PDF       │    │ • PyMuPDF    │    │ • Ollama    │    │ • Renomear  │ │
│  │ • JPG/PNG   │    │ • Tesseract  │    │ • OpenAI    │    │ • Converter │ │
│  │             │    │   OCR        │    │             │    │   img→PDF   │ │
│  └─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘ │
│                                               │                             │
│                                               ▼                             │
│                                    ┌─────────────────┐                      │
│                                    │ CLASSIFICAÇÃO   │                      │
│                                    │                 │                      │
│                                    │ CSV de códigos  │                      │
│                                    │ (pattern match) │                      │
│                                    └─────────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Tecnologias Envolvidas

| Componente | Tecnologia | Propósito |
|------------|------------|-----------|
| Runtime | Python 3.10+ | Linguagem principal |
| PDF Processing | PyMuPDF (fitz) | Extração de texto de PDFs |
| OCR | Tesseract + pytesseract | Reconhecimento de texto em imagens |
| Image Processing | Pillow (PIL) | Manipulação de imagens |
| LLM Client | OpenAI SDK | Interface com modelos de linguagem |
| Data Processing | Pandas | Manipulação de CSV/DataFrames |
| Container | Docker | Deployment containerizado |

### 1.5 Padrões de Integração

- **LLM-agnostic:** Compatível com qualquer API compatível OpenAI (Ollama, vLLM, OpenAI, Azure OpenAI)
- **Batch Processing:** Processamento em lote de múltiplos arquivos
- **Dry-run Mode:** Simulação sem modificações para validação

---

## 2. Lista de Specs (Specifications)

### 2.1 SPEC-001: Extração de Conteúdo de Documento

| Campo | Valor |
|-------|-------|
| **Nome** | `extract_document_content` |
| **Descrição** | Extrai texto legível de documentos PDF ou imagens (JPG, PNG) |
| **Propósito** | Converter documentos visuais em texto processável |

#### Parâmetros de Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `file_path` | `string` | Sim | Caminho absoluto do arquivo |

#### Estrutura de Saída

```json
{
  "type": "string",
  "description": "Texto extraído do documento",
  "constraints": {
    "max_length": 100000,
    "encoding": "utf-8"
  }
}
```

#### Regras de Uso

- Arquivos PDF: Tenta extração nativa primeiro, fallback para OCR se vazio
- Imagens: OCR direto via Tesseract
- Limite de 100k caracteres (truncamento com warning)
- Idioma OCR configurável (padrão: português)

#### Restrições

- Formatos suportados: `.pdf`, `.jpg`, `.jpeg`, `.png`
- Requer Tesseract instalado no sistema

---

### 2.2 SPEC-002: Extração de Informações via LLM

| Campo | Valor |
|-------|-------|
| **Nome** | `extract_payment_info` |
| **Descrição** | Envia texto para LLM e extrai data e valor de pagamento |
| **Propósito** | Uso de IA para identificação de informações estruturadas |

#### Parâmetros de Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `texto` | `string` | Sim | Texto extraído do comprovante |
| `prompt` | `string` | Sim | Instrução para o LLM |
| `modelo` | `string` | Não | Modelo LLM (padrão: `gemma3:4b`) |
| `timeout` | `int` | Não | Timeout em segundos (padrão: 60) |

#### Estrutura de Saída

```json
{
  "data_pagamento": {
    "type": "string",
    "format": "date",
    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
    "description": "Data do pagamento no formato YYYY-MM-DD"
  },
  "valor_pagamento": {
    "type": "number",
    "format": "float",
    "minimum": 0,
    "description": "Valor pago em formato decimal"
  }
}
```

#### Regras de Uso

- Resposta deve ser JSON puro ou em bloco markdown
- Chain-of-thoughts removido automaticamente (`<think>` tags)
- Retorno "erro" indica falha na extração

#### Restrições

- Texto vazio não é aceito
- Requer endpoint LLM configurado e acessível
- Timeout default: 60 segundos

---

### 2.3 SPEC-003: Classificação de Comprovante

| Campo | Valor |
|-------|-------|
| **Nome** | `classify_payment` |
| **Descrição** | Classifica o tipo de pagamento com base em padrões de texto |
| **Propósito** | Categorização automática por regras de negócio |

#### Parâmetros de Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `texto` | `string` | Sim | Texto do comprovante (lowercase) |
| `dataframe` | `DataFrame` | Sim | Base de códigos/classificações |

#### Estrutura de Saída

```json
{
  "type": "string",
  "description": "Nome da classificação identificada",
  "default": "naoidentificado"
}
```

#### Regras de Uso

- Matching case-insensitive
- Todos os códigos de uma categoria devem estar presentes (AND lógico)
- Primeira categoria encontrada é retornada
- Retorna `naoidentificado` se nenhum match

---

### 2.4 SPEC-004: Renomeação de Arquivo

| Campo | Valor |
|-------|-------|
| **Nome** | `rename_payment_file` |
| **Descrição** | Renomeia arquivo seguindo padrão estruturado |
| **Propósito** | Padronização de nomenclatura para organização |

#### Parâmetros de Entrada

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `data_pagamento` | `string` | Sim | Data no formato YYYY-MM-DD |
| `valor_pagamento` | `float` | Sim | Valor do pagamento |
| `classificacao` | `string` | Sim | Categoria do pagamento |
| `extensao` | `string` | Sim | Extensão original do arquivo |

#### Estrutura de Saída

```
{data_pagamento}-R${valor_formatado}-{classificacao}.{extensao}
```

**Exemplo:** `2023-02-17-R$10799.10-conta_luz.pdf`

#### Regras de Uso

- Imagens são automaticamente convertidas para PDF
- Conflitos de nome: adiciona sufixo numérico (`_1`, `_2`, etc.)
- Modo dry-run disponível para simulação

---

## 3. Lista de Skills

### 3.1 Skills Identificadas

| ID | Skill | Descrição | Spec Relacionada |
|----|-------|-----------|------------------|
| SK-001 | **OCR de Documentos** | Extração de texto de PDFs e imagens usando Tesseract | SPEC-001 |
| SK-002 | **Extração Inteligente** | Uso de LLM para extrair dados estruturados de texto livre | SPEC-002 |
| SK-003 | **Classificação por Regras** | Pattern matching baseado em CSV de códigos | SPEC-003 |
| SK-004 | **Conversão de Formatos** | Conversão de imagens para PDF | SPEC-004 |
| SK-005 | **Processamento em Lote** | Iteração sobre múltiplos arquivos com tratamento de erros | N/A |
| SK-006 | **Gestão de Configuração** | Configuração via env vars e CLI args | N/A |

### 3.2 Mapeamento Spec ↔ Implementação

```
SPEC-001 (extract_document_content)
├── extract_content()           # Router principal
├── extract_text_from_pdf()     # PyMuPDF + OCR fallback
└── extract_text_from_image()   # Tesseract direto

SPEC-002 (extract_payment_info)
└── enviar_para_llm()           # OpenAI SDK client

SPEC-003 (classify_payment)
├── carregar_base_contas()      # CSV loader
├── normalizar_codigos()        # List normalization
└── classifica_boleto()         # Pattern matcher

SPEC-004 (rename_payment_file)
├── renomear_arquivo()          # File operations
└── converter_imagem_para_pdf() # PIL conversion
```

### 3.3 Tecnologias por Skill

| Skill | Bibliotecas/Frameworks |
|-------|------------------------|
| SK-001 | PyMuPDF (fitz), pytesseract, Pillow |
| SK-002 | OpenAI SDK |
| SK-003 | Pandas, csv, json, ast |
| SK-004 | Pillow (PIL) |
| SK-005 | os, pathlib, argparse |
| SK-006 | os.environ, argparse, logging |

---

## 4. Prompts Identificados

### 4.1 PROMPT-001: Extração de Data e Valor

#### Estrutura do Prompt

```
┌─────────────────────────────────────────────────┐
│ INSTRUÇÃO PRINCIPAL                              │
│ "Extrair de um dado texto, utilizando           │
│  exclusivamente as informações que constam..."   │
├─────────────────────────────────────────────────┤
│ REGRAS ESPECÍFICAS                               │
│ 1. Data do pagamento                             │
│ 2. Valor pago                                    │
│ 3. Utilize a técnica chain of thoughts reasoning│
│ 4. Conteúdo entre quatro backticks              │
│ 5. Resposta em JSON                              │
│ 6. Caso não seja possível, responder 'erro'     │
├─────────────────────────────────────────────────┤
│ EXEMPLOS (Few-shot)                              │
│ Exemplo 1: {"data_pagamento": "2023-02-17"...}  │
│ Exemplo 2: {"data_pagamento": "2020-08-20"...}  │
├─────────────────────────────────────────────────┤
│ VARIÁVEL DINÂMICA                                │
│ Conteúdo do comprovante:                         │
│ ````{texto}````                                  │
└─────────────────────────────────────────────────┘
```

#### Variáveis Dinâmicas

| Variável | Tipo | Origem |
|----------|------|--------|
| `{texto}` | string | Saída de `extract_content()` |

#### Prompt Completo (Código)

```python
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
```

### 4.2 Sugestões de Melhoria

| Aspecto | Situação Atual | Sugestão |
|---------|---------------|----------|
| **Conflito de instruções** | "somente o JSON" vs "chain of thoughts" | Remover referência a CoT ou pedir CoT em bloco separado |
| **Robustez de parsing** | Regex para extrair JSON de markdown | Já implementado mas poderia usar JSON mode do LLM se disponível |
| **Validação de saída** | Apenas validação de data | Adicionar validação de range de valor (ex: <= 0 é suspeito) |
| **Idioma** | Prompt em português | Considerar português para modelos multilíngues |
| **Exemplos negativos** | Ausente | Adicionar exemplo de comprovante sem dados claros |

---

## 5. Fluxo de Execução

### 5.1 Diagrama de Sequência

```
┌──────────┐    ┌───────────────┐    ┌─────────────┐    ┌─────────┐    ┌──────────┐
│   main   │    │ listar_arqus  │    │extract_cont │    │   LLM   │    │classifica│
└────┬─────┘    └───────┬───────┘    └──────┬──────┘    └────┬────┘    └────┬─────┘
     │                   │                   │                │              │
     │ verificar_deps()  │                   │                │              │
     │───────────────────│                   │                │              │
     │                   │                   │                │              │
     │ validar_dir()     │                   │                │              │
     │───────────────────│                   │                │              │
     │                   │                   │                │              │
     │ carregar_csv()    │                   │                │              │
     │───────────────────│                   │                │              │
     │                   │                   │                │              │
     │ list_files()      │                   │                │              │
     │──────────────────▶│                   │                │              │
     │   [arquivos]      │                   │                │              │
     │◀──────────────────│                   │                │              │
     │                   │                   │                │              │
     │ FOR each arquivo  │                   │                │              │
     │ ═══════════════════════════════════════════════════════════════════════
     │   │               │                   │                │              │
     │   │extract_content│                   │                │              │
     │   │──────────────────────────────────▶│                │              │
     │   │               │                   │ (PDF ou IMG)   │              │
     │   │               │          ┌────────┴────────┐       │              │
     │   │               │          │ PDF? get_text() │       │              │
     │   │               │          │ IMG? tesseract()│       │              │
     │   │               │          └────────┬────────┘       │              │
     │   │   [texto]     │                   │                │              │
     │   │◀──────────────────────────────────│                │              │
     │   │               │                   │                │              │
     │   │classifica_boleto()                │                │              │
     │   │────────────────────────────────────────────────────────────────▶│
     │   │   [classificacao]                 │                │             │
     │   │◀───────────────────────────────────────────────────────────────│
     │   │               │                   │                │              │
     │   │enviar_para_llm(texto, prompt)     │                │              │
     │   │───────────────────────────────────────────────────▶│              │
     │   │               │                   │ POST /chat/completions       │
     │   │   [JSON]      │                   │                │              │
     │   │◀───────────────────────────────────────────────────│              │
     │   │               │                   │                │              │
     │   │ parse_json()  │                   │                │              │
     │   │ validar_data()│                   │                │              │
     │   │               │                   │                │              │
     │   │ renomear_arquivo()                │                │              │
     │   │ (ou converter_img_pdf())          │                │              │
     │   │               │                   │                │              │
     │ END FOR           │                   │                │              │
     │ ═══════════════════════════════════════════════════════════════════════
     │                   │                   │                │              │
     │ log_summary()     │                   │                │              │
     │                   │                   │                │              │
```

### 5.2 Fluxo Simplificado

```
[1. INICIALIZAÇÃO]
    │
    ├─▶ Verificar dependências (Tesseract, PyMuPDF, OpenAI)
    ├─▶ Validar diretório de entrada
    ├─▶ Carregar e validar CSV de códigos
    │
[2. LISTAGEM]
    │
    ├─▶ Listar arquivos (.pdf, .jpg, .png)
    ├─▶ Filtrar: ignorar já processados, com data no nome, ou "naoidentificado"
    │
[3. PROCESSAMENTO (loop)]
    │
    ├─▶ Extrair texto
    │   ├─ PDF: PyMuPDF → texto nativo ou OCR fallback
    │   └─ Imagem: Tesseract OCR
    │
    ├─▶ Classificar
    │   └─ Pattern match contra CSV (todos os códigos presentes)
    │
    ├─▶ Enviar para LLM
    │   ├─ Construir prompt + contexto
    │   ├─ POST /chat/completions
    │   └─ Parse JSON response
    │
    ├─▶ Validar dados
    │   ├─ Data no formato YYYY-MM-DD
    │   └─ Valor numérico válido
    │
    └─▶ Renomear/Converter
        ├─ Se imagem: converter para PDF
        └─ Renomear: {data}-R${valor}-{classificacao}.pdf
    │
[4. FINALIZAÇÃO]
    │
    ├─▶ Log de resumo (sucessos/erros)
    ├─▶ Lista de arquivos com erro
    └─▶ Limpeza de temporários (atexit)
```

### 5.3 Pontos de Decisão

| Ponto | Condição | Ação True | Ação False |
|-------|----------|-----------|------------|
| Formato do arquivo | `.pdf` | `extract_text_from_pdf()` | `extract_text_from_image()` |
| PDF com texto? | `text.strip()` | Usar texto | OCR fallback |
| Classificação match? | Todos códigos presentes | Retorna categoria | Continua iterando |
| Resposta LLM | `== 'erro'` | Pula arquivo, log erro | Parse JSON |
| Data válida? | Formato YYYY-MM-DD | Continua | Pula arquivo |
| Formato de saída | Imagem? | Converter para PDF | Manter extensão |
| Conflito de nome | Arquivo existe? | Adiciona sufixo `_N` | Usa nome original |

---

## 6. Modelo de Dados

### 6.1 Entidades Principais

#### 6.1.1 Documento de Entrada

```
┌─────────────────────────────────────────┐
│           DocumentoComprovante           │
├─────────────────────────────────────────┤
│ + arquivo_path: string (path absoluto)  │
│ + formato: enum [pdf, jpg, jpeg, png]    │
│ + conteudo_texto: string (extraído)      │
│ + processado: boolean                    │
├─────────────────────────────────────────┤
│ Constraints:                             │
│ - Max 100k caracteres de texto           │
│ - Extensões case-insensitive             │
│ - Ignora arquivos com sufixo ".processed"│
└─────────────────────────────────────────┘
```

#### 6.1.2 Informação de Pagamento (Output LLM)

```
┌─────────────────────────────────────────┐
│          InformacaoPagamento             │
├─────────────────────────────────────────┤
│ + data_pagamento: date (YYYY-MM-DD)     │
│ + valor_pagamento: float (> 0)          │
├─────────────────────────────────────────┤
│ Validações:                              │
│ - Data deve ser parseable               │
│ - Valor deve ser numérico               │
│ - Ambos obrigatórios                     │
└─────────────────────────────────────────┘
```

#### 6.1.3 Classificação

```
┌─────────────────────────────────────────┐
│             Classificacao                │
├─────────────────────────────────────────┤
│ + nome_pagamento: string                │
│ + codigos: list[string]                 │
├─────────────────────────────────────────┤
│ Regras:                                  │
│ - Códigos em lowercase                  │
│ - Match: TODOS os códigos presentes     │
│ - Ordem de prioridade: ordem no CSV     │
└─────────────────────────────────────────┘
```

### 6.2 Estrutura do CSV de Classificação

```csv
nome_pagamento,codigos
conta_luz,"[""LUZ"",""ENERGIA"",""COMPANHIA""]"
conta_agua,"[""AGUA"",""SANEA"",""TRATAMENTO""]"
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `nome_pagamento` | string | Identificador da categoria |
| `codigos` | JSON array | Lista de palavras-chave (AND lógico) |

### 6.3 Esquema de Configuração

```python
CONFIG = {
    'modelo_llm': str,        # Modelo LLM (ex: gemma3:4b)
    'base_url_llm': str,      # URL da API (ex: http://localhost:11434/v1)
    'api_key_llm': str,       # Chave de autenticação
    'tesseract_lang': str,    # Idioma OCR (ex: por)
    'log_level': str          # DEBUG, INFO, WARNING, ERROR
}
```

### 6.4 Formato de Saída (Nome do Arquivo)

```
{data_pagamento}-R${valor_formatado}-{classificacao}.{extensao}
        │               │                │              │
        │               │                │              └─ pdf (convertido) ou original
        │               │                └─ nome_pagamento ou "naoidentificado"
        │               └─ valor com 2 casas decimais
        └─ YYYY-MM-DD
```

**Exemplos:**
- `2023-02-17-R$10799.10-conta_luz.pdf`
- `2024-01-15-R$250.00-naoidentificado.pdf`

---

## 7. Observabilidade

### 7.1 Eventos de Log Implementados

| Nível | Evento | Contexto |
|-------|--------|----------|
| INFO | Início de processamento | `Iniciando processamento de N arquivos` |
| INFO | Arquivo processado | `✓ {arquivo} processado com sucesso` |
| INFO | Classificação identificada | `Boleto classificado como: {nome}` |
| INFO | OCR concluído | Número de caracteres extraídos |
| INFO | Conversão de formato | `Imagem convertida para PDF` |
| WARNING | Dados insuficientes no CSV | Linha específica ignorada |
| WARNING | Texto muito longo | Truncamento aplicado |
| ERROR | Falha de extração | Arquivo e tipo de erro |
| ERROR | JSON inválido | Resposta do LLM malformada |
| ERROR | Data/valor inválidos | Dados não parseáveis |
| DEBUG | Resposta do LLM | Primeiros 200 chars |
| DEBUG | Tamanho do contexto | Número de caracteres |

### 7.2 Métricas Recomendadas

| Métrica | Tipo | Descrição | Implementação Atual |
|---------|------|-----------|---------------------|
| `sucessos_total` | Counter | Arquivos processados com sucesso | ✅ Variável local |
| `erros_total` | Counter | Arquivos com falha | ✅ Variável local |
| `llm_latency_seconds` | Histogram | Tempo de resposta do LLM | ⚠️ Não implementado |
| `ocr_latency_seconds` | Histogram | Tempo de OCR por arquivo | ⚠️ Não implementado |
| `llm_tokens_input` | Counter | Tokens enviados ao LLM | ⚠️ Não implementado |
| `llm_tokens_output` | Counter | Tokens recebidos do LLM | ⚠️ Não implementado |
| `classificacao_distribution` | Counter | Distribuição por categoria | ⚠️ Não implementado |
| `arquivo_size_bytes` | Histogram | Tamanho dos arquivos processados | ⚠️ Não implementado |

### 7.3 Logging Estruturado

**Configuração atual:**
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('boleto_extract.log')
    ]
)
```

### 7.4 Sugestões de Melhoria

| Área | Lacuna | Recomendação |
|------|--------|--------------|
| **Métricas** | Sem métricas estruturadas | Adicionar prometheus_client ou OpenTelemetry |
| **Tracing** | Sem correlação de requests | Implementar request_id em logs |
| **Latência LLM** | Não medida | Timer decorator em `enviar_para_llm()` |
| **Custos** | Tokens não contabilizados | Extrair `usage` da resposta OpenAI |
| **Alertas** | Sem thresholds | Definir alertas para taxa de erro > X% |
| **Dashboards** | Ausentes | Criar dashboard com KPIs principais |

### 7.5 Estrutura de Log Sugerida (Melhorada)

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "event": "arquivo_processado",
  "arquivo": "comprovante123.pdf",
  "classificacao": "conta_luz",
  "data_pagamento": "2024-01-10",
  "valor_pagamento": 150.00,
  "llm_model": "gemma3:4b",
  "llm_latency_ms": 2500,
  "ocr_latency_ms": 800,
  "texto_size_chars": 3500,
  "request_id": "uuid-xxx"
}
```

---

## 8. Proposta de Evals (Avaliação)

### 8.1 Casos de Teste Funcionais

#### TEST-001: Extração de PDF com texto nativo

| Campo | Valor |
|-------|-------|
| **Input** | PDF com texto selecionável |
| **Expected** | Texto extraído sem OCR |
| **Critério** | `len(texto) > 0` e OCR não invocado |

#### TEST-002: Extração de PDF escaneado (OCR)

| Campo | Valor |
|-------|-------|
| **Input** | PDF com apenas imagens |
| **Expected** | Texto extraído via OCR |
| **Critério** | Texto legível com > 50% de palavras corretas |

#### TEST-003: Extração de imagem (JPG/PNG)

| Campo | Valor |
|-------|-------|
| **Input** | Screenshot de comprovante |
| **Expected** | Texto extraído via Tesseract |
| **Critério** | Valores numéricos corretamente identificados |

#### TEST-004: Classificação correta

| Campo | Valor |
|-------|-------|
| **Input** | Comprovante com "LUZ" e "ENERGIA" |
| **Expected** | Classificação = "conta_luz" |
| **Critério** | Match exato com CSV |

#### TEST-005: Classificação não identificada

| Campo | Valor |
|-------|-------|
| **Input** | Comprovante genérico sem keywords |
| **Expected** | Classificação = "naoidentificado" |
| **Critério** | Fallback correto |

#### TEST-006: Extração LLM - caso feliz

| Campo | Valor |
|-------|-------|
| **Input** | Texto com "17/02/2023" e "R$ 10.799,10" |
| **Expected** | `{"data_pagamento": "2023-02-17", "valor_pagamento": 10799.10}` |
| **Critério** | JSON válido, formatos corretos |

#### TEST-007: Extração LLM - dados ausentes

| Campo | Valor |
|-------|-------|
| **Input** | Texto sem data ou valor claro |
| **Expected** | Resposta "erro" |
| **Critério** | Não inventar dados |

#### TEST-008: Conversão imagem → PDF

| Campo | Valor |
|-------|-------|
| **Input** | comprovante.png |
| **Expected** | comprovante_{data}_{valor}_{class}.pdf |
| **Critério** | Arquivo PDF válido gerado |

### 8.2 Casos de Teste de Qualidade (Evals)

#### EVAL-001: Acurácia de Extração de Data

```yaml
dataset: 100 comprovantes anotados
metric: exact_match
threshold: >= 95%
formula: (datas_corretas / total) * 100
```

#### EVAL-002: Acurácia de Extração de Valor

```yaml
dataset: 100 comprovantes anotados
metric: fuzzy_match (tolerância: ±0.01)
threshold: >= 95%
formula: (valores_corretos / total) * 100
```

#### EVAL-003: Taxa de Classificação Correta

```yaml
dataset: 100 comprovantes categorizados manualmente
metric: accuracy
threshold: >= 90%
confusion_matrix: gerar para análise de erros
```

#### EVAL-004: Taxa de Erro LLM

```yaml
metric: erro_rate
threshold: <= 5%
formula: (respostas_erro / total_requests) * 100
```

#### EVAL-005: Latência E2E

```yaml
metric: p95_latency_seconds
threshold: <= 30s por arquivo
components: ocr + llm + file_ops
```

### 8.3 Dataset de Referência Sugerido

```
comprovantes_test/
├── conta_luz/
│   ├── comprovante_001.pdf  # Texto nativo, valor R$ 150,00
│   ├── comprovante_002.png  # Screenshot, valor R$ 89,50
│   └── metadata.json        # Ground truth
├── conta_agua/
│   ├── ...
├── naoidentificado/
│   ├── comprovante_generico.pdf
│   └── metadata.json
└── edge_cases/
    ├── pdf_escaneado.pdf    # Qualidade baixa
    ├── multipaginas.pdf     # PDF com várias páginas
    └── valor_alto.pdf       # Valor > 100k (teste de formatação)
```

### 8.4 Critérios de Qualidade

| Dimensão | Critério | Threshold |
|----------|----------|-----------|
| **Precisão** | Data e valor extraídos corretamente | ≥ 95% |
| **Robustez** | Funciona com PDFs de baixa qualidade | ≥ 80% |
| **Performance** | Tempo médio por arquivo | ≤ 15s |
| **Disponibilidade** | Taxa de sucesso em batch | ≥ 98% |
| **Consistência** | Mesmo input → mesmo output | 100% (determinístico) |

---

## Apêndices

### A. Variáveis de Ambiente

```bash
export BOLETO_MODELO_LLM=gemma3:4b
export BOLETO_BASE_URL_LLM=http://localhost:11434/v1
export BOLETO_API_KEY_LLM=ollama
export BOLETO_TESSERACT_LANG=por
export BOLETO_LOG_LEVEL=INFO
```

### B. Exemplo de Execução

```bash
# Modo normal
python boleto_extract.py --path_arquivos ./comprovantes --path_base_contas ./dbcodigocontas.csv

# Dry-run com modelo customizado
python boleto_extract.py --dry-run --modelo llama3.2 --timeout 120 --log-level DEBUG
```

### C. Estrutura de Arquivos

```
boleto_extract/
├── boleto_extract.py      # Script principal
├── dbcodigocontas.csv     # Base de classificação
├── requirements.txt       # Dependências Python
├── Dockerfile             # Container image
├── docker-compose.yml     # Orquestração
├── build.sh               # Script de build
├── README.md              # Documentação
├── boleto_extract.log     # Output de logs
├── comprovantes/          # Diretório de entrada default
└── docs/
    └── plans/
        └── ARCHITECTURE.md  # Este documento
```

---

**Documento gerado via engenharia reversa do código-fonte.**  
**Para atualizações, manter sincronizado com implementação.**
