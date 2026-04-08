# SK-002: Extração Inteligente via LLM

**Versão:** 1.0  
**Spec Relacionada:** [SPEC-002](../specs/SPEC-002-extract-payment-info.md)

## Descrição

Skill responsável por utilizar modelos de linguagem (LLM) para extrair informações estruturadas (data e valor de pagamento) de texto não-estruturado.

## Capacidades

| Capacidade | Descrição |
|------------|-----------|
| Extração de data | Identifica data de pagamento em diversos formatos |
| Extração de valor | Identifica valor monetário em diversos formatos |
| Normalização | Converte para formato padronizado (ISO date, float) |
| Multi-modelo | Compatível com qualquer API OpenAI-compatible |
| Fallback | Retorna "erro" quando não consegue extrair |

## Função Implementada

### enviar_para_llm(texto, prompt, modelo, timeout)

**Propósito:** Interface com modelo de linguagem para extração de dados.

```python
def enviar_para_llm(texto: str, prompt: str, modelo: str = None, timeout: int = 60) -> str:
    """
    Envia texto para LLM e retorna resposta formatada.
    
    Returns:
        JSON string com data_pagamento e valor_pagamento
        ou 'erro' se não conseguir extrair
    """
```

## Prompt Engineering

### Template Utilizado

O prompt segue estrutura clara:
1. **Instrução principal:** O que extrair
2. **Regras específicas:** Formato esperado
3. **Few-shot examples:** 2 exemplos de output
4. **Delimitador:** Texto entre backticks

### Técnicas Aplicadas

| Técnica | Aplicação |
|---------|-----------|
| Few-shot learning | 2 exemplos de JSON válido |
| Instruction tuning | Regras claras e numeradas |
| Output formatting | JSON schema definido |
| Error handling | Instrução para retornar "erro" |

## Tecnologias

| Componente | Biblioteca | Versão |
|------------|------------|--------|
| LLM Client | OpenAI SDK | 1.38.0 |
| HTTP Client | httpx | < 0.28 |

## Configuração

```bash
# Modelo LLM
export BOLETO_MODELO_LLM=gemma3:4b

# URL do servidor
export BOLETO_BASE_URL_LLM=http://localhost:11434/v1

# API Key
export BOLETO_API_KEY_LLM=ollama
```

## Modelos Compatíveis

| Modelo | Provider | Notas |
|--------|----------|-------|
| gemma3:4b | Ollama | Default, local |
| llama3.2 | Ollama | Alternativa local |
| gpt-4 | OpenAI | Cloud, alta precisão |
| gpt-3.5-turbo | OpenAI | Cloud, custo menor |
| claude-3 | Anthropic | Via proxy OpenAI |

## Pós-processamento

A resposta do LLM passa por limpeza:

```python
# Remove chain-of-thought
resposta = re.sub(r'<think>.*?</think>', '', resposta)

# Corrige escapes de template
resposta = resposta.replace('{{', '{').replace('}}', '}')

# Extrai JSON de markdown
match = re.search(r"```json\s*(\{.*?\})\s*```", resposta)
```

## Limitações

- Dependente de disponibilidade do LLM
- Latência variável (2-30s dependendo do modelo)
- Não determinístico (respostas podem variar)
- Custo por token em APIs pagas
- Limite de contexto do modelo

## Métricas de Qualidade

| Métrica | Threshold |
|---------|-----------|
| Acurácia de extração | ≥ 95% |
| Latência P95 | ≤ 15s |
| Taxa de erro | ≤ 5% |

## Exemplos de Uso

```python
# Extração bem-sucedida
resultado = enviar_para_llm(
    texto="Pagamento de R$ 150,00 em 17/02/2023",
    prompt=PROMPT,
    modelo="gemma3:4b"
)
# Resultado: '{"data_pagamento": "2023-02-17", "valor_pagamento": 150.00}'

# Falha de extração
resultado = enviar_para_llm(
    texto="Lorem ipsum dolor sit amet",
    prompt=PROMPT
)
# Resultado: 'erro'
```

## Considerações de Segurança

⚠️ **ATENÇÃO:** O texto completo do comprovante é enviado ao LLM.

- Prefira modelos locais (Ollama) para dados sensíveis
- Verifique políticas de privacidade de provedores cloud
- Dados podem conter CPF, CNPJ, dados bancários
- Considere LGPD/GDPR ao processar dados de terceiros
