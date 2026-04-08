# SK-003: Classificação por Regras

**Versão:** 1.0  
**Spec Relacionada:** [SPEC-003](../specs/SPEC-003-classify-payment.md)

## Descrição

Skill responsável por classificar comprovantes de pagamento em categorias predefinidas através de correspondência de padrões (pattern matching) baseada em um arquivo CSV de regras.

## Capacidades

| Capacidade | Descrição |
|------------|-----------|
| Pattern matching | Busca keywords no texto do comprovante |
| Multi-código | Suporta múltiplos códigos por categoria (AND) |
| Case-insensitive | Matching ignorando maiúsculas/minúsculas |
| Configurável | Regras definidas em CSV externo |
| Fallback | Retorna "naoidentificado" quando não há match |

## Funções Implementadas

### carregar_base_contas(path_csv)

**Propósito:** Carregar e parsear arquivo CSV de classificação.

```python
def carregar_base_contas(path_csv: str) -> pd.DataFrame:
    """
    Carrega CSV preservando listas na coluna 'codigos'.
    
    Returns:
        DataFrame com colunas: nome_pagamento, codigos
    """
```

### normalizar_codigos(codigos_raw)

**Propósito:** Converter coluna de códigos em lista normalizada.

```python
def normalizar_codigos(codigos_raw) -> list[str]:
    """
    Converte códigos para lista de strings lowercase.
    
    Suporta:
    - JSON array: '["codigo1", "codigo2"]'
    - Python literal: ['codigo1', 'codigo2']
    - String simples: 'codigo1,codigo2'
    """
```

### classifica_boleto(texto, dataframe)

**Propósito:** Classificar comprovante baseado em regras.

```python
def classifica_boleto(texto: str, dataframe: pd.DataFrame) -> str:
    """
    Classifica boleto por pattern matching.
    
    Algoritmo:
    1. Converte texto para lowercase
    2. Para cada categoria, verifica se TODOS os códigos estão presentes
    3. Retorna primeira categoria com match
    4. Se nenhum match, retorna 'naoidentificado'
    """
```

## Tecnologias

| Componente | Biblioteca | Versão |
|------------|------------|--------|
| Data Processing | Pandas | 2.2.2 |
| CSV Parsing | csv (stdlib) | - |
| JSON Parsing | json (stdlib) | - |
| Literal Eval | ast (stdlib) | - |

## Formato do CSV

```csv
nome_pagamento,codigos
conta_luz,"[""LUZ"",""ENERGIA"",""COMPANHIA""]"
conta_agua,"[""AGUA"",""SANEA""]"
cartao_credito,"[""CARTAO"",""CREDITO""]"
```

### Colunas

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `nome_pagamento` | string | Identificador da categoria |
| `codigos` | JSON array | Lista de keywords obrigatórias |

## Algoritmo de Classificação

```
FUNÇÃO classifica_boleto(texto, dataframe):
    texto_lower = texto.to_lowercase()
    
    PARA CADA linha EM dataframe:
        nome = linha.nome_pagamento
        codigos = linha.codigos  # lista normalizada
        
        SE todos(codigo EM texto_lower PARA codigo EM codigos):
            RETORNA nome
    
    RETORNA 'naoidentificado'
```

### Características

| Característica | Comportamento |
|----------------|---------------|
| Lógica de match | AND (todos códigos devem estar presentes) |
| Case sensitivity | Insensitive (lowercase comparison) |
| Prioridade | Ordem no CSV determina prioridade |
| Substring match | Sim (código pode ser parte de palavra) |

## Limitações

- Sem aprendizado (rule-based puro)
- Ordem do CSV afeta resultado em caso de ambiguidade
- Códigos genéricos podem causar falsos positivos
- Não considera contexto semântico

## Métricas de Qualidade

| Métrica | Threshold |
|---------|-----------|
| Acurácia de classificação | ≥ 90% |
| Taxa de não identificados | ≤ 15% |
| Tempo de classificação | ≤ 10ms |

## Exemplos de Uso

```python
# Carregar base
df = carregar_base_contas("dbcodigocontas.csv")
df['codigos'] = df['codigos'].apply(normalizar_codigos)

# Classificar
texto = "Companhia de LUZ e ENERGIA - Fatura mensal"
categoria = classifica_boleto(texto, df)
# Resultado: 'conta_luz'

# Sem match
texto = "Documento genérico sem keywords"
categoria = classifica_boleto(texto, df)
# Resultado: 'naoidentificado'
```

## Boas Práticas para CSV

1. **Ordenar do específico ao genérico:** Categorias mais específicas primeiro
2. **Evitar códigos ambíguos:** "banco" é muito genérico
3. **Usar múltiplos códigos:** Aumenta precisão
4. **Testar com exemplos reais:** Validar com comprovantes do domínio
5. **Documentar exceções:** Anotar casos edge conhecidos
