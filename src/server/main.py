# 服务器代码
from fastapi import FastAPI, Security, HTTPException, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import logging
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("server.log")  # 同时记录到文件
    ]
)
logger = logging.getLogger("FileMonitorServer")

app = FastAPI(title="File Monitor Server")

# 简单存储（实际应使用数据库）
events_db = []

# 认证配置
API_KEY = "your-secret-key-123"
api_key_header = APIKeyHeader(name="X-API-Key")


class FileEvent(BaseModel):
    host: str  # 客户端主机标识
    path: str  # 文件路径
    event_type: str  # created/modified/deleted/moved
    timestamp: str  # ISO 格式时间戳
    dest_path: str = None

#post请求
@app.post("/api/events")
async def report_event(
        request: Request,  # 新增：获取请求对象
        event: FileEvent,
        api_key: str = Security(api_key_header)
):
    """接收并处理客户端事件"""
    client_ip = request.client.host  # 获取客户端IP

    """接收客户端上报的文件事件"""
    if api_key != API_KEY:
        logger.warning(f"认证失败！客户端IP: {client_ip}，使用的Key: {api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 记录接收的事件
    logger.info(
        f"收到来自 {event.host} 的事件: "
        f"类型={event.event_type}, 路径={event.path}"
    )

    # 添加时间戳和服务端记录时间
    server_timestamp = datetime.utcnow().isoformat()
    event_data = event.dict()
    event_data["server_time"] = server_timestamp

    events_db.append(event_data)
    return {"status": "success"}

@app.get("/api/events")
async def get_events():
    """获取所有事件（用于调试）"""
    return {"count": len(events_db), "events": events_db}

if __name__ == "__main__":
    logger.info("服务器启动，监听在 http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)