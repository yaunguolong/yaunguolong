"""
增强的文档加载器 - 支持多种格式和OCR处理
"""
from typing import List, Optional, Union
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, WebBaseLoader, Docx2txtLoader, PyMuPDFLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
import pdfplumber
import fitz  # PyMuPDF
import bs4
import os
from pathlib import Path
from modularizationV2.logger.log import get_logger
from modularizationV2.config.config import DOCUMENT_CONFIG

logger = get_logger()

class EnhancedLoader:
    """
    增强的文档加载器类，支持多种文档格式和OCR处理
    
    支持格式:
    - TXT: 文本文件
    - PDF: PDF文档（支持OCR）
    - DOCX: Word文档  
    - Web: 网页内容
    """
    
    def __init__(self, file_path: str):
        """
        初始化文档加载器

        Args:
            file_path (str): 文件路径或网页URL
        """
        self.file_path = file_path
        self.file_extension = os.path.splitext(file_path)[1].lower() if file_path else ''

    def load_document(self, use_ocr_for_pdf: bool = False,
                      content_classes: Optional[List[str]] = None,
                      title_classes: Optional[List[str]] = None) -> List[Document]:
        """
        统一加载文档函数，根据文件类型自动选择加载方式

        Args:
            use_ocr_for_pdf (bool): 是否对PDF使用OCR识别
            content_classes: 网页正文CSS类名列表
            title_classes: 网页标题CSS类名列表

        Returns:
            List[Document]: 加载的文档列表
        """
        # 验证文件类型
        if self.file_extension not in DOCUMENT_CONFIG["ALLOWED_EXTENSIONS"] and not self.file_path.startswith('http'):
            raise ValueError(f"不支持的文件类型: {self.file_extension}")

        # 判断是否为网页URL
        if self.file_path.startswith('http'):
            return self._load_web_document(content_classes, title_classes)

        # 根据文件扩展名选择加载方式
        if self.file_extension == '.docx':
            return self._load_docx_document()
        elif self.file_extension == '.txt':
            return self._load_txt_document()
        elif self.file_extension == '.pdf':
            if use_ocr_for_pdf:
                return self._load_pdf_with_ocr()
            else:
                return self._load_pymu_pdf()
        else:
            # 默认尝试使用文本加载器
            return self._load_txt_document()

    def _load_docx_document(self) -> List[Document]:
        """加载DOCX文档"""
        try:
            doc_loader = Docx2txtLoader(self.file_path)
            docs = doc_loader.load()
            logger.info(f"成功加载DOCX文档: {self.file_path}, 页数: {len(docs)}")
            return docs
        except Exception as e:
            logger.error(f"加载DOCX文档失败: {str(e)}")
            raise

    def _load_txt_document(self) -> List[Document]:
        """加载TXT文档"""
        try:
            txt_loader = TextLoader(self.file_path)
            docs = txt_loader.load()
            logger.info(f"成功加载TXT文档: {self.file_path}, 内容长度: {len(docs[0].page_content) if docs else 0}")
            return docs
        except Exception as e:
            logger.error(f"加载TXT文档失败: {str(e)}")
            raise

    def _load_pdf_with_ocr(self) -> List[Document]:
        """
        优先使用 pdfplumber 结构化提取文本与表格，如失败再用 Tesseract OCR
        """
        documents = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables()

                    # 拼接表格为结构化字符串
                    table_strs = []
                    for table in tables:
                        table_str = "\n".join(
                            ["\t".join(str(cell) for cell in row) for row in table if row]
                        )
                        table_strs.append(table_str)

                    content = text + "\n\n" + "\n\n".join(table_strs)
                    if content.strip():
                        documents.append(Document(
                            page_content=content.strip(),
                            metadata={"source": self.file_path, "page": i + 1, "type": "pdf_plumber"}
                        ))
            
            logger.info(f"成功使用pdfplumber加载PDF文档: {self.file_path}, 页数: {len(documents)}")
            
        except Exception as e:
            logger.warning(f"pdfplumber加载失败: {str(e)}，尝试使用PyMuPDF")
            documents = self._load_pymu_pdf()
        
        return documents

    def _load_pymu_pdf(self) -> List[Document]:
        """使用PyMuPDF加载PDF文档"""
        try:
            doc = fitz.open(self.file_path)
            documents = []

            # 遍历每一页
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    documents.append(Document(
                        page_content=text.strip(),
                        metadata={"page": page_num + 1, "source": self.file_path, "type": "pymupdf"}
                    ))

            logger.info(f"成功使用PyMuPDF加载PDF文档: {self.file_path}, 页数: {len(documents)}")
            return documents
            
        except Exception as e:
            logger.error(f"PyMuPDF加载失败: {str(e)}")
            raise

    def _load_web_document(self, content_classes: Optional[List[str]] = None,
                           title_classes: Optional[List[str]] = None) -> List[Document]:
        """加载网页内容"""
        try:
            # 默认CSS类名
            default_content_classes = ["post-content", "post-title", "post-header", "content", "main"]

            # 合并传入的类名和默认类名
            if content_classes or title_classes:
                classes = (content_classes or []) + (title_classes or [])
            else:
                classes = default_content_classes

            loader = WebBaseLoader(
                web_paths=[self.file_path],
                bs_kwargs=dict(parse_only=bs4.SoupStrainer(
                    class_=tuple(classes)
                ))
            )
            docs = loader.load()
            logger.info(f"成功加载网页内容: {self.file_path}, 内容长度: {len(docs[0].page_content) if docs else 0}")
            return docs
            
        except Exception as e:
            logger.error(f"网页内容加载失败: {str(e)}")
            raise

def load_documents_from_folder(folder_path: str = "docs", 
                              use_ocr_for_pdf: bool = False) -> List[Document]:
    """
    从文件夹加载所有支持的文档
    
    Args:
        folder_path: 文件夹路径
        use_ocr_for_pdf: 是否对PDF使用OCR
        
    Returns:
        List[Document]: 所有文档列表
    """
    all_docs = []
    folder = Path(folder_path)
    
    if not folder.exists():
        logger.warning(f"文件夹不存在: {folder_path}")
        return all_docs
    
    # 支持的文件格式
    supported_extensions = DOCUMENT_CONFIG["ALLOWED_EXTENSIONS"]
    
    for ext in supported_extensions:
        for file in folder.glob(f"*{ext}"):
            try:
                loader = EnhancedLoader(str(file))
                docs = loader.load_document(use_ocr_for_pdf=use_ocr_for_pdf)
                all_docs.extend(docs)
                logger.info(f"成功加载文件: {file.name}, 文档数: {len(docs)}")
            except Exception as e:
                logger.error(f"加载文件失败: {file.name}, 错误: {str(e)}")
    
    return all_docs

def load_documents_from_file(file_path: str, use_ocr_for_pdf: bool = False) -> List[Document]:
    """
    加载单个文件文档
    
    Args:
        file_path: 文件路径
        use_ocr_for_pdf: 是否对PDF使用OCR
        
    Returns:
        List[Document]: 文档列表
    """
    try:
        loader = EnhancedLoader(file_path)
        return loader.load_document(use_ocr_for_pdf=use_ocr_for_pdf)
    except Exception as e:
        logger.error(f"加载文件失败: {file_path}, 错误: {str(e)}")
        raise

# 向后兼容的函数
def load_documents(folder_path: str = "docs") -> List[Document]:
    """向后兼容的加载函数"""
    return load_documents_from_folder(folder_path)