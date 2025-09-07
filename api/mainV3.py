"""
增强的RAG应用主服务 - 集成安全、监控、缓存和异步处理
"""
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import make_asgi_app
import uvicorn

from modularizationV2.api.routes import router
from modularizationV2.config.config import DEPLOYMENT_CONFIG, SECURITY_CONFIG, MONITORING_CONFIG
from modularizationV2.logger.log import get_logger, log_execution_step, log_system_startup, log_api_request

# 初始化日志
logger = get_logger()

# 记录应用启动
log_system_startup("FastAPI应用", "3.0.0", {
    "host": DEPLOYMENT_CONFIG["HOST"],
    "port": DEPLOYMENT_CONFIG["PORT"],
    "workers": DEPLOYMENT_CONFIG["WORKERS"],
    "reload": DEPLOYMENT_CONFIG["RELOAD"]
})

# 初始化速率限制器
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="增强版RAG智能问答系统",
    description="基于检索增强生成的文档管理和智能问答API服务，支持多种检索策略、缓存、监控和安全认证",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加Prometheus监控
if MONITORING_CONFIG["PROMETHEUS_ENABLED"]:
    log_execution_step("prometheus_setup", "初始化Prometheus监控", "started")
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    log_execution_step("prometheus_setup", "初始化Prometheus监控", "completed")
    logger.info("Prometheus监控已启用")

# 中间件配置
log_execution_step("middleware_setup", "配置中间件", "started")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
log_execution_step("middleware_setup", "配置中间件", "completed")

# 速率限制异常处理
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    client_ip = get_remote_address(request)
    logger.log_rate_limit(client_ip, request.url.path)
    return JSONResponse(
        status_code=429,
        content={"error": "请求频率过高", "retry_after": exc.retry_after}
    )

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {str(exc)}", {
        "path": request.url.path,
        "method": request.method,
        "client_ip": get_remote_address(request)
    })
    return JSONResponse(
        status_code=500,
        content={"error": "内部服务器错误", "status": "error"}
    )

# 请求生命周期监控
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # 记录请求开始
    log_execution_step("api_request", f"处理API请求: {request.method} {request.url.path}", "started", 
                      extra_data={
                          "method": request.method,
                          "path": request.url.path,
                          "client_ip": get_remote_address(request),
                          "user_agent": request.headers.get("user-agent")
                      })
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-API-Version"] = "3.0.0"
        
        # 记录请求完成
        log_execution_step("api_request", f"处理API请求: {request.method} {request.url.path}", "completed", 
                          duration=process_time,
                          extra_data={
                              "status_code": response.status_code,
                              "method": request.method,
                              "path": request.url.path,
                              "client_ip": get_remote_address(request)
                          })
        
        # 使用新的API请求日志函数
        log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=process_time,
            client_ip=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        log_execution_step("api_request", f"处理API请求: {request.method} {request.url.path}", "failed", 
                          duration=process_time,
                          extra_data={
                              "error": str(e),
                              "method": request.method,
                              "path": request.url.path,
                              "client_ip": get_remote_address(request)
                          })
        raise

# 注册API路由
log_execution_step("router_registration", "注册API路由", "started")
app.include_router(router)
log_execution_step("router_registration", "注册API路由", "completed")

# 健康检查端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "增强版RAG智能问答系统",
        "version": "3.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "3.0.0",
        "components": {
            "api": "running",
            "monitoring": "enabled" if MONITORING_CONFIG["PROMETHEUS_ENABLED"] else "disabled",
            "security": "enabled" if SECURITY_CONFIG["API_KEY"] else "disabled"
        }
    }

# 系统信息端点
@app.get("/system/info")
async def system_info():
    """获取系统信息"""
    from modularizationV2.config.config import get_config
    config = get_config()
    
    return {
        "deployment": config["deployment"],
        "performance": config["performance"],
        "monitoring": config["monitoring"],
        "security": {
            "rate_limit": config["security"]["RATE_LIMIT"],
            "jwt_enabled": bool(config["security"]["JWT_SECRET"])
        }
    }

if __name__ == "__main__":
    # 启动应用
    log_execution_step("app_startup", "启动FastAPI应用", "started", 
                      extra_data={
                          "host": DEPLOYMENT_CONFIG["HOST"],
                          "port": DEPLOYMENT_CONFIG["PORT"],
                          "workers": DEPLOYMENT_CONFIG["WORKERS"],
                          "reload": DEPLOYMENT_CONFIG["RELOAD"]
                      })
    
    try:
        if DEPLOYMENT_CONFIG["RELOAD"] or DEPLOYMENT_CONFIG["WORKERS"] > 1:
            # 使用导入字符串以支持reload和workers
            uvicorn.run(
                "api.mainV3:app",
                host=DEPLOYMENT_CONFIG["HOST"],
                port=DEPLOYMENT_CONFIG["PORT"],
                reload=DEPLOYMENT_CONFIG["RELOAD"],
                workers=DEPLOYMENT_CONFIG["WORKERS"],
                log_level=DEPLOYMENT_CONFIG["LOG_LEVEL"]
            )
        else:
            # 直接传递app对象
            uvicorn.run(
                app,
                host=DEPLOYMENT_CONFIG["HOST"],
                port=DEPLOYMENT_CONFIG["PORT"],
                reload=DEPLOYMENT_CONFIG["RELOAD"],
                workers=DEPLOYMENT_CONFIG["WORKERS"],
                log_level=DEPLOYMENT_CONFIG["LOG_LEVEL"]
            )
        
        log_execution_step("app_startup", "启动FastAPI应用", "completed")
        
    except Exception as e:
        log_execution_step("app_startup", "启动FastAPI应用", "failed", 
                          extra_data={"error": str(e)})
        raise