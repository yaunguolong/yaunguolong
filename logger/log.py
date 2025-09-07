"""
增强的日志模块 - 支持结构化日志、监控集成和详细执行步骤记录
"""
# -*- coding: utf-8 -*-
import logging
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import prometheus_client as prom

# Prometheus指标
LOG_COUNTER = prom.Counter('log_messages_total', 'Total log messages', ['level'])
LOG_LEVEL_GAUGE = prom.Gauge('log_level_count', 'Log level count', ['level'])
QUERY_DURATION = prom.Histogram('query_duration_seconds', 'Query processing duration')
UPLOAD_DURATION = prom.Histogram('upload_duration_seconds', 'Document upload duration')

class StructuredLogger:
    """结构化日志记录器 - 支持详细执行步骤记录"""
    
    def __init__(self, name: str = "rag-app", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.name = name
        
        # 确保logs目录存在
        self._ensure_log_directory()
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 控制台输出
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(console_handler)
            
            # 主应用日志文件
            try:
                app_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
                app_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self.logger.addHandler(app_handler)
            except Exception as e:
                print(f"无法创建主应用日志文件: {e}")
            
            # 执行步骤日志文件
            try:
                steps_handler = logging.FileHandler('logs/execution_steps.log', encoding='utf-8')
                steps_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self.logger.addHandler(steps_handler)
            except Exception as e:
                print(f"无法创建执行步骤日志文件: {e}")
            
            # 错误日志文件
            try:
                error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self.logger.addHandler(error_handler)
            except Exception as e:
                print(f"无法创建错误日志文件: {e}")
    
    def _ensure_log_directory(self):
        """确保日志目录存在"""
        log_dirs = ['logs', 'logs/api', 'logs/core', 'logs/gradio']
        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except Exception as e:
                    print(f"无法创建日志目录 {log_dir}: {e}")
    
    def _log_with_metrics(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录日志并更新监控指标"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **(extra or {})
        }
        
        # 更新Prometheus指标
        LOG_COUNTER.labels(level=level).inc()
        LOG_LEVEL_GAUGE.labels(level=level).set(
            sum(1 for h in self.logger.handlers if isinstance(h, logging.StreamHandler))
        )
        
        # 记录结构化日志（确保中文字符正确显示）
        if level.lower() == 'debug':
            self.logger.debug(json.dumps(log_data, ensure_ascii=False))
        elif level.lower() == 'info':
            self.logger.info(json.dumps(log_data, ensure_ascii=False))
        elif level.lower() == 'warning':
            self.logger.warning(json.dumps(log_data, ensure_ascii=False))
        elif level.lower() == 'error':
            self.logger.error(json.dumps(log_data, ensure_ascii=False))
        elif level.lower() == 'critical':
            self.logger.critical(json.dumps(log_data, ensure_ascii=False))
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_metrics('debug', message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_metrics('info', message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_metrics('warning', message, extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_metrics('error', message, extra)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_metrics('critical', message, extra)
    
    def log_query(self, query: str, documents: list, answer: str):
        """记录查询日志"""
        with QUERY_DURATION.time():
            self.info("Query processed", {
                "query": query,
                "document_count": len(documents),
                "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer,
                "answer_length": len(answer)
            })
    
    def log_document_processing(self, filename: str, doc_count: int, chunk_count: int):
        """记录文档处理日志"""
        with UPLOAD_DURATION.time():
            self.info("Document processed", {
                "filename": filename,
                "document_count": doc_count,
                "chunk_count": chunk_count
            })
    
    def log_document_deletion(self, doc_ids: list, collection_name: str):
        """记录文档删除日志"""
        self.info("Documents deleted", {
            "document_ids": doc_ids,
            "collection_name": collection_name,
            "count": len(doc_ids)
        })
    
    def log_rate_limit(self, client_ip: str, endpoint: str):
        """记录速率限制日志"""
        self.warning("Rate limit exceeded", {
            "client_ip": client_ip,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_auth_success(self, user_id: str, endpoint: str):
        """记录认证成功日志"""
        self.info("Authentication successful", {
            "user_id": user_id,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_auth_failure(self, user_id: str, endpoint: str, reason: str):
        """记录认证失败日志"""
        self.warning("Authentication failed", {
            "user_id": user_id,
            "endpoint": endpoint,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_execution_step(self, step_name: str, step_description: str, 
                          status: str = "started", duration: Optional[float] = None,
                          extra_data: Optional[Dict[str, Any]] = None):
        """记录执行步骤日志"""
        step_data = {
            "step_name": step_name,
            "step_description": step_description,
            "status": status,  # started, completed, failed
            "timestamp": datetime.utcnow().isoformat(),
            **(extra_data or {})
        }
        
        if duration is not None:
            step_data["duration_seconds"] = duration
        
        # 根据状态选择日志级别
        if status == "failed":
            self.error(f"执行步骤失败: {step_name} - {step_description}", step_data)
        elif status == "completed":
            self.info(f"执行步骤完成: {step_name} - {step_description}", step_data)
        else:
            self.info(f"执行步骤开始: {step_name} - {step_description}", step_data)
    
    def log_api_request(self, method: str, path: str, status_code: int, 
                       duration: float, client_ip: str, user_agent: str = None):
        """记录API请求日志"""
        self.info("API请求处理", {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_seconds": duration,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_system_startup(self, component: str, version: str = None, 
                          config: Optional[Dict[str, Any]] = None):
        """记录系统启动日志"""
        startup_data = {
            "component": component,
            "version": version,
            "timestamp": datetime.utcnow().isoformat(),
            **(config or {})
        }
        self.info(f"系统组件启动: {component}", startup_data)
    
    def log_system_shutdown(self, component: str, reason: str = "normal"):
        """记录系统关闭日志"""
        self.info(f"系统组件关闭: {component}", {
            "component": component,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              unit: str = "seconds", context: Optional[Dict[str, Any]] = None):
        """记录性能指标"""
        self.info(f"性能指标: {metric_name}", {
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.utcnow().isoformat(),
            **(context or {})
        })
    
    def log_configuration_change(self, config_key: str, old_value: Any, 
                                new_value: Any, source: str = "manual"):
        """记录配置变更"""
        self.info(f"配置变更: {config_key}", {
            "config_key": config_key,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_data_operation(self, operation: str, entity_type: str, 
                          entity_id: str = None, details: Optional[Dict[str, Any]] = None):
        """记录数据操作日志"""
        self.info(f"数据操作: {operation}", {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": datetime.utcnow().isoformat(),
            **(details or {})
        })

# 全局日志实例
_logger_instance = None

def get_logger() -> StructuredLogger:
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger()
    return _logger_instance

# 快捷函数
def debug(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().debug(message, extra)

def info(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().info(message, extra)

def warning(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().warning(message, extra)

def error(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().error(message, extra)

def critical(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().critical(message, extra)

def log_query(query: str, documents: list, answer: str):
    get_logger().log_query(query, documents, answer)

def log_document_processing(filename: str, doc_count: int, chunk_count: int):
    get_logger().log_document_processing(filename, doc_count, chunk_count)

def log_document_deletion(doc_ids: list, collection_name: str):
    get_logger().log_document_deletion(doc_ids, collection_name)

def log_rate_limit(client_ip: str, endpoint: str):
    get_logger().log_rate_limit(client_ip, endpoint)

def log_auth_success(user_id: str, endpoint: str):
    get_logger().log_auth_success(user_id, endpoint)

def log_auth_failure(user_id: str, endpoint: str, reason: str):
    get_logger().log_auth_failure(user_id, endpoint, reason)

# 新增的便捷函数
def log_execution_step(step_name: str, step_description: str, 
                      status: str = "started", duration: Optional[float] = None,
                      extra_data: Optional[Dict[str, Any]] = None):
    get_logger().log_execution_step(step_name, step_description, status, duration, extra_data)

def log_api_request(method: str, path: str, status_code: int, 
                   duration: float, client_ip: str, user_agent: str = None):
    get_logger().log_api_request(method, path, status_code, duration, client_ip, user_agent)

def log_system_startup(component: str, version: str = None, 
                      config: Optional[Dict[str, Any]] = None):
    get_logger().log_system_startup(component, version, config)

def log_system_shutdown(component: str, reason: str = "normal"):
    get_logger().log_system_shutdown(component, reason)

def log_performance_metric(metric_name: str, value: float, 
                          unit: str = "seconds", context: Optional[Dict[str, Any]] = None):
    get_logger().log_performance_metric(metric_name, value, unit, context)

def log_configuration_change(config_key: str, old_value: Any, 
                            new_value: Any, source: str = "manual"):
    get_logger().log_configuration_change(config_key, old_value, new_value, source)

def log_data_operation(operation: str, entity_type: str, 
                      entity_id: str = None, details: Optional[Dict[str, Any]] = None):
    get_logger().log_data_operation(operation, entity_type, entity_id, details)