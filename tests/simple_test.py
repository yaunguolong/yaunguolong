#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试embedding修复
"""
import os
import sys

# 设置环境变量
os.environ['MODEL_PROVIDER'] = 'dashscope'
os.environ['DASHSCOPE_API_KEY'] = 'test_key'

# 添加当前目录到Python路径
sys.path.insert(0, '../../modularization')

def test_custom_embeddings():
    """测试自定义embedding类"""
    try:
        from core.model import CustomDashScopeEmbeddings
        
        # 创建自定义embedding实例
        embeddings = CustomDashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key="test_key"
        )
        
        print("✅ CustomDashScopeEmbeddings创建成功")
        
        # 测试embed_documents方法（这是修复的关键）
        test_text = "这是一个测试文本"
        print(f"测试文本: {test_text}")
        print(f"文本类型: {type(test_text)}")
        
        # 这里应该不会报错，因为我们的包装器会处理字符串
        try:
            result = embeddings.embed_documents(test_text)
            print(f"✅ embed_documents(字符串)成功，结果类型: {type(result)}")
        except Exception as e:
            print(f"❌ embed_documents(字符串)失败: {e}")
        
        # 测试正常的列表调用
        try:
            result = embeddings.embed_documents([test_text])
            print(f"✅ embed_documents(列表)成功，结果类型: {type(result)}")
        except Exception as e:
            print(f"❌ embed_documents(列表)失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 测试自定义Embedding修复...")
    test_custom_embeddings()
