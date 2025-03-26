import os
import configparser
from typing import Dict, Any,List, Set
import logging
from logger import get_logger
"""
config.ini

[Settings]
WATCH_PATHS = D:/test_folder1,D:/test_folder2
RECURSIVE = True
IGNORE_EXT = .exe;.mp3

[Remote]
API_ENDPOINT = http://192.168.30.129:8000/api/events    ;远程API地址
API_KEY = your-secret-key-123                           ;密钥
MAX_RETRIES = 3                                         ;重试次数

[Logging]
LOG_FILE = logs/file_changes.log  ; 日志文件路径
MAX_SIZE_MB = 10                  ; 单个日志文件最大大小（MB）
BACKUP_COUNT = 3                  ; 保留的备份文件数量
CONSOLE_LEVEL = INFO              ; 控制台日志级别（DEBUG/INFO/WARNING/ERROR） 控制台显示 CONSOLE_LEVEL 级别及以上日志
FILE_LEVEL = INFO                 ; 文件日志级别 文件只记录 INFO 及以上级别
; 新增错误日志专用配置
ERROR_LOG_FILE = logs/errors.log  ; 独立错误日志文件
KEEP_ERROR_DAYS = 30              ; 错误日志保留天数

[Heartbeat]
INTERVAL_SECONDS = 30; 心跳间隔（秒）
TIMEOUT_SECONDS = 90; 服务端超时阈值（秒）

"""
class ConfigError(Exception):
    """自定义配置异常"""
    pass


def read_config(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    读取并解析配置文件，返回配置字典
    :param config_path: 配置文件路径
    :return: 包含配置参数的字典
    """
    try:
        config = configparser.ConfigParser()

        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            raise ConfigError(f"配置文件 {config_path} 不存在！")

        config.read(config_path, encoding='utf-8')

        config_dict: Dict[str, Any] = {}

        # ---------------------- 解析 [Settings] ----------------------
        try:
            settings = config["Settings"]
        except KeyError:
            raise ConfigError("配置文件中缺少 [Settings] 段落")

        # 解析监控路径

        config_dict["watch_paths"] = []
        if "WATCH_PATHS" in settings:
            raw_paths = settings["WATCH_PATHS"].split(",")
            config_dict["watch_paths"] = [p.strip() for p in raw_paths if p.strip()]

        # 解析递归监控选项（默认True）
        config_dict["recursive"] = True
        if "RECURSIVE" in settings:
            try:
                config_dict["recursive"] = config.getboolean("Settings", "RECURSIVE")
            except ValueError:
                raise ConfigError("RECURSIVE 必须是 true/false, yes/no, on/off, 1/0")

        # 解析忽略的扩展名（转换为小写集合）
        config_dict["ignore_ext"] = set()
        if "IGNORE_EXT" in settings:
            raw_ext = settings["IGNORE_EXT"].split(";")
            config_dict["ignore_ext"] = {ext.strip().lower() for ext in raw_ext if ext.strip()}

        # ---------------------- 解析 [Remote/服务器 and 客户端] ----------------------
        config_dict["api_endpoint"] = None
        config_dict["api_key"] = ""
        if "Remote" in config:
            remote = config["Remote"]

            # API 端点
            if "API_ENDPOINT" in remote:
                config_dict["api_endpoint"] = remote["API_ENDPOINT"].strip()

            # API 密钥
            if "API_KEY" in remote:
                config_dict["api_key"] = remote["API_KEY"].strip()

            # 最大重试次数
            config_dict["max_retries"] = 3
            if "MAX_RETRIES" in remote:
                try:
                    config_dict["max_retries"] = int(remote["MAX_RETRIES"])
                except ValueError:
                    raise ConfigError("MAX_RETRIES 必须是整数")
        # ---------------------- 解析 [Logging] ----------------------
        # 新增日志配置解析
        config_dict["log_file"] = "file_changes.log"
        config_dict["error_log_file"] = "errors.log"
        config_dict["max_bytes"] = 10 * 1024 * 1024  # 默认10MB
        config_dict["backup_count"] = 3
        config_dict["console_level"] = logging.INFO
        config_dict["file_level"] = logging.INFO
        config_dict["keep_error_days"] = 30
        if "Logging" in config:
            logging_section = config["Logging"]

            # 主日志文件路径
            if "LOG_FILE" in logging_section:
                config_dict["log_file"] = logging_section["LOG_FILE"].strip()
            # 错误日志文件路径
            if "ERROR_LOG_FILE" in logging_section:
                config_dict["error_log_file"] = logging_section["ERROR_LOG_FILE"].strip()

            # 最大文件大小（MB转字节）
            if "MAX_SIZE_MB" in logging_section:
                try:
                    max_mb = int(logging_section["MAX_SIZE_MB"])
                    config_dict["max_bytes"] = max_mb * 1024 * 1024
                except ValueError:
                    raise ConfigError("MAX_SIZE_MB 必须是整数")

            # 备份数量
            if "BACKUP_COUNT" in logging_section:
                try:
                    config_dict["backup_count"] = int(logging_section["BACKUP_COUNT"])
                except ValueError:
                    raise ConfigError("BACKUP_COUNT 必须是整数")

            # 日志级别映射
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR
            }

            # 控制台日志级别
            if "CONSOLE_LEVEL" in logging_section:
                console_level = logging_section["CONSOLE_LEVEL"].upper()
                if console_level not in level_map:
                    raise ConfigError(f"无效的CONSOLE_LEVEL: {console_level}")
                config_dict["console_level"] = level_map[console_level]

            # 文件日志级别
            if "FILE_LEVEL" in logging_section:
                file_level = logging_section["FILE_LEVEL"].upper()
                if file_level not in level_map:
                    raise ConfigError(f"无效的FILE_LEVEL: {file_level}")
                config_dict["file_level"] = level_map[file_level]

            # 错误日志保留天数
            if "KEEP_ERROR_DAYS" in logging_section:
                try:
                    config_dict["keep_error_days"] = int(logging_section["KEEP_ERROR_DAYS"])
                except ValueError:
                    raise ConfigError("KEEP_ERROR_DAYS 必须是整数")

        # ---------------------- 解析 [Heartbeat] ----------------------
        config_dict["heartbeat_interval"] = 30
        config_dict["heartbeat_timeout"] = 90

        if "Heartbeat" in config:
            heartbeat = config["Heartbeat"]

            if "INTERVAL_SECONDS" in heartbeat:
                try:
                    config_dict["heartbeat_interval"] = int(heartbeat["INTERVAL_SECONDS"])
                except ValueError:
                    raise ConfigError("HEARTBEAT_INTERVAL 必须是整数")

            if "TIMEOUT_SECONDS" in heartbeat:
                try:
                    config_dict["heartbeat_timeout"] = int(heartbeat["TIMEOUT_SECONDS"])
                except ValueError:
                    raise ConfigError("HEARTBEAT_TIMEOUT 必须是整数")

        # 添加配置文件绝对路径
        config_dict["config_path"] = os.path.abspath(config_path)

        return config_dict

    except (ConfigError, PermissionError) as e:
        logger = get_logger("ConfigReader")
        logger.error("配置文件加载失败", exc_info=True)
        raise  # 将异常抛给上层处理

if __name__ == "__main__":
    print(read_config())