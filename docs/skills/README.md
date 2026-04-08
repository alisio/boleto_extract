# Skills - Boleto Extract

Este diretório contém a documentação das capacidades executáveis identificadas no sistema.

## Índice de Skills

| ID | Skill | Descrição | Spec |
|----|-------|-----------|------|
| [SK-001](./SK-001-ocr-documentos.md) | OCR de Documentos | Extração de texto de PDFs e imagens | SPEC-001 |
| [SK-002](./SK-002-extracao-inteligente.md) | Extração Inteligente | Uso de LLM para dados estruturados | SPEC-002 |
| [SK-003](./SK-003-classificacao-regras.md) | Classificação por Regras | Pattern matching baseado em CSV | SPEC-003 |
| [SK-004](./SK-004-conversao-formatos.md) | Conversão de Formatos | Conversão de imagens para PDF | SPEC-004 |
| SK-005 | Processamento em Lote | Iteração sobre múltiplos arquivos | - |
| SK-006 | Gestão de Configuração | Configuração via env vars e CLI | - |

## Conceito de Skill

Uma **Skill** representa uma capacidade executável do sistema que:

1. **É atômica:** Executa uma única responsabilidade bem definida
2. **É reutilizável:** Pode ser invocada em diferentes contextos
3. **Tem interface clara:** Entradas e saídas bem documentadas
4. **É testável:** Comportamento verificável de forma isolada

## Mapeamento Skill → Implementação

```
SK-001 (OCR de Documentos)
├── extract_content()
├── extract_text_from_pdf()
└── extract_text_from_image()

SK-002 (Extração Inteligente)
└── enviar_para_llm()

SK-003 (Classificação por Regras)
├── carregar_base_contas()
├── normalizar_codigos()
└── classifica_boleto()

SK-004 (Conversão de Formatos)
├── renomear_arquivo()
└── converter_imagem_para_pdf()

SK-005 (Processamento em Lote)
├── main()
├── listar_arquivos()
└── validar_diretorio()

SK-006 (Gestão de Configuração)
├── obter_configuracao()
├── verificar_dependencias()
└── CLI argument parsing
```

## Stack Tecnológica

| Skill | Bibliotecas |
|-------|-------------|
| SK-001 | PyMuPDF (fitz), pytesseract, Pillow |
| SK-002 | OpenAI SDK |
| SK-003 | Pandas, csv, json, ast |
| SK-004 | Pillow (PIL), pathlib |
| SK-005 | os, pathlib, logging |
| SK-006 | os.environ, argparse, logging |
