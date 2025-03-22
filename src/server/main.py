# 服务器代码

from fastapi import FastAPI, Security, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import uvicorn
from datetime import datetime

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

#post请求
@app.post("/api/events")
async def report_event(
        event: FileEvent,
        api_key: str = Security(api_key_header)
):
    """接收客户端上报的文件事件"""
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 添加时间戳和服务端记录时间
    server_timestamp = datetime.utcnow().isoformat()
    event_data = event.dict()
    event_data["server_time"] = server_timestamp

    events_db.append(event_data)
    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)