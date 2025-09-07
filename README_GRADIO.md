# 🤖 RAG智能问答系统 - Gradio界面

基于Gradio的RAG智能问答系统，集成了会话历史记忆、Redis缓存和多种检索策略。

## ✨ 主要特性

### 🧠 会话历史记忆
- **RunnableWithMessageHistory**: 集成LangChain的会话历史组件
- **ChatMessageHistory**: 支持Redis和内存两种存储方式
- **会话持久化**: 自动保存对话历史到Redis
- **会话管理**: 支持创建、清理和统计会话

### 🔧 高级功能
- **多会话支持**: 可同时管理多个对话会话
- **会话数量控制**: 自定义最大会话数量限制
- **自动清理**: 定期清理过期会话
- **Redis缓存**: 高性能的会话数据存储
- **实时统计**: 显示会话和系统统计信息

### 🎨 用户界面
- **现代化设计**: 基于Gradio 4.0的现代化界面
- **响应式布局**: 适配不同屏幕尺寸
- **实时交互**: 流畅的对话体验
- **配置面板**: 可调整检索参数和链类型

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并配置必要的环境变量：

```env
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 模型配置
MODEL_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_api_key_here

# 向量数据库配置
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=rag_collection
```

### 3. 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
# 基本启动
python run_gradio.py

# 自定义配置
python run_gradio.py --host 0.0.0.0 --port 7860 --max-sessions 20

# 启用公共链接
python run_gradio.py --share

# 调试模式
python run_gradio.py --debug
```

#### 方式二：直接运行

```bash
python gradio_interface.py
```

### 4. 访问界面

打开浏览器访问：`http://localhost:7860`

## 📖 使用指南

### 会话管理

1. **新建会话**: 点击"🆕 新建会话"按钮创建新的对话会话
2. **清理会话**: 点击"🗑️ 清理当前会话"清理当前会话的历史记录
3. **清理所有**: 点击"🧹 清理所有会话"清理所有会话数据
4. **查看统计**: 点击"📊 会话统计"查看系统统计信息

### 对话功能

1. **发送消息**: 在输入框中输入问题，点击"发送"或按Enter键
2. **查看历史**: 聊天界面会显示完整的对话历史
3. **会话记忆**: 系统会自动记住之前的对话内容

### 高级配置

在"⚙️ 高级配置"面板中可以调整：

- **集合名称**: 向量数据库集合名称
- **检索数量**: 每次检索的文档数量 (top_k)
- **链类型**: 选择不同的RAG链类型
  - `basic`: 基础RAG检索链
  - `rerank`: 重排序优化链
  - `fusion`: RAG-Fusion链
  - `multi_query`: 多查询链
  - `complex`: 复杂问题分解链
  - `compressor`: 上下文压缩链
  - `hybrid`: 混合检索链

## 🔧 技术架构

### 核心组件

```
GradioRAGInterface
├── SessionManager          # 会话管理器
│   ├── Redis存储          # 会话数据持久化
│   ├── 内存缓存           # 快速访问
│   └── 自动清理           # 过期会话管理
├── RunnableWithMessageHistory  # LangChain会话历史
├── ChatMessageHistory     # 消息历史存储
└── EnhancedRAGChain       # RAG检索链
```

### 数据流

```
用户输入 → 会话历史检索 → RAG链处理 → 响应生成 → 历史更新 → 用户显示
```

### 存储架构

```
Redis存储:
├── session:{session_id}     # 会话元数据
├── chat_history:{session_id} # 聊天历史
└── 自动TTL过期管理

内存缓存:
├── active_sessions         # 活跃会话
└── 快速访问优化
```

## 🛠️ 配置选项

### 启动参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 0.0.0.0 | 服务器主机地址 |
| `--port` | 7860 | 服务器端口 |
| `--share` | False | 是否创建公共链接 |
| `--max-sessions` | 10 | 最大会话数量 |
| `--debug` | False | 启用调试模式 |

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REDIS_HOST` | localhost | Redis主机地址 |
| `REDIS_PORT` | 6379 | Redis端口 |
| `REDIS_DB` | 0 | Redis数据库编号 |
| `REDIS_PASSWORD` | - | Redis密码 |
| `REDIS_CACHE_TTL` | 3600 | 缓存过期时间(秒) |

## 🔍 故障排除

### 常见问题

1. **Redis连接失败**
   ```
   错误: Redis连接失败
   解决: 检查Redis服务是否启动，配置是否正确
   ```

2. **模型API调用失败**
   ```
   错误: 模型调用失败
   解决: 检查API密钥配置，网络连接是否正常
   ```

3. **向量数据库连接失败**
   ```
   错误: Qdrant连接失败
   解决: 确认Qdrant服务运行正常，端口配置正确
   ```

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log
```

### 性能优化

1. **调整会话数量**: 根据内存情况调整`max_sessions`参数
2. **Redis配置**: 优化Redis内存配置和持久化策略
3. **缓存策略**: 调整缓存TTL和清理频率

## 📊 监控和统计

### 会话统计信息

- 活跃会话数量
- 总消息数量
- Redis连接状态
- 系统资源使用情况

### 性能指标

- 响应时间
- 内存使用
- Redis操作延迟
- 错误率统计

## 🔒 安全考虑

1. **会话隔离**: 每个会话独立存储，避免数据泄露
2. **自动过期**: 会话数据自动过期清理
3. **访问控制**: 可集成用户认证系统
4. **数据加密**: Redis连接支持SSL加密

## 🚀 部署建议

### 生产环境

1. **使用反向代理**: Nginx或Apache
2. **SSL证书**: 启用HTTPS
3. **Redis集群**: 高可用Redis配置
4. **监控告警**: 集成监控系统
5. **日志管理**: 集中化日志收集

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 7860

CMD ["python", "run_gradio.py", "--host", "0.0.0.0", "--port", "7860"]
```

## 📝 更新日志

### v1.0.0
- ✅ 基础Gradio界面
- ✅ 会话历史记忆功能
- ✅ Redis缓存集成
- ✅ 会话管理功能
- ✅ 多种RAG链支持

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目采用MIT许可证。
