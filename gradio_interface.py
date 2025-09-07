"""
Gradio界面 - 集成会话历史记忆的RAG智能问答系统
"""
# -*- coding: utf-8 -*-
import os
import time
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import gradio as gr
import redis
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

from modularizationV2.core.chain import get_rag_chain, reset_rag_chain
from modularizationV2.core.vector_store import get_vector_store_manager, reset_vector_store_manager
from modularizationV2.config.config import REDIS_CONFIG, SECURITY_CONFIG, DOCUMENT_CONFIG, PERFORMANCE_CONFIG
from modularizationV2.logger.log import get_logger, log_execution_step, log_system_startup, log_performance_metric

logger = get_logger()

class SessionManager:
    """会话管理器 - 处理会话历史、Redis缓存和清理"""
    
    def __init__(self, max_sessions: int = 10, session_ttl: int = 3600):
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        self.redis_client = self._init_redis()
        self.active_sessions = {}  # 内存中的活跃会话
        
    def _init_redis(self) -> redis.Redis:
        """初始化Redis连接"""
        log_execution_step("redis_init", "初始化Redis连接", "started", 
                          extra_data={
                              "host": REDIS_CONFIG["HOST"],
                              "port": REDIS_CONFIG["PORT"],
                              "db": REDIS_CONFIG["DB"]
                          })
        try:
            redis_client = redis.Redis(
                host=REDIS_CONFIG["HOST"],
                port=REDIS_CONFIG["PORT"],
                db=REDIS_CONFIG["DB"],
                password=REDIS_CONFIG["PASSWORD"],
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=60  # 优化为60秒
            )
            # 测试连接
            redis_client.ping()
            log_execution_step("redis_init", "初始化Redis连接", "completed")
            logger.info("Redis连接成功")
            return redis_client
        except Exception as e:
            log_execution_step("redis_init", "初始化Redis连接", "failed", 
                              extra_data={"error": str(e)})
            logger.error(f"Redis连接失败: {str(e)}")
            return None
    
    def create_session(self, user_id: str = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        user_id = user_id or "anonymous"
        
        # 检查会话数量限制
        self._cleanup_old_sessions()
        
        # 创建会话记录
        session_info = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0
        }
        
        # 存储到Redis
        if self.redis_client:
            self.redis_client.setex(
                f"session:{session_id}",
                self.session_ttl,
                json.dumps(session_info)
            )
        
        # 存储到内存
        self.active_sessions[session_id] = session_info
        
        logger.info(f"创建新会话: {session_id}")
        return session_id
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """获取会话历史"""
        if not self.redis_client:
            # 如果Redis不可用，使用内存存储
            return InMemoryChatMessageHistory()
        
        return RedisChatMessageHistory(
            session_id=session_id,
            url=f"redis://{REDIS_CONFIG['HOST']}:{REDIS_CONFIG['PORT']}/{REDIS_CONFIG['DB']}",
            key_prefix="chat_history:",
            ttl=self.session_ttl
        )
    
    def update_session_activity(self, session_id: str):
        """更新会话活动时间"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
            self.active_sessions[session_id]["message_count"] += 1
            
            # 更新Redis
            if self.redis_client:
                session_info = self.active_sessions[session_id]
                self.redis_client.setex(
                    f"session:{session_id}",
                    self.session_ttl,
                    json.dumps(session_info)
                )
    
    def clear_session(self, session_id: str):
        """清理指定会话"""
        # 清理Redis中的聊天历史
        if self.redis_client:
            try:
                # 删除聊天历史
                history_keys = self.redis_client.keys(f"chat_history:{session_id}*")
                if history_keys:
                    self.redis_client.delete(*history_keys)
                
                # 删除会话信息
                self.redis_client.delete(f"session:{session_id}")
                
                logger.info(f"清理会话: {session_id}")
            except Exception as e:
                logger.error(f"清理会话失败: {str(e)}")
        
        # 清理内存中的会话
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def clear_all_sessions(self):
        """清理所有会话"""
        # 清理Redis
        if self.redis_client:
            try:
                # 删除所有聊天历史
                history_keys = self.redis_client.keys("chat_history:*")
                if history_keys:
                    self.redis_client.delete(*history_keys)
                
                # 删除所有会话信息
                session_keys = self.redis_client.keys("session:*")
                if session_keys:
                    self.redis_client.delete(*session_keys)
                
                logger.info("清理所有会话")
            except Exception as e:
                logger.error(f"清理所有会话失败: {str(e)}")
        
        # 清理内存
        self.active_sessions.clear()
    
    def _cleanup_old_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, session_info in self.active_sessions.items():
            last_activity = datetime.fromisoformat(session_info["last_activity"])
            if (current_time - last_activity).seconds > self.session_ttl:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.clear_session(session_id)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        self._cleanup_old_sessions()
        
        total_sessions = len(self.active_sessions)
        total_messages = sum(session["message_count"] for session in self.active_sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "max_sessions": self.max_sessions,
            "redis_connected": self.redis_client is not None
        }


class InMemoryChatMessageHistory(BaseChatMessageHistory):
    """内存聊天历史存储（Redis不可用时的备用方案）"""
    
    def __init__(self):
        self.messages = []
    
    def add_message(self, message):
        self.messages.append(message)
    
    def clear(self):
        self.messages.clear()


class GradioRAGInterface:
    """Gradio RAG界面"""
    
    def __init__(self, max_sessions: int = 10):
        self.session_manager = SessionManager(max_sessions=max_sessions)
        self.rag_chain = None
        self.current_session_id = None
        self.chain_with_history = None
        
        # 当前配置参数
        self.current_config = {
            "collection_name": "My_collection_V1",
            "top_k": 5,
            "chain_type": "basic"
        }
        
        # 重置全局实例，确保使用修复后的代码
        reset_rag_chain()
        reset_vector_store_manager()
        
        # 初始化RAG链
        self._init_rag_chain()
    
    def _init_rag_chain(self, collection_name=None, top_k=None):
        """初始化RAG链"""
        collection_name = collection_name or self.current_config["collection_name"]
        top_k = top_k or self.current_config["top_k"]
        
        log_execution_step("rag_chain_init", "初始化RAG链", "started", 
                          extra_data={
                              "collection_name": collection_name,
                              "top_k": top_k
                          })
        try:
            self.rag_chain = get_rag_chain(collection_name=collection_name, top_k=top_k)
            log_execution_step("rag_chain_init", "初始化RAG链", "completed", 
                              extra_data={
                                  "collection_name": collection_name,
                                  "top_k": top_k
                              })
            logger.info(f"RAG链初始化成功 - 集合: {collection_name}, top_k: {top_k}")
        except Exception as e:
            log_execution_step("rag_chain_init", "初始化RAG链", "failed", 
                              extra_data={
                                  "error": str(e),
                                  "collection_name": collection_name,
                                  "top_k": top_k
                              })
            logger.error(f"RAG链初始化失败: {str(e)}")
    
    def update_config(self, collection_name: str, top_k: int, chain_type: str):
        """更新配置参数"""
        old_config = self.current_config.copy()
        
        # 更新配置
        self.current_config.update({
            "collection_name": collection_name,
            "top_k": top_k,
            "chain_type": chain_type
        })
        
        # 如果集合名称或top_k发生变化，重新初始化RAG链
        if (old_config["collection_name"] != collection_name or 
            old_config["top_k"] != top_k):
            self._init_rag_chain(collection_name, top_k)
        
        logger.info(f"配置已更新: {self.current_config}")
        return f"配置已更新: 集合={collection_name}, top_k={top_k}, 链类型={chain_type}"
    
    def _get_chain_with_history(self, session_id: str):
        """获取带历史记忆的链"""
        if not self.rag_chain:
            raise Exception("RAG链未初始化")
        
        # 获取会话历史
        history = self.session_manager.get_session_history(session_id)
        
        # 使用当前配置的链类型
        chain_type = self.current_config["chain_type"]
        
        # 创建带历史的链
        chain_with_history = RunnableWithMessageHistory(
            self.rag_chain.get_chain(chain_type),
            lambda session_id: history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        
        return chain_with_history
    
    def chat_with_history(self, message: str, history: List, session_id: str = None) -> Tuple[str, List]:
        """带历史记忆的聊天"""
        import asyncio
        import threading
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        
        try:
            # 如果没有会话ID，创建新会话
            if not session_id:
                session_id = self.session_manager.create_session()
            
            # 更新当前会话ID
            self.current_session_id = session_id
            
            # 获取带历史的链
            chain_with_history = self._get_chain_with_history(session_id)
            
            # 设置超时时间
            chat_timeout = PERFORMANCE_CONFIG.get("CHAT_TIMEOUT", 60)
            
            # 使用线程池执行器实现跨平台超时控制
            with ThreadPoolExecutor(max_workers=1) as executor:
                # 提交任务到线程池
                future = executor.submit(
                    chain_with_history.invoke,
                    {"input": message},
                    config={"configurable": {"session_id": session_id}}
                )
                
                # 等待结果，带超时
                try:
                    response = future.result(timeout=chat_timeout)
                except TimeoutError:
                    raise TimeoutError(f"聊天请求超时（{chat_timeout}秒）")
            
            # 更新会话活动
            self.session_manager.update_session_activity(session_id)
            
            # 更新Gradio历史
            history.append([message, response])
            
            return "", history, session_id
            
        except TimeoutError as e:
            error_msg = f"请求超时: {str(e)}"
            logger.warning(error_msg)
            history.append([message, error_msg])
            return "", history, session_id or ""
        except Exception as e:
            error_msg = f"处理查询时出错: {str(e)}"
            logger.error(error_msg)
            history.append([message, error_msg])
            return "", history, session_id or ""
    
    def clear_current_session(self, session_id: str) -> Tuple[str, List]:
        """清理当前会话"""
        if session_id:
            self.session_manager.clear_session(session_id)
            logger.info(f"清理会话: {session_id}")
            return "会话已清理", []
        return "没有活跃会话", []
    
    def clear_all_sessions(self) -> str:
        """清理所有会话"""
        self.session_manager.clear_all_sessions()
        logger.info("清理所有会话")
        return "所有会话已清理"
    
    def get_session_stats(self) -> str:
        """获取会话统计信息"""
        stats = self.session_manager.get_session_stats()
        return f"""
        📊 会话统计信息:
        • 活跃会话数: {stats['total_sessions']}/{stats['max_sessions']}
        • 总消息数: {stats['total_messages']}
        • Redis连接: {'✅ 已连接' if stats['redis_connected'] else '❌ 未连接'}
        """
    
    def create_new_session(self) -> Tuple[str, str]:
        """创建新会话"""
        session_id = self.session_manager.create_session()
        return f"新会话已创建: {session_id[:8]}...", session_id


def create_gradio_interface():
    """创建Gradio界面"""
    interface = GradioRAGInterface(max_sessions=10)
    
    with gr.Blocks(
        title="RAG智能问答系统",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
            margin: auto !important;
        }
        .chat-message {
            padding: 10px;
            margin: 5px 0;
            border-radius: 10px;
        }
        .user-message {
            background-color: #e3f2fd;
            text-align: right;
        }
        .bot-message {
            background-color: #f3e5f5;
        }
        """
    ) as demo:
        
        gr.Markdown("""
        # 🤖 RAG智能问答系统
        ### 基于检索增强生成的智能对话系统，支持会话历史记忆和Redis缓存
        """)
        
        # 会话管理区域
        with gr.Row():
            with gr.Column(scale=1):
                session_id_state = gr.State("")
                new_session_btn = gr.Button("🆕 新建会话", variant="secondary")
                clear_session_btn = gr.Button("🗑️ 清理当前会话", variant="secondary")
                clear_all_btn = gr.Button("🧹 清理所有会话", variant="secondary")
                stats_btn = gr.Button("📊 会话统计", variant="secondary")
            
            with gr.Column(scale=2):
                session_info = gr.Textbox(
                    label="当前会话信息",
                    placeholder="点击'新建会话'开始对话",
                    interactive=False
                )
                stats_display = gr.Textbox(
                    label="系统统计",
                    interactive=False,
                    lines=4
                )
        
        # 聊天区域
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="智能对话",
                    height=500,
                    show_label=True,
                    container=True,
                    bubble_full_width=False
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="请输入您的问题...",
                        label="消息输入",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)
        
        # 配置区域
        with gr.Accordion("⚙️ 高级配置", open=False):
            with gr.Row():
                collection_name = gr.Textbox(
                    label="集合名称",
                    value="My_collection_V1",
                    placeholder="向量数据库集合名称"
                )
                top_k = gr.Slider(
                    minimum=1,
                    maximum=20,
                    value=5,
                    step=1,
                    label="检索数量 (top_k)"
                )
                chain_type = gr.Dropdown(
                    choices=[
                        "basic", "rerank", "fusion", "multi_query", 
                        "complex", "compressor", "hybrid"
                    ],
                    value="basic",
                    label="链类型"
                )
            
            with gr.Row():
                apply_config_btn = gr.Button("✅ 应用配置", variant="primary")
                config_status = gr.Textbox(
                    label="配置状态",
                    value="配置已就绪",
                    interactive=False
                )
        
        # 事件处理
        def handle_new_session():
            session_info, session_id = interface.create_new_session()
            return session_info, session_id, []
        
        def handle_send_message(message, history, session_id):
            if not message.strip():
                return "", history, session_id
            
            return interface.chat_with_history(message, history, session_id)
        
        def handle_clear_session(session_id):
            return interface.clear_current_session(session_id)
        
        def handle_clear_all():
            return interface.clear_all_sessions()
        
        def handle_get_stats():
            return interface.get_session_stats()
        
        def handle_apply_config(col_name, top_k_val, chain_type_val):
            """处理配置应用"""
            try:
                result = interface.update_config(col_name, int(top_k_val), chain_type_val)
                return result
            except Exception as e:
                error_msg = f"配置应用失败: {str(e)}"
                logger.error(error_msg)
                return error_msg
        
        # 绑定事件
        new_session_btn.click(
            handle_new_session,
            outputs=[session_info, session_id_state, chatbot]
        )
        
        send_btn.click(
            handle_send_message,
            inputs=[msg_input, chatbot, session_id_state],
            outputs=[msg_input, chatbot, session_id_state]
        )
        
        msg_input.submit(
            handle_send_message,
            inputs=[msg_input, chatbot, session_id_state],
            outputs=[msg_input, chatbot, session_id_state]
        )
        
        clear_session_btn.click(
            handle_clear_session,
            inputs=[session_id_state],
            outputs=[session_info, chatbot]
        )
        
        clear_all_btn.click(
            handle_clear_all,
            outputs=[session_info]
        )
        
        stats_btn.click(
            handle_get_stats,
            outputs=[stats_display]
        )
        
        # 绑定配置应用事件
        apply_config_btn.click(
            handle_apply_config,
            inputs=[collection_name, top_k, chain_type],
            outputs=[config_status]
        )
        
        # 页面加载时显示统计信息
        demo.load(
            handle_get_stats,
            outputs=[stats_display]
        )
    
    return demo


if __name__ == "__main__":
    # 创建并启动Gradio界面
    demo = create_gradio_interface()
    
    # 启动界面
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        # enable_queue=True,
        max_threads=10,
        inbrowser=False,
        quiet=False
    )
