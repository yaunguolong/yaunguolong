
modularization/
├── __init__.py
├── api/                  # ✅ FastAPI 主应用服务
│   ├── main.py
│   └── routes.py
├── core/                 # ✅ 核心模块
│   ├── chain.py
│   ├── vector_store.py
│   ├── model.py
│   ├── chunk.py
│   └── base_prompt.py
├── loader/               # ✅ 文档加载器
│   └── load.py
├── config/               # ✅ 配置模块
│   └── config.py
├── logger/               # ✅ 日志模块
│   └── log.py
└── tests/                # ✅ 单元测试目录
