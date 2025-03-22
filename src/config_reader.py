import os
import configparser
from typing import List, Set
import logging
from logger import get_logger
"""
config.ini

[Settings]
WATCH_PATHS = D:/test_folder1,D:/test_folder2
RECURSIVE = True
IGNORE_EXT = .exe;.mp3

[Logging]
LOG_FILE = logs/file_changes.log  ; 日志文件路径
MAX_SIZE_MB = 10                  ; 单个日志文件最大大小（MB）
BACKUP_COUNT = 3                  ; 保留的备份文件数量
CONSOLE_LEVEL = INFO              ; 控制台日志级别（DEBUG/INFO/WARNING/ERROR） 控制台显示 CONSOLE_LEVEL 级别及以上日志
FILE_LEVEL = INFO                 ; 文件日志级别 文件只记录 INFO 及以上级别
; 新增错误日志专用配置
ERROR_LOG_FILE = logs/errors.log  ; 独立错误日志文件
KEEP_ERROR_DAYS = 30              ; 错误日志保留天数
"""
class ConfigError(Exception):
    """自定义配置异常"""
    pass


def read_config(config_path: str = "config.ini") -> dict:
    """
    读取并解析配置文件
    :return: 包含配置参数的字典
    """
    try:
        config = configparser.ConfigParser()

        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            raise ConfigError(f"配置文件 {config_path} 不存在！")

        config.read(config_path, encoding='utf-8')

        try:
            settings = config["Settings"]
        except KeyError:
            raise ConfigError("配置文件中缺少 [Settings] 段落")

        # 解析监控路径
        watch_paths = []
        if "WATCH_PATHS" in settings:
            raw_paths = settings["WATCH_PATHS"].split(",")
            watch_paths = [p.strip() for p in raw_paths if p.strip()]

        # 解析递归监控选项（默认True）
        recursive = True
        if "RECURSIVE" in settings:
            try:
                recursive = config.getboolean("Settings", "RECURSIVE")
            except ValueError:
                raise ConfigError("RECURSIVE 必须是 true/false, yes/no, on/off, 1/0")

        # 解析忽略的扩展名（转换为小写集合）
        ignore_ext: Set[str] = set()
        if "IGNORE_EXT" in settings:
            raw_ext = settings["IGNORE_EXT"].split(";")
            ignore_ext = {ext.strip().lower() for ext in raw_ext if ext.strip()}
        config_dict={
            "watch_paths": watch_paths,
            "recursive": recursive,
            "ignore_ext": ignore_ext,
            "config_path": os.path.abspath(config_path)
        }

        # 新增日志配置解析
        log_config = {
            "log_file": "file_changes.log",  # 默认值
            "max_bytes": 10 * 1024 * 1024,  # 默认10MB
            "backup_count": 3,
            "console_level": logging.INFO,
            "file_level": logging.INFO,
            "error_log_file":"errors.log",
            "keep_error_days":"30"
        }
        if "Logging" in config:
            log_settings = config["Logging"]

            # 日志文件路径
            if "LOG_FILE" in log_settings:
                log_config["log_file"] = log_settings["LOG_FILE"].strip()

            # 最大文件大小（MB转字节）
            if "MAX_SIZE_MB" in log_settings:
                try:
                    max_mb = int(log_settings["MAX_SIZE_MB"])
                    log_config["max_bytes"] = max_mb * 1024 * 1024
                except ValueError:
                    raise ConfigError("MAX_SIZE_MB 必须是整数")

            # 备份数量
            if "BACKUP_COUNT" in log_settings:
                try:
                    log_config["backup_count"] = int(log_settings["BACKUP_COUNT"])
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
            if "CONSOLE_LEVEL" in log_settings:
                console_level = log_settings["CONSOLE_LEVEL"].upper()
                if console_level not in level_map:
                    raise ConfigError(f"无效的CONSOLE_LEVEL: {console_level}")
                log_config["console_level"] = level_map[console_level]

            # 文件日志级别
            if "FILE_LEVEL" in log_settings:
                file_level = log_settings["FILE_LEVEL"].upper()
                if file_level not in level_map:
                    raise ConfigError(f"无效的FILE_LEVEL: {file_level}")
                log_config["file_level"] = level_map[file_level]
            #错误日志路径
            if "ERROR_LOG_FILE" in log_settings:
                log_config["error_log_file"] = log_settings["ERROR_LOG_FILE"].strip()
            #错误日志保留天数
            if "KEEP_ERROR_DAYS" in log_settings:
                try:
                    log_config["keep_error_days"] = int(log_settings["KEEP_ERROR_DAYS"])
                except ValueError:
                    raise ConfigError("KEEP_ERROR_DAYS 必须是整数")

        # 合并到返回字典
        config_dict.update(log_config)

        #客户端相关配置
        config_dict["api_endpoint"] = config.get("Remote", "API_ENDPOINT")
        config_dict["api_key"] = config.get("Remote", "API_KEY")
        config_dict["max_retries"] = config.getint("Remote", "MAX_RETRIES", fallback=3)

        return config_dict
    except (ConfigError, PermissionError) as e:
        logger = get_logger("ConfigReader")
        logger.error("配置文件加载失败", exc_info=True)
        raise  # 将异常抛给上层处理

if __name__ == "__main__":
    print(read_config())