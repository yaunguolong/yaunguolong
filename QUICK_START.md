# 🚀 Gradio界面快速启动指南

## 快速启动

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 测试环境
```bash
python test_gradio.py
```

### 3. 启动界面

#### 方式一：直接运行
```bash
python gradio_interface.py
```

#### 方式二：使用启动脚本（推荐）
```bash
# 基本启动
python run_gradio.py

# 自定义配置
python run_gradio.py --host 127.0.0.1 --port 7860 --max-sessions 20

# 调试模式
python run_gradio.py --debug
```

### 4. 访问界面
打开浏览器访问：`http://127.0.0.1:7860`

## 功能特性

- ✅ 会话历史记忆
- ✅ Redis缓存支持
- ✅ 多会话管理
- ✅ 自动会话清理
- ✅ 实时统计信息
- ✅ 多种RAG链类型
- ✅ 现代化UI界面

## 故障排除

### 常见问题

1. **Gradio版本问题**
   ```bash
   pip install --upgrade gradio>=4.0.0
   ```

2. **Redis连接失败**
   - 检查Redis服务是否启动
   - 验证配置文件中的Redis连接参数

3. **模块导入失败**
   - 确保在项目根目录运行
   - 检查Python路径设置

### 测试命令
```bash
# 运行测试脚本
python test_gradio.py

# 检查依赖
pip list | grep gradio
```

## 配置说明

### 环境变量
```env
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 模型配置
MODEL_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_api_key

# 向量数据库
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=My_collection_V1
```

### 启动参数
- `--host`: 服务器地址 (默认: 127.0.0.1)
- `--port`: 服务器端口 (默认: 7860)
- `--max-sessions`: 最大会话数 (默认: 10)
- `--debug`: 调试模式
- `--share`: 创建公共链接

## 使用说明

1. **新建会话**: 点击"🆕 新建会话"开始对话
2. **发送消息**: 在输入框输入问题，点击发送
3. **查看历史**: 聊天界面显示完整对话历史
4. **管理会话**: 使用清理按钮管理会话数据
5. **查看统计**: 点击统计按钮查看系统信息

## 技术架构

```
Gradio界面
├── SessionManager (会话管理)
├── RunnableWithMessageHistory (历史记忆)
├── RedisChatMessageHistory (Redis存储)
├── EnhancedRAGChain (RAG链)
└── 现代化UI组件
```

现在可以正常启动Gradio界面了！🎉
