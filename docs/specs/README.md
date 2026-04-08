# Specs - Boleto Extract

Este diretório contém as especificações formais das capacidades do sistema.

## Índice de Specs

| ID | Nome | Descrição |
|----|------|-----------|
| [SPEC-001](./SPEC-001-extract-document-content.md) | Extração de Conteúdo | Extrai texto de PDFs e imagens |
| [SPEC-002](./SPEC-002-extract-payment-info.md) | Extração via LLM | Extrai data e valor usando IA |
| [SPEC-003](./SPEC-003-classify-payment.md) | Classificação | Categoriza pagamento por regras |
| [SPEC-004](./SPEC-004-rename-file.md) | Renomeação | Padroniza nome do arquivo |

## Como usar

Cada spec define:
- **Parâmetros de entrada** (tipos e obrigatoriedade)
- **Estrutura de saída** (schema JSON)
- **Regras de uso** (comportamentos esperados)
- **Restrições** (limitações conhecidas)

## Versionamento

Specs seguem versionamento semântico. Breaking changes incrementam major version.
