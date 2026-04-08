# Evals - Boleto Extract

Este diretório contém a proposta de avaliação (Evals) para validação da solução.

## Estrutura

```
evals/
├── README.md                    # Este arquivo
├── test_cases/
│   ├── functional/              # Testes funcionais
│   └── quality/                 # Testes de qualidade (acurácia)
├── datasets/
│   └── ground_truth.json        # Dataset de referência anotado
└── metrics/
    └── thresholds.json          # Limiares de qualidade
```

## Categorias de Avaliação

### 1. Testes Funcionais

Validam comportamento correto das funções.

| ID | Caso | Descrição |
|----|------|-----------|
| FUNC-001 | PDF com texto | Extração nativa sem OCR |
| FUNC-002 | PDF escaneado | Fallback para OCR |
| FUNC-003 | Imagem JPG/PNG | OCR direto |
| FUNC-004 | Classificação match | Keywords encontradas |
| FUNC-005 | Classificação miss | Nenhum match → naoidentificado |
| FUNC-006 | LLM sucesso | JSON válido retornado |
| FUNC-007 | LLM erro | Retorno "erro" para dados ausentes |
| FUNC-008 | Conversão IMG→PDF | Arquivo PDF gerado |
| FUNC-009 | Conflito de nome | Sufixo adicionado |
| FUNC-010 | Dry-run | Nenhum arquivo modificado |

### 2. Testes de Qualidade (Evals)

Medem acurácia e performance.

| ID | Métrica | Threshold | Dataset |
|----|---------|-----------|---------|
| EVAL-001 | Acurácia de data | ≥ 95% | 100 comprovantes |
| EVAL-002 | Acurácia de valor | ≥ 95% | 100 comprovantes |
| EVAL-003 | Acurácia de classificação | ≥ 90% | 100 comprovantes |
| EVAL-004 | Taxa de erro LLM | ≤ 5% | 100 comprovantes |
| EVAL-005 | Latência E2E P95 | ≤ 30s | 100 comprovantes |

## Dataset de Referência

### Estrutura ground_truth.json

```json
{
  "version": "1.0",
  "created_at": "2024-01-15",
  "samples": [
    {
      "id": "sample_001",
      "file": "conta_luz_001.pdf",
      "expected": {
        "data_pagamento": "2023-02-17",
        "valor_pagamento": 150.00,
        "classificacao": "conta_luz"
      },
      "metadata": {
        "formato": "pdf_nativo",
        "banco": "Banco XYZ",
        "qualidade": "alta"
      }
    }
  ]
}
```

### Categorias de Samples

| Categoria | Quantidade | Descrição |
|-----------|------------|-----------|
| conta_luz | 15 | Faturas de energia |
| conta_agua | 15 | Faturas de saneamento |
| cartao_credito | 15 | Faturas de cartão |
| naoidentificado | 10 | Comprovantes genéricos |
| edge_cases | 15 | Casos difíceis |
| pdf_escaneado | 15 | PDFs de baixa qualidade |
| imagens | 15 | JPG/PNG |

## Execução de Evals

### Script de Avaliação (Proposto)

```python
# eval_runner.py
import json
from pathlib import Path
from boleto_extract import extract_content, enviar_para_llm, classifica_boleto

def run_evals(ground_truth_path: str, results_path: str):
    """Executa avaliação completa contra ground truth."""
    
    with open(ground_truth_path) as f:
        ground_truth = json.load(f)
    
    results = {
        "data_accuracy": 0,
        "valor_accuracy": 0,
        "classificacao_accuracy": 0,
        "error_rate": 0,
        "samples": []
    }
    
    for sample in ground_truth["samples"]:
        # Executar pipeline
        # Comparar com expected
        # Registrar resultado
        pass
    
    # Calcular métricas agregadas
    # Salvar resultados
    
    return results
```

### Métricas de Comparação

| Métrica | Cálculo |
|---------|---------|
| exact_match | `predicted == expected` |
| date_match | Comparação de string de data |
| value_match | `abs(predicted - expected) <= 0.01` |
| classification_match | String exata |

## Critérios de Aprovação

### Threshold Mínimos

| Dimensão | Critério | Mínimo |
|----------|----------|--------|
| Precisão | Data correta | 95% |
| Precisão | Valor correto | 95% |
| Precisão | Classificação correta | 90% |
| Robustez | Funciona com baixa qualidade | 80% |
| Performance | Tempo médio | ≤ 15s |
| Disponibilidade | Taxa de sucesso | ≥ 98% |

### Matriz de Confusão (Classificação)

```
                    Predito
                 Luz  Água  Cartão  NI
Esperado  Luz    [TP]  [FP]  [FP]   [FN]
          Água   [FP]  [TP]  [FP]   [FN]
          Cartão [FP]  [FP]  [TP]   [FN]
          NI     [FP]  [FP]  [FP]   [TN]
```

## Edge Cases

### Lista de Casos Difíceis

| ID | Descrição | Desafio |
|----|-----------|---------|
| EDGE-001 | PDF multipáginas | Dados em páginas diferentes |
| EDGE-002 | Valor alto | R$ > 100.000,00 |
| EDGE-003 | Valor baixo | R$ < 1,00 |
| EDGE-004 | Data passada | Anos < 2000 |
| EDGE-005 | Data futura | Anos > 2030 |
| EDGE-006 | OCR ruim | Documento desbotado |
| EDGE-007 | Múltiplos valores | Várias datas/valores |
| EDGE-008 | Formato incomum | Layout não padrão |
| EDGE-009 | Texto misto | Português + Inglês |
| EDGE-010 | Comprovante PIX | Formato específico |

## Relatórios

### Formato de Relatório

```json
{
  "run_id": "eval_2024_01_15_001",
  "timestamp": "2024-01-15T10:30:00Z",
  "model": "gemma3:4b",
  "total_samples": 100,
  "metrics": {
    "data_accuracy": 0.96,
    "valor_accuracy": 0.97,
    "classificacao_accuracy": 0.92,
    "error_rate": 0.03,
    "avg_latency_seconds": 8.5,
    "p95_latency_seconds": 15.2
  },
  "passed": true,
  "failures": [
    {
      "sample_id": "sample_042",
      "expected": {"data_pagamento": "2023-02-17"},
      "predicted": {"data_pagamento": "2023-02-07"},
      "error_type": "date_mismatch"
    }
  ]
}
```

## Frequência de Execução

| Trigger | Frequência | Escopo |
|---------|------------|--------|
| PR Merge | On merge | Full suite |
| Release | Pre-release | Full suite + edge cases |
| Model change | On change | Full suite |
| Weekly | Semanal | Regression test |

## Roadmap de Evals

### Fase 1 (Atual)
- [ ] Definir ground truth dataset
- [ ] Implementar eval_runner.py
- [ ] Estabelecer baselines

### Fase 2
- [ ] Automatizar execução em CI
- [ ] Dashboard de métricas
- [ ] Alertas de regressão

### Fase 3
- [ ] A/B testing de prompts
- [ ] Comparação entre modelos
- [ ] Análise de drift
