#!/usr/bin/env python
# -*- encoding=utf8 -*-
import logging
import logging.handlers
import os

# 确保日志文件在项目根目录下的 logs 文件夹中
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILENAME = os.path.join(LOG_DIR, 'app.log') # 统一日志文件名

logger = logging.getLogger()

def set_logger():
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(filename)s [line:%(lineno)d] '
                                  '- %(levelname)s - %(process)d: %(message)s')

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出，使用 RotatingFileHandler 实现日志轮转
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, maxBytes=10485760, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

set_logger()
