# SPEC-001: Extração de Conteúdo de Documento

**Versão:** 1.0  
**Status:** Produção

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | `extract_document_content` |
| **Tipo** | Skill de Extração |
| **Dependências** | PyMuPDF, Tesseract OCR, Pillow |

## Descrição

Extrai texto legível de documentos PDF ou imagens (JPG, PNG), utilizando extração nativa de texto para PDFs com conteúdo textual ou OCR (Optical Character Recognition) para imagens e PDFs escaneados.

## Propósito

Converter documentos visuais (comprovantes de pagamento) em texto processável para análise subsequente por LLM.

## Interface

### Entrada

```python
def extract_content(file_path: str) -> str:
    """
    Args:
        file_path: Caminho absoluto do arquivo a ser processado
        
    Returns:
        Texto extraído do documento
        
    Raises:
        FileNotFoundError: Arquivo não existe
        ValueError: Formato não suportado ou arquivo inválido
    """
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|-----------|------|-------------|---------|-----------|
| `file_path` | `string` | Sim | - | Caminho absoluto do arquivo |

### Saída

```json
{
  "type": "string",
  "description": "Texto extraído do documento",
  "encoding": "utf-8",
  "constraints": {
    "max_length": 100000
  }
}
```

## Comportamento

### Fluxo de Decisão

```
┌─────────────────┐
│ Recebe file_path │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Valida existência│
│ do arquivo       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     .pdf      ┌──────────────────┐
│ Verifica extensão├─────────────▶│extract_text_from_│
│                  │              │pdf()             │
└────────┬────────┘              └────────┬─────────┘
         │                                 │
  .jpg/.png/.jpeg                         │
         │                                 ▼
         ▼                      ┌──────────────────┐
┌─────────────────┐             │ Texto extraído?   │
│extract_text_from│             └────────┬─────────┘
│image()          │                      │
└────────┬────────┘               Sim    │    Não
         │                        ┌──────┴──────┐
         ▼                        │             │
    [Retorna texto]           [Retorna]    [OCR fallback]
```

### PDFs

1. Abre documento com PyMuPDF (`fitz.open`)
2. Itera sobre páginas extraindo texto nativo (`page.get_text()`)
3. Se texto vazio: renderiza páginas como imagem e aplica OCR
4. Retorna concatenação de todas as páginas

### Imagens

1. Abre imagem com Pillow (`Image.open`)
2. Valida dimensões (não pode ser 0x0)
3. Aplica Tesseract OCR (`pytesseract.image_to_string`)
4. Retorna texto extraído

## Regras de Uso

| Regra | Descrição |
|-------|-----------|
| **R1** | Arquivos PDF com texto nativo: extração direta sem OCR |
| **R2** | PDFs escaneados: fallback automático para OCR |
| **R3** | Imagens: OCR direto via Tesseract |
| **R4** | Idioma OCR configurável via `BOLETO_TESSERACT_LANG` |
| **R5** | Truncamento automático se texto > 100k caracteres |

## Restrições

| Restrição | Impacto |
|-----------|---------|
| Formatos suportados | Apenas `.pdf`, `.jpg`, `.jpeg`, `.png` |
| Dependência externa | Tesseract OCR deve estar instalado no sistema |
| Qualidade OCR | Depende da resolução e clareza do documento |
| Performance | OCR é significativamente mais lento que extração nativa |

## Configuração

```bash
# Idioma do Tesseract (default: português)
export BOLETO_TESSERACT_LANG=por

# Para instalar Tesseract (macOS)
brew install tesseract tesseract-lang

# Para instalar Tesseract (Ubuntu)
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

## Exemplos

### Exemplo 1: PDF com texto

```python
texto = extract_content("/path/to/comprovante.pdf")
# Retorna: "COMPROVANTE DE PAGAMENTO\nData: 17/02/2023\nValor: R$ 150,00..."
```

### Exemplo 2: Imagem PNG

```python
texto = extract_content("/path/to/screenshot.png")
# Retorna: "Pagamento confirmado\n17 de fevereiro de 2023..."
```

### Exemplo 3: Erro - formato não suportado

```python
texto = extract_content("/path/to/arquivo.docx")
# Raises: ValueError("Formato de arquivo não suportado: .docx")
```

## Métricas

| Métrica | Descrição | Threshold |
|---------|-----------|-----------|
| `ocr_accuracy` | % de palavras corretas | ≥ 85% |
| `extraction_time_seconds` | Tempo de processamento | ≤ 10s |
| `text_yield_ratio` | Chars extraídos / tamanho arquivo | > 0 |

## Relacionamentos

- **Consumido por:** SPEC-002 (Extração via LLM), SPEC-003 (Classificação)
- **Implementação:** `extract_content()`, `extract_text_from_pdf()`, `extract_text_from_image()`
