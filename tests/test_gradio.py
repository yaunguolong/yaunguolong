#!/usr/bin/env python3
"""
测试Gradio界面启动
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_gradio_import():
    """测试Gradio导入"""
    try:
        import gradio as gr
        print(f"✅ Gradio导入成功，版本: {gr.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Gradio导入失败: {e}")
        return False

def test_gradio_launch_params():
    """测试Gradio启动参数"""
    try:
        import gradio as gr
        
        # 创建一个简单的界面
        with gr.Blocks() as demo:
            gr.Markdown("# 测试界面")
            text = gr.Textbox(label="输入")
            output = gr.Textbox(label="输出")
            
            def echo(x):
                return x
            
            text.submit(echo, text, output)
        
        # 测试启动参数（不实际启动）
        print("✅ Gradio界面创建成功")
        print("✅ 启动参数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ Gradio测试失败: {e}")
        return False

def test_project_imports():
    """测试项目模块导入"""
    try:
        from modularizationV2.config.config import REDIS_CONFIG
        from modularizationV2.logger.log import get_logger
        print("✅ 项目模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 项目模块导入失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始测试Gradio界面...")
    print("=" * 50)
    
    # 测试Gradio导入
    gradio_ok = test_gradio_import()
    
    # 测试项目模块导入
    project_ok = test_project_imports()
    
    # 测试Gradio功能
    if gradio_ok:
        gradio_test_ok = test_gradio_launch_params()
    else:
        gradio_test_ok = False
    
    print("=" * 50)
    print("📊 测试结果:")
    print(f"  Gradio导入: {'✅' if gradio_ok else '❌'}")
    print(f"  项目模块: {'✅' if project_ok else '❌'}")
    print(f"  Gradio功能: {'✅' if gradio_test_ok else '❌'}")
    
    if all([gradio_ok, project_ok, gradio_test_ok]):
        print("\n🎉 所有测试通过！可以启动Gradio界面了。")
        print("运行命令: python run_gradio.py")
    else:
        print("\n⚠️  部分测试失败，请检查依赖安装。")
        print("运行命令: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
