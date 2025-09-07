"""
增强的向量存储管理 - 支持Redis缓存和异步操作
"""
import uuid
import os
import json
import asyncio
import redis
# import aioredis  # 注释掉aioredis导入，使用同步redis
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from langchain_community.storage import RedisStore
from langchain_core.documents import Document
try:
    from modularizationV2.config.config import DB_CONFIG, REDIS_CONFIG, PERFORMANCE_CONFIG
    from modularizationV2.core.model import EnhancedModel
    from modularizationV2.logger.log import get_logger
except ImportError:
    # 如果无法导入，使用相对导入
    from ..config.config import DB_CONFIG, REDIS_CONFIG, PERFORMANCE_CONFIG
    from .model import EnhancedModel
    from ..logger.log import get_logger
logger = get_logger()
class AsyncVectorStoreManager:
    """异步向量存储管理器"""
    
    def __init__(self, embeddings=None, collection_name=DB_CONFIG["COLLECTION_NAME"],
                 host=DB_CONFIG["HOST"], port=DB_CONFIG["PORT"]):
        self.collection = collection_name
        self.client = QdrantClient(host=host, port=port, prefer_grpc=True)
        self.embeddings = embeddings or EnhancedModel().emb()

        # 创建集合（如果不存在）
        self._create_collection_if_not_exists()
        
        # 连接向量存储
        self.store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection,
            embedding=self.embeddings
        )
        
        # 初始化Redis连接（同步版本）
        self.redis_client = self._init_redis_async()
        self.redis_byte_store = RedisStore(
            redis_url=f"redis://{REDIS_CONFIG['HOST']}:{REDIS_CONFIG['PORT']}",
            namespace="multi_vector_rag"
        )

    def _create_collection_if_not_exists(self):
        """创建集合（如果不存在）"""
        try:
            self.client.get_collection(collection_name=self.collection)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
            logger.info(f"集合 {self.collection} 创建成功")

    def _init_redis_async(self):
        """初始化Redis连接（同步版本）"""
        try:
            return redis.Redis(
                host=REDIS_CONFIG["HOST"],
                port=REDIS_CONFIG["PORT"],
                db=REDIS_CONFIG["DB"],
                password=REDIS_CONFIG["PASSWORD"],
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return None

    async def _create_collection_if_not_exists_async(self):
        """异步创建集合（如果不存在）"""
        # 由于已经使用同步客户端，直接调用同步方法
        self._create_collection_if_not_exists()

    async def async_add_documents(self, documents: List[Document]) -> List[str]:
        """异步添加文档到向量存储"""
        ids = [str(uuid.uuid4()) for _ in documents]
        # 使用同步方法，因为QdrantVectorStore的异步方法可能不可用
        self.store.add_documents(documents=documents, ids=ids)
        return ids

    async def async_retrieve(self, query: str, k: int = 5) -> List[Document]:
        """异步检索相似文档"""
        # 使用同步方法，因为QdrantVectorStore的异步方法可能不可用
        return self.store.similarity_search(query, k=k)

    async def async_delete_documents(self, ids: List[str]):
        """异步删除文档"""
        # 使用同步方法，因为QdrantVectorStore的异步方法可能不可用
        return self.store.delete(ids)

class CachedVectorStoreManager:
    """带缓存的向量存储管理器"""
    
    def __init__(self, embeddings=None, collection_name=DB_CONFIG["COLLECTION_NAME"]):
        self.collection = collection_name
        self.embeddings = embeddings or EnhancedModel().emb()
        self.client = QdrantClient(host=DB_CONFIG["HOST"], port=DB_CONFIG["PORT"])
        self.redis_client = self._init_redis()
        
        self._create_collection_if_not_exists()
        
        self.store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection,
            embedding=self.embeddings
        )

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            return redis.Redis(
                host=REDIS_CONFIG["HOST"],
                port=REDIS_CONFIG["PORT"],
                db=REDIS_CONFIG["DB"],
                password=REDIS_CONFIG["PASSWORD"],
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return None

    def _create_collection_if_not_exists(self):
        """创建集合（如果不存在）"""
        try:
            self.client.get_collection(collection_name=self.collection)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

    def _get_cache_key(self, query: str, k: int) -> str:
        """生成缓存键"""
        return f"vector_search:{self.collection}:{query}:{k}"

    def search_with_cache(self, query: str, k: int = 5) -> List[Document]:
        """带缓存的向量搜索"""
        if not PERFORMANCE_CONFIG["CACHE_ENABLED"] or not self.redis_client:
            return self.store.similarity_search(query, k=k)
        
        cache_key = self._get_cache_key(query, k)
        
        # 检查缓存
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            logger.debug(f"向量搜索缓存命中: {query}")
            return [Document(**doc_data) for doc_data in json.loads(cached_result)]
        
        # 执行搜索
        results = self.store.similarity_search(query, k=k)
        
        # 缓存结果
        if results:
            cache_data = json.dumps([{"page_content": doc.page_content, "metadata": doc.metadata} 
                                   for doc in results])
            self.redis_client.setex(cache_key, REDIS_CONFIG["CACHE_TTL"], cache_data)
        
        return results

    def add_documents_with_cache(self, documents: List[Document]) -> List[str]:
        """添加文档并清除相关缓存"""
        ids = [str(uuid.uuid4()) for _ in documents]
        self.store.add_documents(documents=documents, ids=ids)
        
        # 清除相关缓存
        if self.redis_client:
            pattern = f"vector_search:{self.collection}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"清除 {len(keys)} 个向量搜索缓存")
        
        return ids

    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档到向量存储"""
        ids = [str(uuid.uuid4()) for _ in documents]
        self.store.add_documents(documents=documents, ids=ids)
        return ids

    def batch_search(self, queries: List[str], k: int = 5) -> List[List[Document]]:
        """批量向量搜索"""
        results = []
        for query in queries:
            results.append(self.search_with_cache(query, k=k))
        return results

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            collection_info = self.client.get_collection(collection_name=self.collection)
            return {
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "config": collection_info.config.dict()
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {}

# 全局实例
_vector_store_manager = None

def get_vector_store_manager(collection_name=None) -> CachedVectorStoreManager:
    """获取全局向量存储管理器实例"""
    global _vector_store_manager
    # 如果集合名称发生变化，重新创建实例
    if (_vector_store_manager is None or 
        _vector_store_manager.collection != collection_name):
        _vector_store_manager = CachedVectorStoreManager(collection_name=collection_name)
    return _vector_store_manager


def reset_vector_store_manager():
    """重置全局向量存储管理器实例，强制重新初始化"""
    global _vector_store_manager
    _vector_store_manager = None
    logger.info("向量存储管理器实例已重置")

def get_async_vector_store_manager() -> AsyncVectorStoreManager:
    """获取异步向量存储管理器实例"""
    return AsyncVectorStoreManager()