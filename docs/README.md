# Documentação Técnica - Boleto Extract

**Solução de IA para Processamento de Comprovantes de Pagamento**

---

## 📋 Índice Geral

### Arquitetura
- [ARCHITECTURE.md](./plans/ARCHITECTURE.md) - Visão completa da solução

### Especificações (Specs)
- [README.md](./specs/README.md) - Índice de specs
- [SPEC-001](./specs/SPEC-001-extract-document-content.md) - Extração de Conteúdo
- [SPEC-002](./specs/SPEC-002-extract-payment-info.md) - Extração via LLM
- [SPEC-003](./specs/SPEC-003-classify-payment.md) - Classificação
- [SPEC-004](./specs/SPEC-004-rename-file.md) - Renomeação

### Capacidades (Skills)
- [README.md](./skills/README.md) - Índice de skills
- [SK-001](./skills/SK-001-ocr-documentos.md) - OCR de Documentos
- [SK-002](./skills/SK-002-extracao-inteligente.md) - Extração Inteligente
- [SK-003](./skills/SK-003-classificacao-regras.md) - Classificação por Regras
- [SK-004](./skills/SK-004-conversao-formatos.md) - Conversão de Formatos

### Avaliação (Evals)
- [README.md](./evals/README.md) - Proposta de avaliação

---

## 🎯 Resumo Executivo

### O que é

O **Boleto Extract** é uma solução de automação que processa comprovantes de pagamento (PDFs e imagens), extrai informações estruturadas usando IA, e organiza os arquivos de forma padronizada.

### Problema Resolvido

| Antes | Depois |
|-------|--------|
| Comprovantes com nomes genéricos | Nome padronizado: `YYYY-MM-DD-R$VALOR-TIPO.pdf` |
| Identificação manual de data/valor | Extração automática via LLM |
| Classificação inconsistente | Categorização baseada em regras |

### Fluxo Principal

```
📄 PDF/Imagem → 🔍 OCR → 🤖 LLM → 🏷️ Classificação → 📁 Renomeação
```

### KPIs de Qualidade

| Métrica | Target |
|---------|--------|
| Acurácia de extração | ≥ 95% |
| Acurácia de classificação | ≥ 90% |
| Tempo médio por arquivo | ≤ 15s |
| Taxa de sucesso | ≥ 98% |

---

## 🧩 Componentes

### Specs (Especificações)

Definem o **contrato** de cada capacidade:
- Parâmetros de entrada/saída
- Regras de negócio
- Restrições técnicas

### Skills (Capacidades)

Descrevem a **implementação** de cada spec:
- Funções e algoritmos
- Tecnologias utilizadas
- Limitações conhecidas

### Evals (Avaliação)

Propõem **testes de qualidade**:
- Casos de teste funcionais
- Métricas de acurácia
- Datasets de referência

---

## 🔧 Stack Tecnológica

| Componente | Tecnologia |
|------------|------------|
| Runtime | Python 3.10+ |
| PDF Processing | PyMuPDF |
| OCR | Tesseract |
| LLM Interface | OpenAI SDK |
| Data Processing | Pandas |
| Container | Docker |

---

## 📊 Diagrama de Contexto

```
┌─────────────────────────────────────────────────────────────────┐
│                        BOLETO EXTRACT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────┐   ┌────────────┐   ┌─────────┐   ┌─────────┐     │
│   │ Entrada │──▶│ Extração   │──▶│   LLM   │──▶│  Saída  │     │
│   │         │   │ (OCR)      │   │         │   │         │     │
│   │ PDF     │   │ PyMuPDF    │   │ Ollama/ │   │ Rename  │     │
│   │ JPG/PNG │   │ Tesseract  │   │ OpenAI  │   │ Convert │     │
│   └─────────┘   └────────────┘   └─────────┘   └─────────┘     │
│                                                                  │
│                                   │                              │
│                                   ▼                              │
│                        ┌───────────────────┐                     │
│                        │  Classificação    │                     │
│                        │  (CSV de códigos) │                     │
│                        └───────────────────┘                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura de Arquivos Gerados

```
docs/
├── README.md                           # Este índice
├── plans/
│   └── ARCHITECTURE.md                 # Documento principal
├── specs/
│   ├── README.md
│   ├── SPEC-001-extract-document-content.md
│   ├── SPEC-002-extract-payment-info.md
│   ├── SPEC-003-classify-payment.md
│   └── SPEC-004-rename-file.md
├── skills/
│   ├── README.md
│   ├── SK-001-ocr-documentos.md
│   ├── SK-002-extracao-inteligente.md
│   ├── SK-003-classificacao-regras.md
│   └── SK-004-conversao-formatos.md
└── evals/
    └── README.md
```

---

## 🚀 Próximos Passos Sugeridos

1. **Validar specs** com stakeholders
2. **Implementar evals** com dataset real
3. **Estabelecer baseline** de métricas
4. **Configurar CI/CD** para avaliação contínua
5. **Documentar edge cases** encontrados em produção

---

## ✍️ Metadados do Documento

| Campo | Valor |
|-------|-------|
| Gerado em | 2026-04-08 |
| Método | Engenharia reversa de código |
| Versão do código | Commit atual |
| Autor | Análise automatizada |

---

## 📚 Referências

- [README.md](../README.md) - Documentação de uso
- [requirements.txt](../requirements.txt) - Dependências
- [Dockerfile](../Dockerfile) - Container image
