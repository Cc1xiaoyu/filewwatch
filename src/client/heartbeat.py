import threading
import time
import requests
from typing import Dict
import logging
from datetime import datetime

logger = logging.getLogger("FileMonitor.Heartbeat")

class HeartbeatClient:
    def __init__(self, client_id: str, api_endpoint: str, api_key: str, interval: int):
        """

        :param client_id: 客户端id
        :param api_endpoint:
        :param api_key:
        :param interval: 心跳间隔 int
        """
        self.client_id = client_id
        self.api_endpoint = api_endpoint
        self.headers = {"X-API-Key": api_key}
        self.interval = interval
        self._timer = None
        self.is_running = False

    def _send_heartbeat(self):
        """发送心跳请求（带重试）"""
        try:
            data = {
                "client_id": self.client_id,
                "timestamp": datetime.now().isoformat()
            }
            response = requests.post(
                self.api_endpoint,
                json=data,
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"心跳发送失败: {str(e)}")
        finally:
            if self.is_running:
                self._schedule_next()

    def _schedule_next(self):
        """安排下一次心跳"""
        self._timer = threading.Timer(self.interval, self._send_heartbeat)
        self._timer.daemon = True  # 作为守护线程
        self._timer.start()

    def start(self):
        """启动心跳线程"""
        if not self.is_running:
            self.is_running = True
            self._schedule_next()
            logger.info("心跳检测已启动")

    def stop(self):
        """停止心跳"""
        if self._timer:
            self._timer.cancel()
        self.is_running = False
        logger.info("心跳检测已停止")