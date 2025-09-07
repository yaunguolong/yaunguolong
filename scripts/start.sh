#!/bin/bash

# RAG应用启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi
    
    # 检查Docker（如果使用Docker部署）
    if [ "$1" = "docker" ] && ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 安装Python依赖
install_dependencies() {
    log_info "安装Python依赖..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        if [ $? -eq 0 ]; then
            log_success "Python依赖安装成功"
        else
            log_error "Python依赖安装失败"
            exit 1
        fi
    else
        log_error "requirements.txt 不存在"
        exit 1
    fi
}

# 启动开发服务器
start_dev() {
    log_info "启动开发服务器..."
    uvicorn api.mainV3:app --host 0.0.0.0 --port 8000 --reload
}

# 启动生产服务器
start_prod() {
    log_info "启动生产服务器..."
    gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 api.mainV3:app
}

# 使用Docker启动
start_docker() {
    log_info "使用Docker启动..."
    
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d
        if [ $? -eq 0 ]; then
            log_success "Docker服务启动成功"
            echo -e "\n服务访问地址:"
            echo "API文档: http://localhost:8000/docs"
            echo "健康检查: http://localhost:8000/health"
            echo "监控面板: http://localhost:3000 (admin/admin)"
        else
            log_error "Docker服务启动失败"
            exit 1
        fi
    else
        log_error "docker-compose.yml 不存在"
        exit 1
    fi
}

# 显示帮助
show_help() {
    echo "用法: $0 [模式]"
    echo ""
    echo "模式:"
    echo "  dev     启动开发服务器 (默认)"
    echo "  prod    启动生产服务器"
    echo "  docker  使用Docker启动"
    echo "  install 仅安装依赖"
    echo "  help    显示帮助信息"
    echo ""
    echo "环境变量:"
    echo "  请确保设置了必要的环境变量，参见 .env.example"
}

# 主函数
main() {
    local mode=${1:-dev}
    
    case $mode in
        dev)
            check_dependencies
            install_dependencies
            start_dev
            ;;
        prod)
            check_dependencies
            install_dependencies
            start_prod
            ;;
        docker)
            check_dependencies docker
            start_docker
            ;;
        install)
            install_dependencies
            ;;
        help)
            show_help
            ;;
        *)
            log_error "未知模式: $mode"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"