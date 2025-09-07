import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DB_CONFIG = {
    "HOST": os.getenv("QDRANT_HOST", "localhost"),
    "PORT": int(os.getenv("QDRANT_PORT", 6333)),
    "COLLECTION_NAME": os.getenv("QDRANT_COLLECTION", "rag_collection"),
    "API_KEY": os.getenv("QDRANT_API_KEY", ""),
}

# Redis配置
REDIS_CONFIG = {
    "HOST": os.getenv("REDIS_HOST", "localhost"),
    "PORT": int(os.getenv("REDIS_PORT", 6379)),
    "DB": int(os.getenv("REDIS_DB", 0)),
    "PASSWORD": os.getenv("REDIS_PASSWORD", None),
    "CACHE_TTL": int(os.getenv("REDIS_CACHE_TTL", 3600)),  # 1小时
}

# 模型配置
MODEL_CONFIG = {
    "tencent": {
        "BASE_URL": os.getenv("OPENAI_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1"),
        "API_KEY": os.getenv("HUNYUAN_API_KEY", ""),
    },
    "dashscope": {
        "BASE_URL": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "API_KEY": os.getenv("DASHSCOPE_API_KEY", ""),
    }
}

# 默认模型设置
DEFAULT_MODELS = {
    "PROVIDER": os.getenv("MODEL_PROVIDER", "dashscope"),
    "CHAT": os.getenv("CHAT_MODEL", "qwen-flash"),
    "EMBEDDING": os.getenv("EMBEDDING_MODEL", "text-embedding-v2"),
    "RERANK": os.getenv("RERANK_MODEL", "gte-rerank-v2"),
}

# 安全配置
SECURITY_CONFIG = {
    "API_KEY": os.getenv("API_KEY", ""),
    "RATE_LIMIT": int(os.getenv("RATE_LIMIT", 100)),  # 每分钟请求限制
    "JWT_SECRET": os.getenv("JWT_SECRET", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidGVzdF91c2VyIiwic2NvcGUiOiJjaGF0IiwiZXhwIjoxNzU3MjMwOTc2fQ.vjwl5AOwRDtbShGa4NyZUz0NJDCnctlGlm1V6-jJQ8Y"),
    "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    "TOKEN_EXPIRE_MINUTES": int(os.getenv("TOKEN_EXPIRE_MINUTES", 30)),
}

# 性能配置
PERFORMANCE_CONFIG = {
    "CACHE_ENABLED": os.getenv("CACHE_ENABLED", "true").lower() == "true",
    "ASYNC_ENABLED": os.getenv("ASYNC_ENABLED", "true").lower() == "true",
    "MAX_WORKERS": int(os.getenv("MAX_WORKERS", 4)),
    "BATCH_SIZE": int(os.getenv("BATCH_SIZE", 10)),
    "CONNECTION_TIMEOUT": int(os.getenv("CONNECTION_TIMEOUT", 60)),  # 优化为60秒
    "REQUEST_TIMEOUT": int(os.getenv("REQUEST_TIMEOUT", 60)),  # 新增请求超时配置
    "CHAT_TIMEOUT": int(os.getenv("CHAT_TIMEOUT", 60)),  # 新增聊天超时配置
}

# 监控配置
MONITORING_CONFIG = {
    "PROMETHEUS_ENABLED": os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
    "METRICS_PORT": int(os.getenv("METRICS_PORT", 9090)),
    "HEALTH_CHECK_INTERVAL": int(os.getenv("HEALTH_CHECK_INTERVAL", 60)),
}

# 部署配置
DEPLOYMENT_CONFIG = {
    "HOST": os.getenv("HOST", "127.0.0.1"),
    "PORT": int(os.getenv("PORT", 8000)),
    "RELOAD": os.getenv("RELOAD", "false").lower() == "true",
    "WORKERS": int(os.getenv("WORKERS", 4)),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "info"),
}

# 文档处理配置
DOCUMENT_CONFIG = {
    "MAX_FILE_SIZE": int(os.getenv("MAX_FILE_SIZE", 10485760)),  # 10MB
    "ALLOWED_EXTENSIONS": os.getenv("ALLOWED_EXTENSIONS", ".txt,.pdf,.docx,.doc").split(","),
    "CHUNK_SIZE": int(os.getenv("CHUNK_SIZE", 500)),
    "CHUNK_OVERLAP": int(os.getenv("CHUNK_OVERLAP", 50)),
    "OCR_ENABLED": os.getenv("OCR_ENABLED", "false").lower() == "true",
}

def get_config() -> Dict[str, Any]:
    """获取完整配置"""
    return {
        "db": DB_CONFIG,
        "redis": REDIS_CONFIG,
        "model": MODEL_CONFIG,
        "default_models": DEFAULT_MODELS,
        "security": SECURITY_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "monitoring": MONITORING_CONFIG,
        "deployment": DEPLOYMENT_CONFIG,
        "document": DOCUMENT_CONFIG,
    }