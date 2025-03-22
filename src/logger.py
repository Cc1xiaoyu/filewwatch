import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional

"""
说明：
日志模块化：
    所有日志配置集中在 logger.py
    支持日志轮转（单个文件最大10MB，保留3个备份）
    分离控制台和文件日志格式
日志分级：
    内置 DEBUG/INFO/WARNING/ERROR 分级
    可通过 setup_logger() 参数调整日志级别
多日志记录器：
    使用 get_logger("FileMonitor.Handler") 创建层级化日志
    便于后续过滤不同模块的日志
异常处理增强：
    自动创建日志文件目录
    移除已有处理器避免重复日志

所有 WARNING 及以上级别的日志会额外写入 errors.log
三类处理器并行：

处理器类型	输出目标	            日志级别	                轮转策略
控制台处理器	标准输出	            由 console_level 控制	无
主文件处理器	file_changes.log	由 file_level 控制	    按大小轮转（默认10MB）
错误日志处理器	errors.log	        固定为 WARNING+	        按天轮转，保留指定天数

"""
def setup_logger(config: dict) -> None:
    """
    配置全局日志记录器
    :param config: 根据配置字典初始化日志
    :return:
    """
    # 根据配置字典初始化日志
    log_file = config.get("log_file", "file_changes.log")
    max_bytes = config.get("max_bytes", 10 * 1024 * 1024)#默认10MB
    backup_count = config.get("backup_count", 3)
    console_level = config.get("console_level", logging.INFO)
    file_level = config.get("file_level", logging.INFO)
    error_log_file=config.get("error_log_file","errors.log")
    keep_error_days = config.get("keep_error_days", 30)
    #创建全局日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 设置全局最低级别

    # 确保日志目录存在 -------------------------------------------------
    def ensure_dir(file_path: str) -> None:
        """递归创建日志文件所需的目录"""
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    for path in [log_file, error_log_file]:
        ensure_dir(path)
    # 定义日志格式器 --------------------------------------------------
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    # 清除已有处理器（避免重复添加） -------------------------------------
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 控制台处理器（所有级别） ------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    # 主日志文件处理器（轮转方式） ---------------------------------------
    main_file_handler  = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    main_file_handler.setLevel(file_level)
    main_file_handler.setFormatter(file_formatter)
    logger.addHandler(main_file_handler)

    # 错误日志专用处理器（按时间轮转） ------------------------------------
    error_file_handler = TimedRotatingFileHandler(
        filename=error_log_file,
        when='midnight',  # 每天轮转
        interval=1,
        backupCount=keep_error_days,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.WARNING)  # 只记录WARNING及以上级别
    error_file_handler.setFormatter(file_formatter)
    logger.addHandler(error_file_handler)
    # 全局未捕获异常处理 -----------------------------------------------
    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        """捕获所有未处理的异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 忽略键盘中断
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.error(
            "未捕获的全局异常",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_uncaught_exception

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return logging.getLogger(name)

def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    """全局未捕获异常处理"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 忽略键盘中断
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = get_logger("UnhandledException")
    logger.critical(
        "未捕获的异常",
        exc_info=(exc_type, exc_value, exc_traceback)
    )