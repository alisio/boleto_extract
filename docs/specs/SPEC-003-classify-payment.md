# SPEC-003: Classificação de Comprovante

**Versão:** 1.0  
**Status:** Produção

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | `classify_payment` |
| **Tipo** | Skill de Classificação (Rule-based) |
| **Dependências** | Pandas, CSV de códigos |

## Descrição

Classifica o tipo de pagamento com base em correspondência de padrões de texto (keywords) definidos em um arquivo CSV de configuração. Utiliza lógica AND para matching de múltiplos códigos.

## Propósito

Categorizar automaticamente comprovantes de pagamento em tipos pré-definidos (conta de luz, água, cartão, etc.) para organização e posterior análise.

## Interface

### Entrada

```python
def classifica_boleto(texto: str, dataframe: pd.DataFrame) -> str:
    """
    Args:
        texto: Texto extraído do comprovante (será convertido para lowercase)
        dataframe: DataFrame com colunas 'nome_pagamento' e 'codigos'
        
    Returns:
        Nome da classificação identificada ou 'naoidentificado'
    """
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `texto` | `string` | Sim | Texto do comprovante |
| `dataframe` | `pd.DataFrame` | Sim | Base de códigos carregada |

### DataFrame Esperado

```python
# Colunas obrigatórias
df.columns = ['nome_pagamento', 'codigos']

# Tipos
df['nome_pagamento']  # str: identificador da categoria
df['codigos']         # list[str]: lista de keywords (lowercase)
```

### Saída

```json
{
  "type": "string",
  "description": "Identificador da categoria de pagamento",
  "default": "naoidentificado",
  "examples": ["conta_luz", "conta_agua", "cartao_credito"]
}
```

## Estrutura do CSV

### Formato

```csv
nome_pagamento,codigos
conta_luz,"[""LUZ"",""ENERGIA"",""COMPANHIA""]"
conta_agua,"[""AGUA"",""SANEA"",""TRATAMENTO""]"
cartao_credito,"[""CARTAO"",""CREDITO"",""BANCO""]"
```

### Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `nome_pagamento` | string | Identificador único da categoria |
| `codigos` | JSON array | Lista de palavras-chave obrigatórias |

### Regras de Códigos

- **Case-insensitive:** Códigos são normalizados para lowercase
- **Lógica AND:** TODOS os códigos devem estar presentes no texto
- **Ordem importa:** Primeira categoria com match é retornada
- **Parcial:** Substring match (não requer palavra completa)

## Comportamento

### Algoritmo de Classificação

```
PARA CADA categoria NO dataframe:
    códigos = categoria.codigos  # lista normalizada
    
    SE todos(código IN texto_lowercase PARA código EM códigos):
        RETORNA categoria.nome_pagamento
        
RETORNA 'naoidentificado'
```

### Fluxo de Processamento

```
┌─────────────────┐
│ texto.lower()   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FOR categoria   │
│ IN dataframe    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ALL(código IN   │────────▶ MATCH? ────▶ return nome_pagamento
│ texto)?         │              │
└────────┬────────┘              │
         │ NO                    │
         ▼                       │
┌─────────────────┐              │
│ next categoria  │◀─────────────┘
└────────┬────────┘
         │
         ▼ (sem mais categorias)
┌─────────────────┐
│ return          │
│'naoidentificado'│
└─────────────────┘
```

## Regras de Uso

| Regra | Descrição |
|-------|-----------|
| **R1** | Matching é case-insensitive |
| **R2** | Todos os códigos da categoria devem estar presentes (AND) |
| **R3** | Primeira categoria com match é retornada |
| **R4** | Se nenhum match, retorna `naoidentificado` |
| **R5** | Códigos podem ser substrings (não requer palavra completa) |

## Restrições

| Restrição | Impacto |
|-----------|---------|
| Ordem no CSV | Determina prioridade de classificação |
| Ambiguidade | Textos com múltiplos matches retornam primeiro |
| Falsos positivos | Códigos genéricos podem causar classificação incorreta |
| Sem ML | Não aprende com erros, apenas rule-based |

## Exemplos

### Exemplo 1: Match de conta de luz

**CSV:**
```csv
nome_pagamento,codigos
conta_luz,"[""luz"",""energia""]"
```

**Texto:**
```
Companhia de LUZ e ENERGIA
Fatura mensal
```

**Resultado:** `conta_luz` ✓

### Exemplo 2: Match parcial (não classifica)

**CSV:**
```csv
nome_pagamento,codigos
conta_luz,"[""luz"",""energia"",""companhia""]"
```

**Texto:**
```
Fatura de LUZ
(sem "energia" ou "companhia")
```

**Resultado:** `naoidentificado` (faltam códigos)

### Exemplo 3: Prioridade de ordem

**CSV:**
```csv
nome_pagamento,codigos
banco_geral,"[""banco""]"
cartao_credito,"[""banco"",""cartao"",""credito""]"
```

**Texto:**
```
BANCO XYZ - CARTÃO DE CRÉDITO
```

**Resultado:** `banco_geral` (primeira match, mesmo que cartao_credito também matcharia)

**Sugestão:** Ordenar CSV do mais específico para mais genérico.

## Funções Auxiliares

### carregar_base_contas

```python
def carregar_base_contas(path_csv: str) -> pd.DataFrame:
    """Carrega CSV preservando listas na coluna 'codigos'."""
```

### normalizar_codigos

```python
def normalizar_codigos(codigos_raw) -> list[str]:
    """Converte coluna 'codigos' em lista normalizada de strings lowercase."""
```

## Métricas

| Métrica | Descrição | Threshold |
|---------|-----------|-----------|
| `classification_accuracy` | Taxa de classificações corretas | ≥ 90% |
| `unidentified_rate` | Taxa de 'naoidentificado' | ≤ 10% |
| `classification_time` | Tempo de classificação | ≤ 10ms |

## Relacionamentos

- **Depende de:** SPEC-001 (texto extraído)
- **Consumido por:** Fluxo principal (`main()`), SPEC-004 (nome do arquivo)
- **Implementação:** `classifica_boleto()`, `carregar_base_contas()`, `normalizar_codigos()`
