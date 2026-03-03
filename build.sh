#!/bin/bash
# =============================================================================
# Build script multi-plataforma para boloeto_extract
# Suporta: x64 (amd64), Apple Silicon (arm64), Raspberry Pi 5 (arm64)
# =============================================================================

set -e

# Configurações
IMAGE_NAME="boleto_extract"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-docker.io}"
DOCKER_USERNAME="${DOCKER_USERNAME:-}"
TAG="${TAG:-latest}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica se buildx está instalado
check_buildx() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado!"
        exit 1
    fi
    
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx não está disponível!"
        exit 1
    fi
}

# Configura builder multi-plataforma
setup_builder() {
    log_info "Configurando builder multi-plataforma..."
    
    # Cria builder se não existir
    if ! docker buildx inspect multiarch-builder &> /dev/null; then
        docker buildx create --name multiarch-builder --driver docker-container --use
    else
        docker buildx use multiarch-builder
    fi
    
    # Inicializa o builder
    docker buildx inspect --bootstrap
}

# Build para arquitetura específica
build_for_platform() {
    local platform=$1
    local tag_suffix=$2
    
    local full_tag="${DOCKER_USERNAME}/${IMAGE_NAME}:${tag_suffix}"
    
    log_info "Buildando para ${platform}..."
    
    docker buildx build \
        --platform="${platform}" \
        --tag="${full_tag}" \
        --push=false \
        --load \
        .
    
    log_info "Build concluído: ${full_tag}"
}

# Build para todas as plataformas
build_all() {
    log_info "Iniciando build para todas as plataformas..."
    
    # Plataformas: amd64 (x64), arm64 (Apple Silicon + RPi5)
    local platforms="linux/amd64,linux/arm64"
    
    local full_tag="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"
    
    log_info "Plataformas: ${platforms}"
    log_info "Imagem: ${full_tag}"
    
    # Build e push para registry
    docker buildx build \
        --platform="${platforms}" \
        --tag="${full_tag}" \
        --push \
        .
    
    log_info "Build multi-plataforma concluído!"
    log_info "Imagens disponíveis em: ${DOCKER_REGISTRY}/${DOCKER_USERNAME}/${IMAGE_NAME}"
}

# Build local (sem push)
build_local() {
    log_info "Build local para plataforma atual..."
    docker build -t "${IMAGE_NAME}:${TAG}" .
    log_info "Build local concluído!"
}

# Exibe ajuda
show_help() {
    echo "用法: $0 [COMANDO] [OPÇÕES]"
    echo ""
    echo "Comandos:"
    echo "  all         Build para todas as plataformas (amd64, arm64) e faz push"
    echo "  amd64       Build apenas para x64 (linux/amd64)"
    echo "  arm64       Build apenas para ARM64 (Apple Silicon / RPi5)"
    echo "  local       Build local para a plataforma atual"
    echo "  setup       Configura o builder multi-plataforma"
    echo "  help        Mostra esta ajuda"
    echo ""
    echo "Variáveis de ambiente:"
    echo "  DOCKER_USERNAME  Username do Docker Hub (obrigatório para push)"
    echo "  TAG              Tag da imagem (padrão: latest)"
    echo "  DOCKER_REGISTRY  Registry Docker (padrão: docker.io)"
    echo ""
    echo "Exemplos:"
    echo "  $0 setup"
    echo "  DOCKER_USERNAME=meuuser TAG=v1.0.0 $0 all"
    echo "  $0 local"
}

# Main
case "${1:-help}" in
    all)
        check_buildx
        setup_builder
        build_all
        ;;
    amd64)
        check_buildx
        setup_builder
        build_for_platform "linux/amd64" "amd64"
        ;;
    arm64)
        check_buildx
        setup_builder
        build_for_platform "linux/arm64" "arm64"
        ;;
    local)
        build_local
        ;;
    setup)
        check_buildx
        setup_builder
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Comando desconhecido: $1"
        show_help
        exit 1
        ;;
esac
