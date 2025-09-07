#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟测试embedding修复
"""
import os
import sys
from unittest.mock import Mock, patch

# 设置环境变量
os.environ['MODEL_PROVIDER'] = 'dashscope'
os.environ['DASHSCOPE_API_KEY'] = 'test_key'

# 添加当前目录到Python路径
sys.path.insert(0, '../../modularization')

def test_embedding_parameter_fix():
    """测试embedding参数修复"""
    try:
        from core.model import CustomDashScopeEmbeddings
        
        # 创建自定义embedding实例
        embeddings = CustomDashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key="test_key"
        )
        
        print("✅ CustomDashScopeEmbeddings创建成功")
        
        # 模拟DashScopeEmbeddings的调用
        with patch.object(embeddings._embeddings, 'embed_documents') as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3]]  # 模拟返回结果
            
            # 测试1: 传递字符串（这是问题场景）
            test_text = "这是一个测试文本"
            result = embeddings.embed_documents(test_text)
            
            # 验证mock被调用时传递的是列表
            mock_embed.assert_called_with([test_text])
            print(f"✅ 字符串参数修复成功: {result}")
            
            # 重置mock
            mock_embed.reset_mock()
            
            # 测试2: 传递列表（正常场景）
            test_texts = ["文本1", "文本2"]
            result = embeddings.embed_documents(test_texts)
            
            # 验证mock被调用时传递的是原列表
            mock_embed.assert_called_with(test_texts)
            print(f"✅ 列表参数正常: {result}")
            
            # 重置mock
            mock_embed.reset_mock()
            
            # 测试3: 异步方法
            with patch.object(embeddings._embeddings, 'aembed_documents') as mock_aembed:
                mock_aembed.return_value = [[0.1, 0.2, 0.3]]
                
                import asyncio
                async def test_async():
                    result = await embeddings.aembed_documents(test_text)
                    return result
                
                result = asyncio.run(test_async())
                mock_aembed.assert_called_with([test_text])
                print(f"✅ 异步字符串参数修复成功: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 测试Embedding参数修复...")
    success = test_embedding_parameter_fix()
    
    if success:
        print("\n🎉 所有测试通过！Embedding参数修复成功。")
        print("现在可以处理字符串和列表两种参数格式了。")
    else:
        print("\n❌ 测试失败，需要进一步检查。")
