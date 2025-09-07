"""
增强的API路由模块 - 包含安全认证、速率限制和监控
"""
import os
import uuid
import time
import asyncio
import tempfile
import shutil
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, HTTPException, File, UploadFile, Query, Body, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, generate_latest

from modularizationV2.core.chain import get_rag_chain
from modularizationV2.core.vector_store import get_vector_store_manager
from modularizationV2.core.model import EnhancedModel
from modularizationV2.core.base_prompt import PROMPTS, get_rag_prompt
from modularizationV2.loader.load import EnhancedLoader, load_documents_from_file
from modularizationV2.core.chunk import get_text_splitter
from modularizationV2.logger.log import get_logger
from modularizationV2.config.config import SECURITY_CONFIG, DOCUMENT_CONFIG, PERFORMANCE_CONFIG

logger = get_logger()

router = APIRouter()
security = HTTPBearer()

# Prometheus监控指标
QUERY_COUNTER = Counter('rag_query_total', 'Total RAG queries', ['chain_type', 'status'])
QUERY_DURATION = Histogram('rag_query_duration_seconds', 'RAG query duration', ['chain_type'])
UPLOAD_COUNTER = Counter('document_upload_total', 'Total document uploads', ['file_type', 'status'])
RATE_LIMIT_COUNTER = Counter('rate_limit_exceeded_total', 'Total rate limit exceeded')

# 速率限制器
limiter = Limiter(key_func=get_remote_address)


# JWT认证
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECURITY_CONFIG["JWT_SECRET"],
            algorithms=[SECURITY_CONFIG["JWT_ALGORITHM"]]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# 简单的用户验证（生产环境应该使用数据库）
def authenticate_user(username: str, password: str) -> bool:
    """简单的用户认证（生产环境应该使用数据库）"""
    # 这里使用简单的硬编码验证，生产环境应该连接数据库
    valid_users = {
        "admin": "admin123",
        "user": "user123",
        "test": "test123"
    }
    return valid_users.get(username) == password


# 速率限制异常处理 - 移到mainV3.py中处理

# 请求/响应模型
class TokenRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class QueryRequest(BaseModel):
    query: str = Field(..., description="用户查询问题")
    collection_name: str = Field("My_collection_V1", description="向量集合名称")
    top_k: int = Field(5, description="检索结果数量", ge=1, le=20)
    chain_type: str = Field("basic",
                            description="链类型: basic, rerank, fusion, multi_query, complex, compressor, hybrid")
    session_id: Optional[str] = Field(None, description="会话ID")


class QueryResponse(BaseModel):
    answer: str
    retrieved_count: int
    collection_name: str
    processing_time: float
    chain_type: str


class DocumentUploadResponse(BaseModel):
    status: str
    filename: str
    document_count: int
    chunk_count: int
    document_ids: List[str]
    collection_name: str
    processing_type: str


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    components: Dict[str, str]


# Token生成端点
@router.post("/token", response_model=TokenResponse)
async def create_access_token(token_request: TokenRequest):
    """生成JWT访问token"""
    # 验证用户凭据
    if not authenticate_user(token_request.username, token_request.password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建token载荷
    expire = time.time() + (SECURITY_CONFIG["TOKEN_EXPIRE_MINUTES"] * 60)
    payload = {
        "sub": token_request.username,
        "exp": expire,
        "iat": time.time(),
        "scope": "chat"
    }

    # 生成token
    access_token = jwt.encode(
        payload,
        SECURITY_CONFIG["JWT_SECRET"],
        algorithm=SECURITY_CONFIG["JWT_ALGORITHM"]
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=SECURITY_CONFIG["TOKEN_EXPIRE_MINUTES"] * 60
    )


# 健康检查端点
@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "components": {
            "vector_db": "connected",
            "model": "available",
            "cache": "enabled" if PERFORMANCE_CONFIG["CACHE_ENABLED"] else "disabled"
        }
    }


# Prometheus指标端点
@router.get("/metrics")
async def metrics():
    """Prometheus监控指标"""
    return generate_latest()


