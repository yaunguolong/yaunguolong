# 增强RAG智能问答系统

基于modularizationV2框架的完整RAG系统实现，包含性能优化、安全加固、监控增强和部署优化。

## 🚀 核心特性

### 1. 性能优化
- **缓存机制**: Redis缓存向量检索结果，减少重复计算
- **异步处理**: 支持异步模型调用和批量处理
- **连接池**: 数据库连接复用，提高并发性能
- **内存优化**: LRU缓存策略，避免内存泄漏

### 2. 安全加固
- **JWT认证**: 基于Token的API访问控制
- **速率限制**: 防止API滥用和DDoS攻击
- **输入验证**: 严格的请求参数验证
- **环境隔离**: 生产环境和开发环境分离

### 3. 监控增强
- **Prometheus集成**: 实时监控系统指标
- **结构化日志**: JSON格式日志，便于分析
- **健康检查**: 自动服务健康监测
- **性能指标**: 查询延迟、吞吐量等关键指标

### 4. 部署优化
- **Docker容器化**: 一键部署所有服务
- **环境配置**: 灵活的环境变量配置
- **健康检查**: 容器健康状态监控
- **资源限制**: CPU和内存资源限制

## 📦 系统架构

```
modularizationV2/
├── api/                 # FastAPI应用层
│   ├── mainV3.py       # 增强的主应用
│   └── routes.py       # 安全认证API路由
├── core/               # 核心业务层
│   ├── model.py        # 增强的模型管理（缓存+异步）
│   ├── chain.py        # 多策略RAG链
│   ├── vector_store.py # 带缓存的向量存储
│   ├── base_prompt.py # 提示词模板
│   └── chunk.py        # 文档分块
├── config/             # 配置管理
│   └── config.py       # 统一配置管理
├── loader/             # 文档加载
│   └── load.py         # 多格式文档加载
├── logger/             # 日志系统
│   └── log.py          # 结构化日志
├── tests/              # 单元测试
├── monitoring/         # 监控配置
│   └── prometheus.yml # Prometheus配置
├── scripts/            # 部署脚本
│   └── start.sh       # 启动脚本
├── Dockerfile          # 容器化配置
├── docker-compose.yml  # 多服务编排
└── requirements.txt    # Python依赖
```

## 🛠️ 快速开始

### 环境要求
- Python 3.11+
- Redis 7.0+
- Qdrant 1.6+
- Docker 20.10+ (可选)

### 1. 安装依赖
```bash
# 复制环境配置
cp .env.example .env

# 编辑环境变量
vim .env

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 启动服务
```bash
# 开发模式
python -m api.mainV3

# 生产模式
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 api.mainV3:app

# 使用Docker（推荐）
docker-compose up -d
```

### 3. 访问服务
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 监控面板: http://localhost:3000 (admin/admin)

## 🔧 配置说明

### 环境变量
```bash
# 数据库配置
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_HOST=localhost
REDIS_PORT=6379

# 模型配置
OPENAI_API_KEY=your-api-key
DASHSCOPE_API_KEY=your-api-key

# 安全配置
API_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
RATE_LIMIT=100

# 性能配置
CACHE_ENABLED=true
ASYNC_ENABLED=true
```

### 支持的链类型
- `basic`: 基础检索链
- `rerank`: 重排序检索
- `fusion`: RAG-Fusion融合
- `multi_query`: 多查询检索
- `complex`: 复杂问题分解
- `compressor`: 上下文压缩
- `hybrid`: 混合检索

## 📊 监控指标

系统暴露以下Prometheus指标：

- `rag_query_total`: RAG查询总数
- `rag_query_duration_seconds`: 查询处理时间
- `document_upload_total`: 文档上传统计
- `log_messages_total`: 日志消息统计
- `rate_limit_exceeded_total`: 速率限制触发次数

## 🔒 安全特性

### 认证方式
```bash
# 获取访问Token
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 使用Token访问API
curl -X GET http://localhost:8000/query \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "chain_type": "basic"}'
```

### 速率限制
- 默认限制: 100请求/分钟
- 可配置: 通过环境变量调整
- 细粒度: 支持按端点单独配置

## 🐳 容器化部署

### 服务组成
```yaml
services:
  rag-app:     # RAG应用服务
  qdrant:      # 向量数据库
  redis:       # 缓存数据库
  prometheus:  # 监控系统
  grafana:     # 监控面板
  nginx:       # 反向代理（可选）
```

### 部署命令
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f rag-app

# 停止服务
docker-compose down
```

## 🧪 测试验证

### 健康检查
```bash
curl http://localhost:8000/health
```

### 查询测试
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是人工智能？",
    "chain_type": "basic",
    "top_k": 5
  }'
```

### 监控验证
```bash
curl http://localhost:8000/metrics
```

## 🚨 故障排除

### 常见问题
1. **Redis连接失败**: 检查Redis服务状态和配置
2. **Qdrant连接失败**: 确认Qdrant服务运行正常
3. **模型调用失败**: 验证API密钥和网络连接
4. **内存不足**: 调整Docker资源限制或减少工作进程数

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# Docker容器日志
docker-compose logs -f rag-app

# 监控日志
docker-compose logs -f prometheus
```

## 📈 性能调优

### 缓存配置
```python
# 调整缓存TTL（秒）
REDIS_CACHE_TTL=3600

# 启用/禁用缓存
CACHE_ENABLED=true
```

### 并发配置
```python
# 工作进程数
WORKERS=4

# 批量处理大小
BATCH_SIZE=10

# 连接超时
CONNECTION_TIMEOUT=30
```

## 📝 版本历史

### v3.0.0 (当前)
- 完整的性能优化实现
- 安全认证和速率限制
- Prometheus监控集成
- Docker容器化部署
- 结构化日志系统

### v2.0.0
- 模块化架构设计
- 多策略RAG链支持
- 基础API服务

## 🤝 贡献指南

1. Fork本项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request
---

**注意**: 生产环境部署前请务必:
1. 修改默认密钥和密码
2. 配置适当的资源限制
3. 设置监控告警
4. 定期备份数据
