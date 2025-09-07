#!/usr/bin/env python3
"""
Loader集成测试脚本
测试文档加载、分块、向量存储的完整流程
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from modularizationV2.loader.load import EnhancedLoader, load_documents_from_folder
from modularizationV2.core.chunk import get_text_splitter, split_documents
from modularizationV2.core.vector_store import get_vector_store_manager
from modularizationV2.logger.log import get_logger

logger = get_logger()

def test_loader_integration():
    """测试完整的文档处理流程"""
    print("🚀 开始Loader集成测试...")
    
    # 创建测试数据目录
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    # 创建测试文件
    test_files = [
        ("test.txt", "这是一个测试文本文件。\n包含多行内容用于测试文档加载功能。"),
        ("test_doc.txt", "另一个测试文档，用于验证多文件加载。")
    ]
    
    for filename, content in test_files:
        file_path = test_data_dir / filename
        file_path.write_text(content, encoding="utf-8")
        print(f"📄 创建测试文件: {file_path}")
    
    try:
        # 测试1: 单个文件加载
        print("\n1. 测试单个文件加载...")
        loader = EnhancedLoader(str(test_data_dir / "test.txt"))
        documents = loader.load_document()
        print(f"✅ 加载成功: {len(documents)}个文档")
        for doc in documents:
            print(f"   - 内容预览: {doc.page_content[:50]}...")
        
        # 测试2: 文件夹批量加载
        print("\n2. 测试文件夹批量加载...")
        all_docs = load_documents_from_folder(str(test_data_dir))
        print(f"✅ 批量加载成功: {len(all_docs)}个文档")
        
        # 测试3: 文本分块
        print("\n3. 测试文本分块...")
        text_splitter = get_text_splitter(chunk_size=50, chunk_overlap=10)
        chunks = text_splitter.split_documents(all_docs)
        print(f"✅ 分块成功: {len(chunks)}个文本块")
        for i, chunk in enumerate(chunks[:3]):
            print(f"   - 块{i+1}: {chunk.page_content[:30]}...")
        
        # 测试4: 向量存储集成
        print("\n4. 测试向量存储集成...")
        vector_store = get_vector_store_manager("test_collection")
        document_ids = vector_store.add_documents(chunks)
        print(f"✅ 向量存储成功: {len(document_ids)}个文档ID")
        
        # 测试5: 检索验证
        print("\n5. 测试检索功能...")
        results = vector_store.search_with_cache("测试", k=3)
        print(f"✅ 检索成功: {len(results)}个相关文档")
        for i, result in enumerate(results):
            print(f"   - 结果{i+1}: {result.page_content[:30]}...")
        
        print("\n🎉 所有测试通过！Loader集成正常工作。")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理测试文件
        for file in test_data_dir.glob("*"):
            file.unlink()
        test_data_dir.rmdir()
        print("🧹 清理测试文件完成")
    
    return True

if __name__ == "__main__":
    success = test_loader_integration()
    sys.exit(0 if success else 1)