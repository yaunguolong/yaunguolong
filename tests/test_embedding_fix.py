#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试embedding修复
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_embedding_import():
    """测试embedding导入"""
    try:
        from modularizationV2.core.model import EnhancedModel, CustomDashScopeEmbeddings
        print("✅ 模型模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模型模块导入失败: {e}")
        return False

def test_embedding_creation():
    """测试embedding创建"""
    try:
        from modularizationV2.core.model import EnhancedModel
        
        # 创建模型实例
        model = EnhancedModel()
        print("✅ 模型实例创建成功")
        
        # 创建embedding实例
        embeddings = model.emb()
        print(f"✅ Embedding实例创建成功: {type(embeddings)}")
        
        return True
    except Exception as e:
        print(f"❌ Embedding创建失败: {e}")
        return False

def test_embedding_single_text():
    """测试单个文本embedding"""
    try:
        from modularizationV2.core.model import EnhancedModel
        
        model = EnhancedModel()
        embeddings = model.emb()
        
        # 测试单个文本
        test_text = "这是一个测试文本"
        result = embeddings.embed_query(test_text)
        
        print(f"✅ 单个文本embedding成功，向量维度: {len(result)}")
        return True
    except Exception as e:
        print(f"❌ 单个文本embedding失败: {e}")
        return False

def test_embedding_documents():
    """测试文档列表embedding"""
    try:
        from modularizationV2.core.model import EnhancedModel
        
        model = EnhancedModel()
        embeddings = model.emb()
        
        # 测试文档列表
        test_texts = ["这是第一个文档", "这是第二个文档", "这是第三个文档"]
        result = embeddings.embed_documents(test_texts)
        
        print(f"✅ 文档列表embedding成功，文档数量: {len(result)}")
        return True
    except Exception as e:
        print(f"❌ 文档列表embedding失败: {e}")
        return False

def test_embedding_string_as_list():
    """测试字符串作为列表处理"""
    try:
        from modularizationV2.core.model import EnhancedModel
        
        model = EnhancedModel()
        embeddings = model.emb()
        
        # 测试字符串作为列表（这是问题所在）
        test_text = "这是一个测试文本"
        result = embeddings.embed_documents(test_text)  # 传递字符串而不是列表
        
        print(f"✅ 字符串作为列表embedding成功，结果数量: {len(result)}")
        return True
    except Exception as e:
        print(f"❌ 字符串作为列表embedding失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始测试Embedding修复...")
    print("=" * 50)
    
    # 测试导入
    import_ok = test_embedding_import()
    
    if not import_ok:
        print("❌ 导入失败，无法继续测试")
        return
    
    # 测试创建
    creation_ok = test_embedding_creation()
    
    if not creation_ok:
        print("❌ 创建失败，无法继续测试")
        return
    
    # 测试各种embedding场景
    single_ok = test_embedding_single_text()
    docs_ok = test_embedding_documents()
    string_as_list_ok = test_embedding_string_as_list()
    
    print("=" * 50)
    print("📊 测试结果:")
    print(f"  导入测试: {'✅' if import_ok else '❌'}")
    print(f"  创建测试: {'✅' if creation_ok else '❌'}")
    print(f"  单个文本: {'✅' if single_ok else '❌'}")
    print(f"  文档列表: {'✅' if docs_ok else '❌'}")
    print(f"  字符串列表: {'✅' if string_as_list_ok else '❌'}")
    
    if all([import_ok, creation_ok, single_ok, docs_ok, string_as_list_ok]):
        print("\n🎉 所有测试通过！Embedding修复成功。")
    else:
        print("\n⚠️  部分测试失败，请检查修复。")

if __name__ == "__main__":
    main()
