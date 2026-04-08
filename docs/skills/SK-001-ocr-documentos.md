# SK-001: OCR de Documentos

**Versão:** 1.0  
**Spec Relacionada:** [SPEC-001](../specs/SPEC-001-extract-document-content.md)

## Descrição

Skill responsável por extrair texto de documentos em diversos formatos (PDF, imagens) utilizando técnicas de OCR (Optical Character Recognition) e extração nativa de texto.

## Capacidades

| Capacidade | Descrição |
|------------|-----------|
| Extração nativa de PDF | Extrai texto selecionável de PDFs |
| OCR de PDF escaneado | Fallback para PDFs sem texto nativo |
| OCR de imagens | Extração de texto de JPG, PNG, JPEG |
| Multi-página | Processa todas as páginas de um PDF |
| Multi-idioma | Configurável para diferentes idiomas |

## Funções Implementadas

### extract_content(file_path)

**Propósito:** Router principal que direciona para extrator apropriado.

```python
def extract_content(file_path: str) -> str:
    """Extrai conteúdo baseado na extensão do arquivo."""
    ext = os.path.splitext(file_path)[-1].lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.jpg', '.jpeg', '.png']:
        return extract_text_from_image(file_path)
    else:
        raise ValueError(f"Formato não suportado: {ext}")
```

### extract_text_from_pdf(pdf_path)

**Propósito:** Extração de texto de arquivos PDF.

**Fluxo:**
1. Abre PDF com PyMuPDF
2. Itera páginas extraindo texto nativo
3. Se vazio → renderiza como imagem + OCR
4. Retorna texto concatenado

### extract_text_from_image(image_path)

**Propósito:** Extração de texto de imagens via Tesseract.

**Fluxo:**
1. Abre imagem com Pillow
2. Valida dimensões
3. Aplica Tesseract OCR
4. Retorna texto extraído

## Tecnologias

| Componente | Biblioteca | Versão |
|------------|------------|--------|
| PDF Processing | PyMuPDF (fitz) | 1.24.9 |
| OCR Engine | pytesseract | 0.3.10 |
| Image Processing | Pillow | 10.4.0 |
| OCR Backend | Tesseract | Sistema |

## Configuração

```bash
# Idioma do Tesseract
export BOLETO_TESSERACT_LANG=por

# Instalação do Tesseract
# macOS:
brew install tesseract tesseract-lang

# Ubuntu:
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

## Limitações

- Qualidade do OCR depende da resolução do documento
- PDFs protegidos por senha não são suportados
- Textos manuscritos têm baixa taxa de reconhecimento
- Performance degradada em documentos grandes

## Métricas de Qualidade

| Métrica | Threshold |
|---------|-----------|
| Acurácia OCR | ≥ 85% |
| Tempo de extração (PDF) | ≤ 5s |
| Tempo de extração (imagem) | ≤ 10s |

## Exemplos de Uso

```python
# PDF com texto
texto = extract_content("comprovante.pdf")

# Imagem
texto = extract_content("screenshot.png")

# Verificar se extraiu algo
if texto.strip():
    print(f"Extraído: {len(texto)} caracteres")
```
