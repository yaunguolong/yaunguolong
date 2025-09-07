#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gradio界面启动脚本
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
parent_dir = project_root.parent
sys.path.insert(0, str(parent_dir))

from modularizationV2.gradio_interface import create_gradio_interface
from modularizationV2.logger.log import get_logger

logger = get_logger()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动RAG智能问答系统Gradio界面")
    parser.add_argument(
        "--host", 
        default="127.0.0.1",
        help="服务器主机地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=7860, 
        help="服务器端口 (默认: 7860)"
    )
    parser.add_argument(
        "--share", 
        action="store_true", 
        help="是否创建公共链接 (默认: False)"
    )
    parser.add_argument(
        "--max-sessions", 
        type=int, 
        default=10, 
        help="最大会话数量 (默认: 10)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试模式"
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("正在启动Gradio界面...")
        logger.info(f"服务器地址: http://{args.host}:{args.port}")
        logger.info(f"最大会话数: {args.max_sessions}")
        
        # 创建Gradio界面
        demo = create_gradio_interface()
        
        # 启动界面
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=args.debug,
            #enable_queue=True,
            max_threads=10,
            debug=args.debug,
            inbrowser=False,
            quiet=not args.debug
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭...")
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
