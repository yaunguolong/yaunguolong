"""
增强的RAG链模块 - 支持多种检索策略和异步处理
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from functools import lru_cache
from langchain.load import dumps, loads
from langchain_core.runnables import RunnablePassthrough, RunnableMap, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers.multi_query import LineListOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import (
    LLMChainFilter, LLMChainExtractor, DocumentCompressorPipeline, EmbeddingsFilter
)
from langchain_community.document_transformers import EmbeddingsRedundantFilter

try:
    from modularizationV2.core.vector_store import get_vector_store_manager, get_async_vector_store_manager
    from modularizationV2.core.base_prompt import PROMPTS, get_rag_prompt
    from modularizationV2.core.model import EnhancedModel
    from modularizationV2.config.config import PERFORMANCE_CONFIG
    from modularizationV2.logger.log import get_logger
except ImportError:
    # 如果无法导入，使用相对导入
    from .vector_store import get_vector_store_manager, get_async_vector_store_manager
    from .base_prompt import PROMPTS, get_rag_prompt
    from .model import EnhancedModel
    from ..config.config import PERFORMANCE_CONFIG
    from ..logger.log import get_logger

logger = get_logger()


class EnhancedRAGChain:
    """增强的RAG链，支持多种检索策略和缓存"""

    def __init__(self, collection_name=None, top_k=5, llm=None):
        self.top_k = top_k
        self.collection_name = collection_name
        self.llm = llm or EnhancedModel().model_llm()
        self.embeddings = EnhancedModel().emb()
        self.prompts = get_rag_prompt()
        self.vector_store = get_vector_store_manager(collection_name=self.collection_name)
        self.async_vector_store = get_async_vector_store_manager()
        self.retriever = self.vector_store.search_with_cache

        # 缓存链实例
        self._chain_cache = {}
        self._last_cache_clean = time.time()

    def _clean_chain_cache(self):
        """清理链缓存"""
        current_time = time.time()
        if current_time - self._last_cache_clean > 300:  # 每5分钟清理一次
            self._chain_cache = {k: v for k, v in self._chain_cache.items()
                                 if current_time - v['timestamp'] < 600}
            self._last_cache_clean = current_time

    def get_chain(self, chain_type: str = "basic"):
        """获取指定类型的链（带缓存）"""
        self._clean_chain_cache()

        cache_key = f"{chain_type}:{self.top_k}"
        if cache_key in self._chain_cache:
            return self._chain_cache[cache_key]['chain']

        chain = self._build_chain(chain_type)
        self._chain_cache[cache_key] = {
            'chain': chain,
            'timestamp': time.time()
        }

        return chain

    def _build_chain(self, chain_type: str):
        """构建指定类型的链"""
        chain_builders = {
            "basic": self._build_basic_chain,
            "rerank": self._build_rerank_chain,
            "fusion": self._build_fusion_chain,
            "multi_query": self._build_multi_query_chain,
            "complex": self._build_complex_chain,
            "compressor": self._build_compressor_chain,
            "hybrid": self._build_hybrid_chain,
        }

        builder = chain_builders.get(chain_type, self._build_basic_chain)
        return builder()

    def _build_basic_chain(self):
        """构建基础RAG链"""

        def format_docs(docs):
            return "\n\n".join([doc.page_content for doc in docs])

        return (
                RunnableMap({
                    "context": RunnableLambda(lambda x: self.retriever(x, self.top_k)) | RunnableLambda(format_docs),
                    "question": RunnablePassthrough()
                })
                | self.prompts
                | self.llm
                | StrOutputParser()
        )

    def _build_rerank_chain(self):
        """构建重排序RAG链"""

        def rerank_docs(input_data):
            documents = input_data["documents"]
            query = input_data["query"]
            if not documents:
                return []

            reranker = EnhancedModel().get_lc_ali_rerank()
            try:
                compressed_docs = reranker.compress_documents(documents, query)
                return compressed_docs
            except Exception as e:
                logger.warning(f"重排序出错: {e}")
                return documents[:3]

        def format_docs(docs):
            return "\n\n".join([doc.page_content for doc in docs])

        return (
                RunnableMap({
                    "documents": RunnableLambda(lambda x: self.retriever(x, self.top_k)),
                    "query": RunnablePassthrough()
                })
                | RunnableMap({
            "context": RunnableLambda(rerank_docs) | RunnableLambda(format_docs),
            "question": lambda x: x["query"],
        })
                | self.prompts
                | self.llm
                | StrOutputParser()
        )

    def _build_fusion_chain(self):
        """构建RAG-Fusion链"""
        from langchain.load import dumps, loads

        query_generation_chain = (
                {"question": RunnablePassthrough()}
                | PROMPTS["DEFAULT_PROMPTS"]["rag_fusion"]
                | self.llm
                | StrOutputParser()
                | (lambda x: x.split("\n"))
        )

        def reciprocal_rank_fusion(results: List[List]) -> List:
            """
            互逆排序融合算法实现
            算法原理：合并多个排序结果，为每个文档计算融合分数：
            分数 = Σ(1/(rank + k))，其中rank是文档在单个列表中的排名
             Args:
             results: 二维列表，包含多个查询的检索结果（每个元素是文档列表）
             Returns:
             按融合分数降序排列的元组列表：(文档对象, 融合分数)
             """
            k = 60
            fused_scores = {}

            for docs in results:
                for rank, doc in enumerate(docs):
                    doc_str = dumps(doc)
                    if doc_str not in fused_scores:
                        fused_scores[doc_str] = 0.0
                    fused_scores[doc_str] += 1 / (rank + k)

            return [loads(doc) for doc, _ in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)]

        def format_docs(docs):
            """格式化文档"""
            return "\n\n".join([doc.page_content for doc in docs])

        def process_queries(queries):
            """处理多个查询并融合结果"""
            results = []
            for query in queries:
                docs = self.retriever(query, self.top_k)
                results.append(docs)
            return reciprocal_rank_fusion(results)

        return (
                RunnableMap({
                    "docs": query_generation_chain | RunnableLambda(process_queries),
                    "question": RunnablePassthrough()
                })
                | RunnableMap({
            "context": lambda x: format_docs(x["docs"]),
            "question": lambda x: x["question"]
        })
                | self.prompts
                | self.llm
                | StrOutputParser()
        )

    def _build_multi_query_chain(self):
        """构建多查询链"""
        question_generator = (
                {"question": RunnablePassthrough()}
                | PROMPTS["DEFAULT_PROMPTS"]["multi"]
                | self.llm
                | StrOutputParser()
                | (lambda x: x.split("\n"))
        )

        def get_unique_union(documents: List[List]):
            flattened_docs = [dumps(doc) for sublist in documents for doc in sublist]
            unique_docs = list(set(flattened_docs))
            return [loads(doc) for doc in unique_docs]

        def process_queries(queries):
            results = []
            for query in queries:
                docs = self.retriever(query, self.top_k)
                results.append(docs)
            return get_unique_union(results)

        retriever_set_chain = (
                question_generator
                | RunnableLambda(process_queries)
        )

        return (
                {"question": RunnablePassthrough(), "context": retriever_set_chain}
                | self.prompts
                | self.llm
                | StrOutputParser()
        )

    def _build_complex_chain(self):
        """构建复杂问题链"""

        def decompose_question(question: str) -> List[str]:
            chain = PROMPTS["DEFAULT_PROMPTS"]["decomposition"] | self.llm | LineListOutputParser()
            return chain.invoke({"question": question})

        def get_sub_question_answers(questions: List[str]) -> List[str]:
            answers = []
            for sub_q in questions:
                docs = self.retriever(sub_q, self.top_k)
                doc_contents = [doc.page_content for doc in docs]

                chain = PROMPTS["DEFAULT_PROMPTS"]["sub_question"] | self.llm | StrOutputParser()
                response = chain.invoke({
                    "sub_question": sub_q,
                    "documents": "\n".join(doc_contents)
                })
                answers.append(f"子问题: {sub_q}\n答案: {response}")
            return answers

        def format_sub_answers(inputs: Dict[str, Any]) -> Dict[str, str]:
            question = inputs["question"]
            sub_questions = decompose_question(question)
            sub_answers = get_sub_question_answers(sub_questions)

            return {
                "context": "\n\n".join(sub_answers),
                "question": question
            }

        return (
                RunnableLambda(format_sub_answers)
                | PROMPTS["DEFAULT_PROMPTS"]["final_answer"]
                | self.llm
                | StrOutputParser()
        )

    def _build_compressor_chain(self):
        """构建压缩器链"""
        splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=0, separator=". ")
        redundant_filter = EmbeddingsRedundantFilter(embeddings=self.embeddings)
        embedding_filter = EmbeddingsFilter(embeddings=self.embeddings, similarity_threshold=0.6)

        pipeline = DocumentCompressorPipeline(
            transformers=[splitter, redundant_filter, embedding_filter]
        )

        # 创建一个简单的检索器类
        class SimpleRetriever:
            def __init__(self, retriever_func, top_k):
                self.retriever_func = retriever_func
                self.top_k = top_k

            def get_relevant_documents(self, query):
                return self.retriever_func(query, self.top_k)

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=pipeline,
            base_retriever=SimpleRetriever(self.retriever, self.top_k)
        )

        def compressor_docs_format(docs: list):
            return "\n\n".join([f"Document {i + 1}:\n\n{d.page_content}" for i, d in enumerate(docs)])

        return (
                RunnableMap({
                    "context": RunnableLambda(
                        lambda x: compression_retriever.get_relevant_documents(x)) | RunnableLambda(
                        compressor_docs_format),
                    "question": RunnablePassthrough()
                })
                | self.prompts
                | self.llm
                | StrOutputParser()
        )

    def _build_hybrid_chain(self):
        """构建混合检索链"""
        # 简化实现，实际项目中需要集成BM25等
        return self._build_basic_chain()

    async def async_invoke(self, query: str, chain_type: str = "basic") -> str:
        """异步调用RAG链"""
        chain = self.get_chain(chain_type)

        if PERFORMANCE_CONFIG["ASYNC_ENABLED"]:
            # 使用异步执行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, chain.invoke, query)
        else:
            return chain.invoke(query)

    def batch_invoke(self, queries: List[str], chain_type: str = "basic") -> List[str]:
        """批量调用RAG链"""
        chain = self.get_chain(chain_type)
        return chain.batch(queries)

    async def async_batch_invoke(self, queries: List[str], chain_type: str = "basic") -> List[str]:
        """异步批量调用RAG链"""
        chain = self.get_chain(chain_type)

        if PERFORMANCE_CONFIG["ASYNC_ENABLED"]:
            # 使用异步批量执行
            tasks = [self.async_invoke(query, chain_type) for query in queries]
            return await asyncio.gather(*tasks)
        else:
            return chain.batch(queries)

    def get_available_chains(self) -> List[str]:
        """获取可用的链类型"""
        return ["basic", "rerank", "fusion", "multi_query", "complex", "compressor", "hybrid"]

    def clear_cache(self):
        """清空链缓存"""
        self._chain_cache = {}
        logger.info("RAG链缓存已清空")


# 全局实例
_rag_chain_instance = None


def get_rag_chain(collection_name=None, top_k=5, llm=None) -> EnhancedRAGChain:
    """获取全局RAG链实例"""
    global _rag_chain_instance
    # 如果参数发生变化，重新创建实例
    if (_rag_chain_instance is None or 
        _rag_chain_instance.collection_name != collection_name or 
        _rag_chain_instance.top_k != top_k):
        _rag_chain_instance = EnhancedRAGChain(collection_name, top_k, llm)
    return _rag_chain_instance


def reset_rag_chain():
    """重置全局RAG链实例，强制重新初始化"""
    global _rag_chain_instance
    _rag_chain_instance = None
    logger.info("RAG链实例已重置")