# 智能问答端点
@router.post("/query", response_model=QueryResponse)
@limiter.limit(f"{SECURITY_CONFIG['RATE_LIMIT']}/minute")
async def query_documents(
        request: Request,
        query_request: QueryRequest,
        token_payload: Dict = Depends(verify_token)
):
    """
    执行文档检索和智能问答,\n
    query：问题,\n
    collection_name：数据库集合名称,\n
    top_k：查询检索上下文的数量,\n
    chain_type: 链类型: \n
        "basic": 基础RAG索引链,\n
        "rerank": 后检索优化-模型重排序RAG链,\n
        "fusion": 后检索优化-RAG-Fusion,\n
        "multi_query": 查询优化-Multi-Query多路召回,\n
        "complex": 查询优化-Decomposition复杂问题分解,\n
        "compressor": 后检索优化-上下文压缩,\n
        "hybrid": 混合检索
    """
    start_time = time.time()

    try:
        # 获取RAG链
        rag_chain = get_rag_chain(
            collection_name=query_request.collection_name,
            top_k=query_request.top_k
        )

        # 执行查询（带超时控制）
        request_timeout = PERFORMANCE_CONFIG.get("REQUEST_TIMEOUT", 60)
        with QUERY_DURATION.labels(chain_type=query_request.chain_type).time():
            try:
                answer = await asyncio.wait_for(
                    rag_chain.async_invoke(
                        query_request.query,
                        query_request.chain_type
                    ),
                    timeout=request_timeout
                )
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=408, 
                    detail=f"请求超时（{request_timeout}秒），请稍后重试"
                )

        # 检索文档数量
        vector_store = get_vector_store_manager(query_request.collection_name)
        docs = vector_store.search_with_cache(query_request.query, query_request.top_k)

        processing_time = time.time() - start_time

        # 记录指标
        QUERY_COUNTER.labels(
            chain_type=query_request.chain_type,
            status="success"
        ).inc()

        return QueryResponse(
            answer=answer,
            retrieved_count=len(docs),
            collection_name=query_request.collection_name,
            processing_time=processing_time,
            chain_type=query_request.chain_type
        )

    except Exception as e:
        QUERY_COUNTER.labels(
            chain_type=query_request.chain_type,
            status="error"
        ).inc()
        logger.error(f"查询处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理查询时出错: {str(e)}")


# 文档上传端点
@router.post("/documents/upload", response_model=DocumentUploadResponse)
@limiter.limit("10/minute")
async def upload_document(
        request: Request,
        file: UploadFile = File(...),
        collection_name: str = Query("rag_collection"),
        chunk_size: int = Query(DOCUMENT_CONFIG["CHUNK_SIZE"]),
        chunk_overlap: int = Query(DOCUMENT_CONFIG["CHUNK_OVERLAP"]),
        use_ocr: bool = Query(False),
        token_payload: Dict = Depends(verify_token)
):
    """上传并处理文档文件"""
    try:
        # 验证文件类型
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in DOCUMENT_CONFIG["ALLOWED_EXTENSIONS"]:
            raise HTTPException(400, f"不支持的文件类型: {file_extension}")

        # 验证文件大小
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置文件指针

        if file_size > DOCUMENT_CONFIG["MAX_FILE_SIZE"]:
            raise HTTPException(400, f"文件大小超过限制: {file_size} > {DOCUMENT_CONFIG['MAX_FILE_SIZE']}")

        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)

        # 保存上传文件
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 处理文档 - 使用增强的加载器
        loader = EnhancedLoader(temp_file_path)
        documents = loader.load_document(use_ocr_for_pdf=use_ocr)

        # 文本分块
        text_splitter = get_text_splitter(chunk_size, chunk_overlap)
        chunks = text_splitter.split_documents(documents)

        # 添加到向量库
        vector_store = get_vector_store_manager(collection_name)
        document_ids = vector_store.add_documents(chunks)

        # 记录处理详情
        logger.log_document_processing(file.filename, len(documents), len(chunks))

        # 记录指标
        UPLOAD_COUNTER.labels(
            file_type=file_extension,
            status="success"
        ).inc()

        return DocumentUploadResponse(
            status="success",
            filename=file.filename,
            document_count=len(documents),
            chunk_count=len(chunks),
            document_ids=document_ids,
            collection_name=collection_name,
            processing_type="ocr" if use_ocr else "standard"
        )

    except Exception as e:
        UPLOAD_COUNTER.labels(
            file_type=file_extension,
            status="error"
        ).inc()
        logger.error(f"文件上传处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")
    finally:
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir)


# 获取可用链类型
@router.get("/chains")
async def get_available_chains(token_payload: Dict = Depends(verify_token)):
    """
    获取可用的RAG链类型,\n
    "basic": 基础RAG索引链,\n
    "rerank": 后检索优化-模型重排序RAG链,\n
    "fusion": 后检索优化-RAG-Fusion,\n
    "multi_query": 查询优化-Multi-Query多路召回,\n
    "complex": 查询优化-Decomposition复杂问题分解,\n
    "compressor": 后检索优化-上下文压缩,\n
    "hybrid": 混合检索
    """
    rag_chain = get_rag_chain()
    return {"available_chains": rag_chain.get_available_chains()}


# 清空缓存
@router.post("/cache/clear")
async def clear_cache(token_payload: Dict = Depends(verify_token)):
    """清空系统缓存"""
    try:
        rag_chain = get_rag_chain()
        rag_chain.clear_cache()

        model = EnhancedModel()
        model.clear_cache()

        return {"status": "success", "message": "缓存已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空缓存时出错: {str(e)}")


# 获取系统状态
@router.get("/status")
async def get_system_status(token_payload: Dict = Depends(verify_token)):
    """获取系统状态信息"""
    try:
        vector_store = get_vector_store_manager()
        stats = vector_store.get_collection_stats()

        return {
            "vector_db": stats,
            "cache_enabled": PERFORMANCE_CONFIG["CACHE_ENABLED"],
            "async_enabled": PERFORMANCE_CONFIG["ASYNC_ENABLED"],
            "rate_limit": SECURITY_CONFIG["RATE_LIMIT"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统状态时出错: {str(e)}")
