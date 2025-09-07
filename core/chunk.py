"""
这个模块负责将文档分割成小块
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
from langchain_core.documents import Document


def get_text_splitter(chunk_size: int = 500, chunk_overlap: int = 50) -> RecursiveCharacterTextSplitter:
    """
    获取配置好的文本分割器
    
    Args:
        chunk_size: 分块大小
        chunk_overlap: 重叠大小
        
    Returns:
        RecursiveCharacterTextSplitter: 文本分割器实例
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )


def split_documents(documents: List[Document], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """
    分割文档为文本块
    
    Args:
        documents: 文档列表
        chunk_size: 分块大小
        chunk_overlap: 重叠大小
        
    Returns:
        List[Document]: 分割后的文档块列表
    """
    splitter = get_text_splitter(chunk_size, chunk_overlap)
    return splitter.split_documents(documents)
