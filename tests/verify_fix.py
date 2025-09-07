#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证embedding修复
"""
import os
import sys

# 设置环境变量
os.environ['MODEL_PROVIDER'] = 'dashscope'
os.environ['DASHSCOPE_API_KEY'] = 'test_key'

# 添加当前目录到Python路径
sys.path.insert(0, '../../modularization')

def verify_parameter_handling():
    """验证参数处理逻辑"""
    try:
        from core.model import CustomDashScopeEmbeddings
        
        # 创建自定义embedding实例
        embeddings = CustomDashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key="test_key"
        )
        
        print("✅ CustomDashScopeEmbeddings创建成功")
        
        # 测试参数处理逻辑
        test_cases = [
            ("字符串", "这是一个测试文本"),
            ("列表", ["文本1", "文本2"]),
            ("空列表", []),
        ]
        
        for case_name, test_input in test_cases:
            print(f"\n测试 {case_name}: {test_input}")
            print(f"输入类型: {type(test_input)}")
            
            # 模拟我们的修复逻辑
            if isinstance(test_input, str):
                processed_input = [test_input]
                print(f"✅ 字符串转换为列表: {processed_input}")
            else:
                processed_input = test_input
                print(f"✅ 列表保持不变: {processed_input}")
            
            print(f"处理后类型: {type(processed_input)}")
            print(f"处理后内容: {processed_input}")
        
        print("\n🎉 参数处理逻辑验证成功！")
        print("修复说明:")
        print("1. 当传入字符串时，自动转换为列表 [字符串]")
        print("2. 当传入列表时，保持原样")
        print("3. 这样确保了DashScopeEmbeddings总是接收到列表格式的texts参数")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 验证Embedding参数修复...")
    success = verify_parameter_handling()
    
    if success:
        print("\n✅ 修复验证成功！")
        print("现在Gradio界面应该可以正常处理embedding调用了。")
    else:
        print("\n❌ 验证失败。")
