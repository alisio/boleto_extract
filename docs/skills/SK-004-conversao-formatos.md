# SK-004: Conversão de Formatos

**Versão:** 1.0  
**Spec Relacionada:** [SPEC-004](../specs/SPEC-004-rename-file.md)

## Descrição

Skill responsável por converter arquivos de imagem (JPG, PNG) para formato PDF e renomear arquivos seguindo padrão estruturado.

## Capacidades

| Capacidade | Descrição |
|------------|-----------|
| Conversão IMG→PDF | Converte JPG/PNG para PDF |
| Renomeação padronizada | Aplica formato data-valor-classificacao |
| Tratamento de conflitos | Resolve nomes duplicados com sufixo |
| Modo dry-run | Simula operações sem executar |
| Preservação de originais | Renomeia originais para backup |

## Funções Implementadas

### converter_imagem_para_pdf(imagem_path, destino_pdf)

**Propósito:** Converter imagem para PDF.

```python
def converter_imagem_para_pdf(imagem_path: str, destino_pdf: str) -> bool:
    """
    Converte imagem PNG/JPG para PDF usando Pillow.
    
    - Converte RGBA para RGB automaticamente
    - Resolução de saída: 100 DPI
    """
```

### renomear_arquivo(origem, destino, dry_run)

**Propósito:** Renomear arquivo com tratamento de erros.

```python
def renomear_arquivo(origem: Path, destino: Path, dry_run: bool = False) -> Path:
    """
    Renomeia arquivo com tratamento de conflitos.
    
    - Se destino existe: adiciona sufixo _1, _2, etc.
    - Se dry_run: apenas loga sem executar
    
    Returns:
        Path do arquivo renomeado (pode diferir do destino se houve conflito)
    """
```

## Tecnologias

| Componente | Biblioteca | Versão |
|------------|------------|--------|
| Image Processing | Pillow | 10.4.0 |
| File Operations | pathlib (stdlib) | - |

## Padrão de Nomenclatura

### Formato

```
{data_pagamento}-R${valor_formatado}-{classificacao}.{extensao}
```

### Componentes

| Componente | Formato | Exemplo |
|------------|---------|---------|
| data_pagamento | YYYY-MM-DD | 2023-02-17 |
| valor_formatado | 2 casas decimais | 150.00 |
| classificacao | lowercase | conta_luz |
| extensao | pdf (sempre para imagens) | pdf |

### Exemplos

| Entrada | Saída |
|---------|-------|
| comprovante.pdf | 2023-02-17-R$150.00-conta_luz.pdf |
| foto.jpg | 2023-02-17-R$89.50-conta_agua.pdf |
| scan.png | 2023-02-17-R$1500.00-naoidentificado.pdf |

## Fluxo de Conversão

```
┌─────────────────────┐
│ Arquivo de entrada  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ É imagem?           │
│ (jpg/png/jpeg)      │
└──────────┬──────────┘
       Sim │ Não
           │     └───────────────┐
           ▼                     ▼
┌─────────────────────┐  ┌─────────────────────┐
│ Converter para PDF  │  │ Manter formato      │
│ - Abrir com Pillow  │  │ original            │
│ - Convert RGBA→RGB  │  └──────────┬──────────┘
│ - Salvar como PDF   │             │
└──────────┬──────────┘             │
           │                        │
           ▼                        │
┌─────────────────────┐             │
│ Renomear original   │             │
│ para convertido_*   │             │
└──────────┬──────────┘             │
           │                        │
           └────────────┬───────────┘
                        │
                        ▼
               ┌─────────────────────┐
               │ Verificar conflito  │
               │ de nome             │
               └──────────┬──────────┘
                     Sim  │  Não
                     ┌────┴─────┐
                     │          │
                     ▼          ▼
         ┌───────────────┐  ┌───────────────┐
         │ Adicionar     │  │ Usar nome     │
         │ sufixo _N     │  │ diretamente   │
         └───────┬───────┘  └───────┬───────┘
                 │                  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Arquivo final   │
                 └─────────────────┘
```

## Tratamento de Conflitos

Quando o arquivo de destino já existe:

```python
# Lógica de resolução
contador = 1
while destino_path.exists():
    nome_base = destino_path.stem
    extensao = destino_path.suffix
    novo_nome = f"{nome_base}_{contador}{extensao}"
    destino_path = destino_path.parent / novo_nome
    contador += 1
```

### Exemplos

```
# Arquivo existente
2023-02-17-R$150.00-conta_luz.pdf

# Novos arquivos com mesmo nome
2023-02-17-R$150.00-conta_luz_1.pdf
2023-02-17-R$150.00-conta_luz_2.pdf
```

## Limitações

- Conversão gera PDF de página única
- Resolução fixa em 100 DPI
- Não preserva metadados da imagem original
- Requer espaço para arquivo temporário

## Métricas de Qualidade

| Métrica | Threshold |
|---------|-----------|
| Taxa de sucesso de conversão | ≥ 99% |
| Taxa de sucesso de renomeação | ≥ 99% |
| Tempo de conversão | ≤ 2s por imagem |
| Taxa de conflitos | Monitorar |

## Exemplos de Uso

```python
# Conversão de imagem
converter_imagem_para_pdf(
    imagem_path="comprovantes/foto.jpg",
    destino_pdf="comprovantes/2023-02-17-R$150.00-conta_luz.pdf"
)

# Renomeação com dry-run
renomear_arquivo(
    origem=Path("comprovantes/doc.pdf"),
    destino=Path("comprovantes/2023-02-17-R$150.00-conta_luz.pdf"),
    dry_run=True
)
# Log: [DRY-RUN] Arquivo seria renomeado: ...

# Renomeação real
novo_path = renomear_arquivo(
    origem=Path("comprovantes/doc.pdf"),
    destino=Path("comprovantes/2023-02-17-R$150.00-conta_luz.pdf")
)
# Retorna: Path do arquivo final (pode ter sufixo se houve conflito)
```

## Modo Dry-Run

O modo dry-run permite simular todas as operações sem modificar arquivos:

```bash
python boleto_extract.py --dry-run
```

Quando ativado:
- Logs mostram o que seria feito
- Nenhum arquivo é renomeado ou convertido
- Útil para validar antes de executar em produção
