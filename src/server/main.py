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
import uuid
import json
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
client_status: Dict[str, Dict] = {}  # 客户端状态存储 # 结构：{'client_id': {last_heartbeat:datetime,now(), 'ip':[ip]}}
client_status2: Dict[str, Dict] = {}  # 结构：{client_id: {online, last_seen, ip, hostname}}
clients_lock = asyncio.Lock()  # 异步锁保证线程安全
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

    async with clients_lock:
        # 更新状态
        client_status[data.client_id] = {
            "last_heartbeat": datetime.now().isoformat(),
            "ip": request.client.host
        }
        client_status2[data.client_id]={
            "online":True,
            "last_seen":datetime.now().isoformat(),
            "ip":request.client.host,
            "hostname":data.client_id
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
@app.get("/",response_class=HTMLResponse)
async def dashboard(request: Request):
    """主路由,返回动态页面:监控仪表盘"""


    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            # "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")
        },  # ,"clients_event":events_db
    )
# --------------------------时间传递---------------------------------------
# SSE 时间流端点
async def sse_event_stream():
    """sse数据传输"""
    while True:
        # 深拷贝当前状态避免数据竞争
        async with clients_lock:
            current_clients = client_status2.copy()
        """字典推导式中的**info是用于解包原有字典，合并到新字典中，然后后面的"online": ...会覆盖原有的online键。这里需要说明合并的顺序，后面的键会覆盖前面的，所以新的online值会替换原来的。"""
        # 转换为可序列化格式
        data = {
            cid: {
                **info,  # 解包原有字典
                "online": info["online"] and  # 二次验证是否超时
                          (datetime.now() - datetime.fromisoformat(info["last_seen"])).seconds < HEARTBEAT_TIMEOUT
            }
            for cid, info in current_clients.items()
        }
        # 按照 SSE 格式生成字符串
        time_data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        outData={"timestamp":time_data,
                 "clients_activeStatus":data}

        json_data = json.dumps(outData)# 关键修复：用 json.dumps 生成合法 JSON
        yield f"data: {json_data} \n\n"

        # 每一秒更新一次
        await asyncio.sleep(1)


# SSE 路由
@app.get("/sse/data")
async def sse_data():
    """定时获取时间+客户端状态"""
    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream"  # 必须声明为事件流
    )
@app.get("/sse/data")
async def sse_data():
    """定时获取客户端状态"""
    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream"  # 必须声明为事件流
    )


"""示例
{
  "DESKTOP-JG61K5D": {
    "online": true,
    "last_heartbeat": "2025-04-05T16:41:37.722801",
    "ip": "192.168.30.1"
  }
}
"""
@app.get("/api/data")
async def get_latest_data():
    """提供最新的客户端数据"""
    return get_client_status()

"""示例
{
  "clients": {
    "DESKTOP-JG61K5D": {
      "online": true,
      "last_heartbeat": "2025-04-05T16:44:08.072718",
      "ip": "192.168.30.1"
    }
  },
  "recent_events": [
    {
      "host": "DESKTOP-JG61K5D",
      "path": "D:\\code\\python\\filewatch\\test_folder\\111\\新建文本文档.txt",
      "event_type": "moved",
      "timestamp": "2025-04-05T16:44:01.851174"
    },
    {
      "host": "DESKTOP-JG61K5D",
      "path": "D:\\code\\python\\filewatch\\test_folder\\111\\新建文本文档.txt",
      "event_type": "created",
      "timestamp": "2025-04-05T16:44:00.205860"
    }
  ]
}
"""
@app.get("/api/status")
async def get_real_time_status():
    """获取客户端的实时状态数据"""
    return {
        "clients": get_client_status(),
        "recent_events": get_recent_events()
    }


if __name__ == "__main__":
    logger.info("服务器启动")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # 启用 uvicorn 服务器运行 python 服务
