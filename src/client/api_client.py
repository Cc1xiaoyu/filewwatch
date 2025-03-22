# 客户端

import requests
from retrying import retry
import logging
from typing import Dict, Any

logger = logging.getLogger("FileMonitor.APIClient")

class APIClient:
    def __init__(self, endpoint: str, api_key: str, max_retries: int = 3):
        self.endpoint = endpoint
        self.headers = {"X-API-Key": api_key}
        self.max_retries = max_retries

    def _should_retry(self, exception) -> bool:
        """决定是否重试"""
        return isinstance(exception, (requests.ConnectionError, requests.Timeout))

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000,
           retry_on_exception=_should_retry)
    def report_event(self, event_data: Dict[str, Any]) -> bool:
        """上报事件到服务器（自动重试）"""
        try:
            response = requests.post(
                self.endpoint,
                json=event_data,
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"上报失败: {str(e)}")
            raise  # 触发重试

    def safe_report(self, event_data: Dict[str, Any]):
        """安全上报（捕获所有异常，避免影响主程序）"""
        try:
            return self.report_event(event_data)
        except Exception as e:
            logger.error(f"事件上报最终失败: {event_data}")
            return False