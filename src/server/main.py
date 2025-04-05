# 服务器代码
from fastapi import FastAPI, Security, HTTPException, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
import logging

from typing import Dict, List, Deque
from collections import deque
import time
import asyncio
# ---------- Web界面相关 ----------
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
# -------------------错误处理---------------------------
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# ---------- 全局状态存储 # 简单存储（实际应使用数据库）----------
events_db: Deque[Dict] = deque(maxlen=50)  # 保留最近50条事件
client_status: Dict[str, Dict] = {}  # 客户端状态存储
last_data_update = time.time()  # 最后数据更新时间戳

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("server.log")  # 同时记录到文件
    ]
)
logger = logging.getLogger("FileMonitorServer")
# ---------- FastAPI应用 ----------
app = FastAPI(title="File Monitor Server")
# 认证配置
API_KEY = "your-secret-key-123"
api_key_header = APIKeyHeader(name="X-API-Key")
HEARTBEAT_TIMEOUT = 90  # 从配置读取，此处简化为常量
# ---------- Web界面相关 ----------

# 挂载静态文件和模板 正确挂载静态文件（关键修改点）
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)
templates = Jinja2Templates(directory="templates", auto_reload=True)


# ---------- 核心功能函数 ----------
def has_new_data() -> bool:
    """检查是否有新数据（简易版：定时刷新）"""
    global last_data_update
    # 每2秒强制刷新一次（生产环境应基于实际数据变更检测）
    if time.time() - last_data_update > 2:
        last_data_update = time.time()
        return True
    return False


def get_recent_events() -> List[Dict]:
    """获取最近50条事件（倒序排列）"""
    return [
        {
            "host": event["host"],
            "path": event["path"],
            "event_type": event["event_type"],
            "timestamp": event["timestamp"]
        }
        for event in reversed(events_db)  # 最新事件在前
    ]


def get_client_status() -> Dict[str, Dict]:
    """获取客户端在线状态"""
    status = {}
    now = datetime.now()

    for client_id, info in client_status.items():
        last_heartbeat = info["last_heartbeat"]  # 上一次时间
        offline_seconds = (now - last_heartbeat).total_seconds()

        status[client_id] = {
            "online": offline_seconds < HEARTBEAT_TIMEOUT,
            "last_heartbeat": last_heartbeat.isoformat(),
            "ip": info["ip"]
        }
    return status


class HeartbeatData(BaseModel):
    """
    心跳数据
    """
    client_id: str
    timestamp: str  # ISO格式时间戳


class FileEvent(BaseModel):
    host: str  # 客户端主机标识
    event_type: str  # created/modified/deleted/moved
    timestamp: str  # ISO 格式时间戳
    path: str  # 文件路径
    dest_path: str | None = None  # 允许 None


# ---------- API端点 ----------
# ----------接收并处理客户端上报事件 ----------
# post请求
@app.post("/api/events")
async def report_event(
        event: FileEvent,
        request: Request,  # 新增：获取请求对象
        api_key: str = Security(api_key_header)
):
    """接收并处理客户端上报事件"""
    client_ip = request.client.host  # 获取客户端IP

    """接收客户端上报的文件事件"""
    if api_key != API_KEY:
        logger.warning(f"认证失败！客户端IP: {client_ip}，使用的Key: {api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 记录接收的事件
    logger.info(
        f"收到来自 {event.host} 的事件: ,时间:{event.timestamp}"
        f"类型={event.event_type}, 路径={event.path}"
    )

    # 存储事件（自动维护队列长度）
    events_db.append({
        "host": event.host,
        "path": event.path,
        "event_type": event.event_type,
        "timestamp": event.timestamp
    })

    # # 添加时间戳和服务端记录时间
    # server_timestamp = datetime.now().isoformat()
    # # event_data = event.dict()
    # event_data = event.model_dump()
    # event_data["server_time"] = server_timestamp
    #
    # events_db.append(event_data)
    return {"status": "success"}


# 心跳检测 报告
@app.post("/api/events/heartbeat")
async def report_heartbeat(
        request: Request,
        data: HeartbeatData,
        api_key: str = Security(api_key_header)
):
    """接收客户端心跳"""
    # 认证检查
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 更新状态
    client_status[data.client_id] = {
        "last_heartbeat": datetime.now(),
        "ip": request.client.host
    }
    logger.info(f"收到来自 {data.client_id} 的心跳")
    return {"status": "alive"}


@app.get("/api/events/status")
async def get_clients_status():
    """获取所有客户端状态（调试用）"""
    status = {}
    for client_id, info in client_status.items():
        last_time = info["last_heartbeat"]
        offline_seconds = (datetime.now() - last_time).total_seconds()
        status[client_id] = {
            "online": offline_seconds < 90,  # 假设超时阈值为90秒
            "last_heartbeat": last_time.isoformat(),
            "ip": info["ip"]
        }
    return status


@app.get("/api/events")
async def get_events():
    """获取所有事件（用于调试）"""
    return {"count": len(events_db), "events": events_db}


# -------------------错误处理---------------------------



"""添加全局异常处理器，返回具体的验证错误信息："""


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_body = await request.body()
    try:
        body = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        body = "[Binary data]"

    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": body
        },
    )


# , response_class=HTMLResponse
# ----------主路由,返回动态页面----------
@app.get("/")
async def dashboard(request: Request):
    """主路由,返回动态页面:监控仪表盘"""
    # client_status_data:Dict[str, Dict]=get_client_status()
    client_status_data = {
        "1": {'ip': "192.168.1.12", 'online': True, 'last_heartbeat': "2025-12-1 11:36"},
        "2": {'ip': "192.168.1.13", 'online': False, 'last_heartbeat': "2025-12-2 11:36"},
        "3": {'ip': "192.168.1.14", 'online': True, 'last_heartbeat': "2025-12-3 11:36"},

    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "clients_status": {
                "1": {'ip': "192.168.1.12", 'online': True, 'last_heartbeat': "2025-12-1 11:36"},
                "2": {'ip': "192.168.1.13", 'online': False, 'last_heartbeat': "2025-12-2 11:36"},
                "3": {'ip': "192.168.1.14", 'online': True, 'last_heartbeat': "2025-12-3 11:36"},

            },
            # "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")
        },  # ,"clients_event":events_db
    )
# --------------------------时间传递---------------------------------------
# SSE 时间流端点
async def time_event_stream():
    while True:
        # 生成当前时间（格式化为字符串）
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # SSE 数据格式要求：以 "data: " 开头，结尾用两个换行
        yield f"data: {current_time}\n\n"

        # 等待1秒
        await asyncio.sleep(1)


# SSE 路由
@app.get("/sse/time")
async def sse_time():
    return StreamingResponse(
        time_event_stream(),
        media_type="text/event-stream"  # 必须声明为事件流
    )




@app.get("/api/data")
async def get_latest_data():
    """提供最新数据的API端点"""
    return get_client_status()


@app.get("/api/status")
async def get_real_time_status():
    """获取实时状态"""
    return {
        "clients": get_client_status(),
        "recent_events": get_recent_events()
    }


if __name__ == "__main__":
    logger.info("服务器启动")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # 启用 uvicorn 服务器运行 python 服务
