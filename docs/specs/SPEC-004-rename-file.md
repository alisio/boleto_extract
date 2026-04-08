# SPEC-004: Renomeação de Arquivo

**Versão:** 1.0  
**Status:** Produção

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | `rename_payment_file` |
| **Tipo** | Skill de File Operations |
| **Dependências** | pathlib, Pillow (para conversão) |

## Descrição

Renomeia arquivos de comprovantes seguindo um padrão estruturado que inclui data do pagamento, valor e classificação. Converte automaticamente imagens para PDF.

## Propósito

Padronizar nomenclatura de comprovantes para facilitar organização, busca e arquivamento.

## Interface

### Entrada

```python
def renomear_arquivo(
    origem: Path | str,
    destino: Path | str,
    dry_run: bool = False
) -> Path:
    """
    Args:
        origem: Caminho do arquivo original
        destino: Caminho de destino com novo nome
        dry_run: Se True, apenas simula sem renomear
        
    Returns:
        Path do arquivo renomeado
        
    Raises:
        PermissionError: Sem permissão para renomear
        OSError: Erro de sistema de arquivos
    """
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|-----------|------|-------------|---------|-----------|
| `data_pagamento` | `string` | Sim | - | Data no formato YYYY-MM-DD |
| `valor_pagamento` | `float` | Sim | - | Valor do pagamento |
| `classificacao` | `string` | Sim | - | Categoria do pagamento |
| `extensao_original` | `string` | Sim | - | Extensão do arquivo original |
| `dry_run` | `bool` | Não | `False` | Modo simulação |

## Formato de Saída

### Padrão de Nome

```
{data_pagamento}-R${valor_formatado}-{classificacao}.{extensao}
```

### Componentes

| Componente | Formato | Exemplo |
|------------|---------|---------|
| `data_pagamento` | YYYY-MM-DD | 2023-02-17 |
| `valor_formatado` | 2 casas decimais | 10799.10 |
| `classificacao` | lowercase, sem espaços | conta_luz |
| `extensao` | pdf (para imagens) ou original | pdf |

### Exemplos de Saída

| Entrada | Saída |
|---------|-------|
| comprovante1.pdf, R$150.00, conta_luz | 2023-02-17-R$150.00-conta_luz.pdf |
| foto.jpg, R$89.50, conta_agua | 2023-01-15-R$89.50-conta_agua.pdf |
| scan.png, R$1500.00, naoidentificado | 2024-03-20-R$1500.00-naoidentificado.pdf |

## Comportamento

### Fluxo de Renomeação

```
┌─────────────────────┐
│ Recebe parâmetros   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Monta novo nome:    │
│ data-R$valor-class  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      Sim
│ É imagem?           │─────────────┐
│ (jpg/png/jpeg)      │             │
└──────────┬──────────┘             │
           │ Não                     │
           │                         ▼
           │              ┌─────────────────────┐
           │              │ Converter para PDF  │
           │              │ (converter_imagem_  │
           │              │ para_pdf)           │
           │              └──────────┬──────────┘
           │                         │
           ▼                         │
┌─────────────────────┐              │
│ dry_run?            │              │
└──────────┬──────────┘              │
           │                         │
     Sim   │   Não                   │
     ┌─────┴──────┐                  │
     │            │                  │
     ▼            ▼                  ▼
┌─────────┐  ┌─────────────────────────────┐
│ Log     │  │ Arquivo destino existe?     │
│ apenas  │  └──────────┬──────────────────┘
└─────────┘             │
                  Sim   │   Não
                  ┌─────┴──────┐
                  │            │
                  ▼            ▼
        ┌─────────────┐  ┌─────────────┐
        │ Adiciona    │  │ Renomeia    │
        │ sufixo _N   │  │ diretamente │
        └──────┬──────┘  └──────┬──────┘
               │                │
               └───────┬────────┘
                       │
                       ▼
               ┌─────────────┐
               │ Return Path │
               └─────────────┘
```

### Conversão de Imagem para PDF

```python
def converter_imagem_para_pdf(imagem_path, destino_pdf):
    """Converte imagem (PNG/JPG) para PDF usando Pillow."""
    with Image.open(imagem_path) as img:
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(destino_pdf, 'PDF', resolution=100.0)
```

### Tratamento de Conflitos

Se o arquivo de destino já existe:
1. Adiciona sufixo numérico: `_1`, `_2`, etc.
2. Incrementa até encontrar nome disponível
3. Log de warning sobre conflito

```python
# Exemplo de resolução de conflito
2023-02-17-R$150.00-conta_luz.pdf      # Original
2023-02-17-R$150.00-conta_luz_1.pdf    # Primeiro conflito
2023-02-17-R$150.00-conta_luz_2.pdf    # Segundo conflito
```

## Regras de Uso

| Regra | Descrição |
|-------|-----------|
| **R1** | Imagens (jpg, jpeg, png) são automaticamente convertidas para PDF |
| **R2** | Data deve estar no formato YYYY-MM-DD |
| **R3** | Valor é formatado com 2 casas decimais |
| **R4** | Conflitos de nome são resolvidos com sufixo numérico |
| **R5** | Modo dry-run não modifica arquivos |
| **R6** | Arquivos originais de imagem são renomeados para `convertido_{nome}` |

## Restrições

| Restrição | Impacto |
|-----------|---------|
| Permissões | Requer permissão de escrita no diretório |
| Espaço | Conversão de imagem gera arquivo adicional |
| Formato | Data e valor devem ser válidos |
| Atomicidade | Renomeação não é transacional |

## Exemplos

### Exemplo 1: Renomeação simples

```python
# Antes
comprovantes/
└── doc123.pdf

# Chamada
renomear_arquivo(
    origem="comprovantes/doc123.pdf",
    destino="comprovantes/2023-02-17-R$150.00-conta_luz.pdf"
)

# Depois
comprovantes/
└── 2023-02-17-R$150.00-conta_luz.pdf
```

### Exemplo 2: Conversão de imagem

```python
# Antes
comprovantes/
└── foto.jpg

# Chamada (internamente converte para PDF)
# destino já com extensão .pdf

# Depois
comprovantes/
├── convertido_foto.jpg    # Original renomeado
└── 2023-02-17-R$89.50-conta_agua.pdf
```

### Exemplo 3: Dry-run

```python
renomear_arquivo(origem, destino, dry_run=True)
# Log: [DRY-RUN] Arquivo seria renomeado: origem -> destino
# Arquivo NÃO é modificado
```

### Exemplo 4: Conflito de nome

```python
# Antes
comprovantes/
└── 2023-02-17-R$150.00-conta_luz.pdf  # Já existe

# Chamada com mesmo nome
# Automaticamente resolve para:

# Depois
comprovantes/
├── 2023-02-17-R$150.00-conta_luz.pdf
└── 2023-02-17-R$150.00-conta_luz_1.pdf  # Novo com sufixo
```

## Métricas

| Métrica | Descrição | Threshold |
|---------|-----------|-----------|
| `rename_success_rate` | Taxa de renomeações bem-sucedidas | ≥ 99% |
| `conversion_success_rate` | Taxa de conversões img→pdf | ≥ 99% |
| `conflict_rate` | Taxa de conflitos de nome | Monitorar |
| `rename_time_ms` | Tempo de renomeação | ≤ 100ms |

## Relacionamentos

- **Depende de:** SPEC-002 (data e valor), SPEC-003 (classificação)
- **Consumido por:** Fluxo principal (`main()`)
- **Implementação:** `renomear_arquivo()`, `converter_imagem_para_pdf()`
