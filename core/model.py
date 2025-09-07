"""
模型封装 - 支持缓存和异步处理
"""
import os
import asyncio
import time
from functools import lru_cache, wraps
from typing import Optional, Callable, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_compressors.dashscope_rerank import DashScopeRerank
from langchain_core.embeddings import Embeddings
from typing import List
try:
    from modularizationV2.config.config import MODEL_CONFIG, DEFAULT_MODELS, PERFORMANCE_CONFIG
    from modularizationV2.logger.log import get_logger
except ImportError:
    # 如果无法导入，使用相对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.config import MODEL_CONFIG, DEFAULT_MODELS, PERFORMANCE_CONFIG
    from logger.log import get_logger

logger = get_logger()

class CustomDashScopeEmbeddings(Embeddings):
    """自定义DashScopeEmbeddings包装器，修复input.texts参数问题"""
    
    def __init__(self, model: str, dashscope_api_key: str):
        self.model = model
        self.dashscope_api_key = dashscope_api_key
        self._embeddings = DashScopeEmbeddings(
            model=model,
            dashscope_api_key=dashscope_api_key
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        # 确保texts是列表格式
        if isinstance(texts, str):
            texts = [texts]
        return self._embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        # 处理非字符串类型（如HumanMessage对象）
        if not isinstance(text, str):
            try:
                # 尝试从消息对象中提取文本内容
                if hasattr(text, 'content'):
                    text = text.content
                elif hasattr(text, 'text'):
                    text = text.text
                else:
                    text = str(text)
            except Exception:
                text = str(text)
        return self._embeddings.embed_query(text)
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步嵌入文档列表"""
        # 确保texts是列表格式
        if isinstance(texts, str):
            texts = [texts]
        return await self._embeddings.aembed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """异步嵌入单个查询"""
        return await self._embeddings.aembed_query(text)

class ModelCache:
    """模型响应缓存"""
    
    def __init__(self, max_size=1000, ttl=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            cached_time, value = self.cache[key]
            if time.time() - cached_time < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            # LRU淘汰策略
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
        self.cache[key] = (time.time(), value)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()

def async_timeout(timeout: int):
    """异步超时装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Function {func.__name__} timed out after {timeout}s")
                raise
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {str(e)}")
                raise
        return wrapper
    return decorator

def cache_response(ttl: int = 300):
    """缓存响应装饰器"""
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not PERFORMANCE_CONFIG["CACHE_ENABLED"]:
                return await func(*args, **kwargs)
                
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 检查缓存
            cached_result = cache.get(cache_key)
            if cached_result and time.time() - cached_result['timestamp'] < ttl:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result['result']
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache[cache_key] = {
                'timestamp': time.time(),
                'result': result
            }
            
            return result
        return wrapper
    return decorator

class EnhancedModel:
    def __init__(self, provider=DEFAULT_MODELS["PROVIDER"]):
        self.provider = provider
        self.config = MODEL_CONFIG[provider]
        self.cache = ModelCache()

        # 设置默认模型
        self.model = DEFAULT_MODELS["CHAT"]
        self.model_emb = DEFAULT_MODELS["EMBEDDING"]
        self.model_rerank = DEFAULT_MODELS["RERANK"]

    @lru_cache(maxsize=100)
    def model_llm(self, model_name=None, temperature=0.5, max_tokens=10000):
        """定义大模型 - 支持缓存"""
        model_to_use = model_name if model_name else self.model
        
        return ChatOpenAI(
            model=model_to_use,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=self.config["BASE_URL"],
            api_key=self.config["API_KEY"],
            verbose=False
        )

    @lru_cache(maxsize=50)
    def emb(self, model_name=None):
        """定义embedding模型 - 支持缓存"""
        model_to_use = model_name if model_name else self.model_emb
        
        if self.provider == "openai":
            return OpenAIEmbeddings(
                model=model_to_use,
                openai_api_key=self.config["API_KEY"],
                openai_api_base=self.config["BASE_URL"]
            )
        else:
            # 创建自定义的DashScopeEmbeddings包装器
            return CustomDashScopeEmbeddings(
                model=model_to_use,
                dashscope_api_key=self.config["API_KEY"]
            )

    @lru_cache(maxsize=20)
    def get_lc_ali_rerank(self, model_name=None, top_n=3):
        """重排序模型 - 支持缓存"""
        model_to_use = model_name if model_name else self.model_rerank
        
        return DashScopeRerank(
            model=model_to_use,
            dashscope_api_key=self.config["API_KEY"],
            top_n=top_n
        )

    @async_timeout(60)
    @cache_response(ttl=300)
    async def async_generate(self, prompt: str, **kwargs):
        """异步生成文本"""
        llm = self.model_llm()
        return await llm.agenerate(prompt, **kwargs)

    @async_timeout(60)
    @cache_response(ttl=3600)
    async def async_embed(self, texts: list, **kwargs):
        """异步生成嵌入向量"""
        embeddings = self.emb()
        return await embeddings.aembed_documents(texts, **kwargs)

    @async_timeout(60)
    async def async_batch_generate(self, prompts: list, batch_size=10, **kwargs):
        """批量异步生成文本"""
        llm = self.model_llm()
        results = []
        
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[llm.agenerate(prompt, **kwargs) for prompt in batch]
            )
            results.extend(batch_results)
        
        return results

    def clear_cache(self):
        """清空所有缓存"""
        self.cache.clear()
        self.model_llm.cache_clear()
        self.emb.cache_clear()
        self.get_lc_ali_rerank.cache_clear()
        logger.info("Model cache cleared")

# 全局模型实例
_model_instance = None

def get_model() -> EnhancedModel:
    """获取全局模型实例"""
    global _model_instance
    if _model_instance is None:
        _model_instance = EnhancedModel()
    return _model_instance