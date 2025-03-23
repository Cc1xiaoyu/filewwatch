"""
对文件夹进行监视
"""

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logger import setup_logger, get_logger
import logging
import os
import socket
from config_reader import read_config, ConfigError  #配置文件读取
from client.api_client import APIClient         #客户端处理
from datetime import datetime

# 在类外初始化日志
logging.basicConfig(
    filename='file_changes.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, ignore_ext: set, api_client: APIClient, host_id: str):
        super().__init__()
        self.ignore_ext = ignore_ext
        self.logger = get_logger("FileMonitor.Handler")  # 获取日志记录器
        self.api_client = api_client
        self.host_id = host_id  # 客户端唯一标识（可配置）

    def _should_ignore(self, path: str) -> bool:
        """检查文件扩展名是否需要忽略"""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.ignore_ext

    def on_modified(self, event):
        try:
            if not event.is_directory and not self._should_ignore(event.src_path):  # 过滤目录事件
                # print(f"[Modified]  {event.src_path}")
                self.logger.info(f"[Modified] \t{event.src_path}")#日志输出
                #上传
                event_data = self._create_event_data("modified", event.src_path)
                self.api_client.safe_report(event_data)
        except Exception as e:
            self.logger.error(f"处理修改事件失败: {event.src_path}", exc_info=True)

    def on_created(self, event):
        if not self._should_ignore(event.src_path):
            # print(f"[Created] {event.src_path}")
            self.logger.info(f"[Created] \t{event.src_path}")# 日志输出
            # 上传
            event_data = self._create_event_data("created", event.src_path)
            self.api_client.safe_report(event_data)

    def on_deleted(self, event):
        if not self._should_ignore(event.src_path):
            # print(f"[Deleted]  {event.src_path}")
            self.logger.info(f"[Deleted/Moved Out] \t{event.src_path}")# 日志输出
            # 上传
            event_data = self._create_event_data("deleted/moved out", event.src_path)
            self.api_client.safe_report(event_data)

    def on_moved(self, event):
        if not self._should_ignore(event.src_path):
            # print(f"[Moved/Rename] {event.src_path} -> {event.dest_path}")
            self.logger.info(f"[Moved] \t{event.src_path} -> {event.dest_path}")# 日志输出
            # 上传
            event_data = self._create_event_data("moved", event.src_path,event.dest_path)
            self.api_client.safe_report(event_data)

    def _create_event_data(self, event_type: str, src_path: str, dest_path: str = None):
        """构造事件数据字典 传递给服务器的数据结构"""
        return {
            "host": self.host_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "path": src_path,
            "dest_path": dest_path
        }

if __name__ == "__main__":
    # 初始化日志（需要先读取配置）
    try:
        config = read_config()
        setup_logger(config)  # 传入配置字典
        logger = get_logger("FileMonitor")
        logger.info(f"成功加载配置文件：{config['config_path']}")

    except ConfigError as e:
        print(f"\033[31m配置错误：{e}\033[0m")
        exit(1)

    # 初始化 API 客户端
    api_client = APIClient(
        endpoint=config["api_endpoint"],# 例如http://192.168.30.129:8000/api/events 传输的路由
        api_key=config["api_key"],      #认证key
        max_retries=config["max_retries"]#最大重传次数
    )

    # 创建事件处理器（添加 host_id 和 api_client）
    host_id = os.environ.get("HOST_ID", socket.gethostname())  # 使用主机名作为默认ID
    event_handler = FileChangeHandler(
        ignore_ext=config["ignore_ext"],
        api_client=api_client,  #客户端实例
        host_id=host_id
    )

    # 路径合法性检查
    valid_paths = []
    for path in config["watch_paths"]:
        if os.path.exists(path):
            valid_paths.append(os.path.abspath(path))
        else:
            print(f"\033[33m警告：路径 '{path}' 不存在，已跳过！\033[0m")
            logging.warning(f"!!!警告!!!目标路径不存在:{path}")  # 日志输出

    if not valid_paths:
        print("\033[31m错误：没有有效的监控路径！\033[0m")
        exit(1)

    # 初始化监控器
    observer = Observer()

    # 添加监控路径
    for path in valid_paths:
        observer.schedule(
            event_handler,
            path,
            recursive=config["recursive"]
        )
        print(f"监控路径：{path} (递归：{config['recursive']})")
    observer.start()
    print("监控已启动...")

    try:
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("监控循环异常", exc_info=True)
        raise
    except KeyboardInterrupt:
        observer.stop()
        print("\n监控已停止。")
    observer.join()