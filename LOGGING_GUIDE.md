# 增强日志系统使用指南

## 📋 概述

本系统已升级为增强的日志系统，支持详细的执行步骤记录、结构化日志和本地文件存储。

## 🗂️ 日志文件结构

```
logs/
├── app.log                 # 主应用日志
├── execution_steps.log     # 执行步骤日志
├── errors.log             # 错误日志
├── api/                   # API相关日志目录
├── core/                  # 核心模块日志目录
└── gradio/                # Gradio界面日志目录
```

## 🔧 主要功能

### 1. 执行步骤日志记录
```python
from modularizationV2.logger.log import log_execution_step

# 记录步骤开始
log_execution_step("database_connection", "连接数据库", "started")

# 记录步骤完成
log_execution_step("database_connection", "连接数据库", "completed", duration=0.5)

# 记录步骤失败
log_execution_step("database_connection", "连接数据库", "failed", 
                  extra_data={"error": "连接超时"})
```

### 2. 系统启动/关闭日志
```python
from modularizationV2.logger.log import log_system_startup, log_system_shutdown

# 记录系统启动
log_system_startup("FastAPI应用", "3.0.0", {
    "host": "127.0.0.1",
    "port": 8000
})

# 记录系统关闭
log_system_shutdown("FastAPI应用", "正常关闭")
```

### 3. API请求日志
```python
from modularizationV2.logger.log import log_api_request

log_api_request(
    method="GET",
    path="/api/health",
    status_code=200,
    duration=0.1,
    client_ip="127.0.0.1",
    user_agent="Mozilla/5.0..."
)
```

### 4. 性能指标日志
```python
from modularizationV2.logger.log import log_performance_metric

log_performance_metric("query_processing_time", 1.5, "seconds", {
    "query_type": "rag",
    "document_count": 10
})
```

### 5. 配置变更日志
```python
from modularizationV2.logger.log import log_configuration_change

log_configuration_change("top_k", 5, 10, "user_interface")
```

### 6. 数据操作日志
```python
from modularizationV2.logger.log import log_data_operation

log_data_operation("create", "document", "doc_123", {
    "filename": "test.pdf",
    "size": 1024
})
```

## 📊 日志格式

### 控制台输出格式
```
2025-09-07 20:47:24,779 - rag-app - INFO - {"timestamp": "2025-09-07T12:47:24.779020", "level": "info", "message": "执行步骤开始: test_step - 测试执行步骤", "step_name": "test_step", "step_description": "测试执行步骤", "status": "started"}
```

### 文件存储格式
- **app.log**: 所有日志记录
- **execution_steps.log**: 执行步骤相关日志
- **errors.log**: 仅错误级别日志

## 🎯 使用场景

### 1. 应用启动流程
```python
# 在mainV3.py中
log_system_startup("FastAPI应用", "3.0.0")
log_execution_step("middleware_setup", "配置中间件", "started")
# ... 配置中间件
log_execution_step("middleware_setup", "配置中间件", "completed")
```

### 2. API请求处理
```python
# 在中间件中自动记录
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    log_execution_step("api_request", f"处理API请求: {request.method} {request.url.path}", "started")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        log_execution_step("api_request", f"处理API请求: {request.method} {request.url.path}", "completed", duration=process_time)
        return response
    except Exception as e:
        log_execution_step("api_request", f"处理API请求: {request.method} {request.url.path}", "failed", extra_data={"error": str(e)})
        raise
```

### 3. RAG链处理
```python
# 在gradio_interface.py中
def _init_rag_chain(self, collection_name=None, top_k=None):
    log_execution_step("rag_chain_init", "初始化RAG链", "started", 
                      extra_data={"collection_name": collection_name, "top_k": top_k})
    try:
        self.rag_chain = get_rag_chain(collection_name=collection_name, top_k=top_k)
        log_execution_step("rag_chain_init", "初始化RAG链", "completed")
    except Exception as e:
        log_execution_step("rag_chain_init", "初始化RAG链", "failed", extra_data={"error": str(e)})
```

## 🔍 日志查看

### 查看实时日志
```bash
# 查看主应用日志
tail -f logs/app.log

# 查看执行步骤日志
tail -f logs/execution_steps.log

# 查看错误日志
tail -f logs/errors.log
```

### 搜索特定日志
```bash
# 搜索特定步骤
grep "rag_chain_init" logs/execution_steps.log

# 搜索错误日志
grep "ERROR" logs/app.log

# 搜索特定时间段的日志
grep "2025-09-07 20:47" logs/app.log
```

## ⚙️ 配置选项

### 日志级别
- DEBUG: 详细调试信息
- INFO: 一般信息（默认）
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

### 文件编码
- 所有日志文件使用UTF-8编码
- 支持中文字符正确显示
- 无Unicode转义序列

## 🚀 最佳实践

1. **步骤命名**: 使用描述性的步骤名称，如`database_connection`、`rag_chain_init`
2. **状态管理**: 始终记录步骤的开始、完成和失败状态
3. **错误信息**: 在失败时提供详细的错误信息
4. **性能监控**: 记录关键操作的执行时间
5. **结构化数据**: 使用extra_data参数提供上下文信息

## 📈 监控集成

日志系统已集成Prometheus监控指标：
- `log_messages_total`: 总日志消息数
- `log_level_count`: 各级别日志计数
- `query_duration_seconds`: 查询处理时间
- `upload_duration_seconds`: 文档上传时间

## 🔧 故障排除

### 常见问题

1. **日志文件未创建**
   - 检查logs目录权限
   - 确保有足够的磁盘空间

2. **中文字符显示问题**
   - 确保使用UTF-8编码查看文件
   - 检查终端编码设置

3. **日志文件过大**
   - 考虑配置日志轮转
   - 定期清理旧日志文件

### 调试模式
```python
# 启用调试级别日志
logger = get_logger()
logger.logger.setLevel(logging.DEBUG)
```

---

**注意**: 本日志系统已完全集成到现有应用中，无需额外配置即可使用。所有执行步骤都会自动记录到相应的日志文件中。
