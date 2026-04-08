# SPEC-002: Extração de Informações via LLM

**Versão:** 1.0  
**Status:** Produção

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | `extract_payment_info` |
| **Tipo** | Skill de IA/NLP |
| **Dependências** | OpenAI SDK, endpoint LLM compatível |

## Descrição

Envia texto extraído de comprovantes para um modelo de linguagem (LLM) e obtém informações estruturadas: data do pagamento e valor pago.

## Propósito

Utilizar capacidade de compreensão de linguagem natural de LLMs para extrair dados estruturados de texto não-estruturado (comprovantes de pagamento em diversos formatos e layouts).

## Interface

### Entrada

```python
def enviar_para_llm(
    texto: str,
    prompt: str,
    modelo: str | None = None,
    timeout: int = 60
) -> str:
    """
    Args:
        texto: Texto extraído do comprovante
        prompt: Template de instrução para o LLM
        modelo: Modelo a utilizar (default: CONFIG['modelo_llm'])
        timeout: Timeout em segundos
        
    Returns:
        Resposta do LLM (JSON string ou 'erro')
        
    Raises:
        ValueError: Texto vazio
        openai.APIError: Falha na comunicação com LLM
    """
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|-----------|------|-------------|---------|-----------|
| `texto` | `string` | Sim | - | Texto do comprovante |
| `prompt` | `string` | Sim | - | Instrução para o modelo |
| `modelo` | `string` | Não | `gemma3:4b` | Identificador do modelo |
| `timeout` | `int` | Não | `60` | Timeout em segundos |

### Saída

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "data_pagamento": {
      "type": "string",
      "format": "date",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
      "description": "Data do pagamento no formato ISO (YYYY-MM-DD)"
    },
    "valor_pagamento": {
      "type": "number",
      "format": "float",
      "minimum": 0,
      "description": "Valor pago em formato decimal"
    }
  },
  "required": ["data_pagamento", "valor_pagamento"]
}
```

### Resposta de Erro

Se o LLM não conseguir extrair as informações:
```
"erro"
```

## Prompt Template

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

### Variáveis Dinâmicas

| Variável | Inserção | Origem |
|----------|----------|--------|
| `{texto}` | Após prompt, entre `\`\`\`\`` | Saída de `extract_content()` |

### Contexto Final Enviado

```
{PROMPT}

````
{TEXTO_DO_COMPROVANTE}
````
```

## Comportamento

### Fluxo de Processamento

```
┌─────────────────┐
│ Recebe texto    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Valida texto    │──────▶ ValueError se vazio
│ (não vazio)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Trunca se > 100k│
│ caracteres      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Monta contexto  │
│ (prompt + texto)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ POST /chat/     │
│ completions     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Valida resposta │──────▶ ValueError se vazio
└────────┬────────┘
         │
         ▼
    [Retorna resposta]
```

### Pós-processamento da Resposta

1. Remove blocos `<think>...</think>` (chain-of-thought)
2. Substitui `{{` por `{` e `}}` por `}` (escape de templates)
3. Remove `\\_` → `_`
4. Extrai JSON de blocos markdown (` ```json...``` `)
5. Retorna string limpa

## Regras de Uso

| Regra | Descrição |
|-------|-----------|
| **R1** | Texto vazio não é aceito (raises ValueError) |
| **R2** | Textos > 100k caracteres são truncados com warning |
| **R3** | Resposta "erro" indica impossibilidade de extração |
| **R4** | JSON pode vir em bloco markdown ou puro |
| **R5** | Timeout configurável (default: 60s) |

## Restrições

| Restrição | Impacto |
|-----------|---------|
| Endpoint LLM | Deve ser compatível com API OpenAI |
| Latência | Dependente do modelo e hardware |
| Custo | Tokens consumidos por request |
| Determinismo | Respostas podem variar entre execuções |

## Configuração

```bash
# Modelo LLM
export BOLETO_MODELO_LLM=gemma3:4b

# URL do servidor (Ollama local)
export BOLETO_BASE_URL_LLM=http://localhost:11434/v1

# API Key
export BOLETO_API_KEY_LLM=ollama
```

### Modelos Testados

| Modelo | Provider | Notas |
|--------|----------|-------|
| `gemma3:4b` | Ollama | Default, bom custo-benefício |
| `llama3.2` | Ollama | Alternativa performática |
| `gpt-4` | OpenAI | Alta precisão, maior custo |
| `gpt-3.5-turbo` | OpenAI | Custo intermediário |

## Exemplos

### Exemplo 1: Extração bem-sucedida

**Input (texto):**
```
COMPROVANTE DE PAGAMENTO
Banco XYZ
Data: 17/02/2023
Valor pago: R$ 10.799,10
Beneficiário: Cia Elétrica
```

**Output:**
```json
{
  "data_pagamento": "2023-02-17",
  "valor_pagamento": 10799.10
}
```

### Exemplo 2: Dados não encontrados

**Input (texto):**
```
Lorem ipsum dolor sit amet...
(texto sem informações de pagamento)
```

**Output:**
```
erro
```

### Exemplo 3: JSON em markdown

**Resposta do LLM:**
````
Analisando o comprovante...

```json
{
  "data_pagamento": "2023-02-17",
  "valor_pagamento": 150.00
}
```
````

**Output processado:**
```json
{"data_pagamento": "2023-02-17", "valor_pagamento": 150.00}
```

## Métricas

| Métrica | Descrição | Threshold |
|---------|-----------|-----------|
| `extraction_accuracy` | Taxa de extrações corretas | ≥ 95% |
| `llm_latency_p95` | Latência percentil 95 | ≤ 10s |
| `error_rate` | Taxa de respostas "erro" | ≤ 5% |
| `tokens_per_request` | Tokens médios por request | Monitorar |

## Relacionamentos

- **Depende de:** SPEC-001 (texto extraído)
- **Consumido por:** Fluxo principal (`main()`)
- **Implementação:** `enviar_para_llm()`
