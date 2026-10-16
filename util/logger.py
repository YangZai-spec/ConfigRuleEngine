import os
import sys
import inspect
import logging


_LOGGERS = {}


def get_logger(loggernamespace=None, logfilename='cfg_checker.log', log_path=None):
    """
    获取 logger 日志对象（同名 logger 全局复用）。

    日志格式中会输出调用脚本名（[脚本名]）。
    - 若显式传入 loggernamespace，则使用该值作为脚本名标识；
    - 若未传入，则自动获取调用 get_logger 的那个脚本的文件名（不含扩展名）作为脚本名。
    - 控制台仅输出 WARNING 及以上级别，INFO 及以上全量写入项目 logs/ 目录下的日志文件。
    """
    if loggernamespace is None:
        # 自动取调用 get_logger 的那个脚本的文件名（不含扩展名）作为脚本名
        frame = inspect.stack()[1]
        loggernamespace = os.path.splitext(os.path.basename(frame.filename))[0]

    if loggernamespace in _LOGGERS:
        return _LOGGERS[loggernamespace]

    # 使用项目目录下的 logs 文件夹
    if log_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)  # 从 util 目录向上一级到项目目录
        log_path = os.path.join(project_dir, 'logs')

    # 确保 logs 目录存在
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    filename = os.path.join(log_path, logfilename)
    log = logging.getLogger(loggernamespace)
    log.setLevel(logging.INFO)
    # 在日志中输出调用脚本名：[%(name)s]
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.WARNING)
    file_handler = logging.FileHandler(filename,
                                       mode='a',
                                       encoding='utf-8',
                                       delay=False)
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)
    log.addHandler(console_handler)
    log.addHandler(file_handler)
    _LOGGERS[loggernamespace] = log
    return log
