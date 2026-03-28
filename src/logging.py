import os
import sys

from loguru import logger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "1") == "1"
LOG_TO_CONSOLE = os.environ.get("LOG_TO_CONSOLE", "1") == "1"


def _init_logger():
    logger.remove()

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    if LOG_TO_FILE:
        os.makedirs("log", exist_ok=True)
        logger.add(
            "log/app.log",
            level=LOG_LEVEL,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            format=fmt,
            backtrace=True,
            diagnose=True,
        )

    if LOG_TO_CONSOLE:
        logger.add(sys.stderr, level=LOG_LEVEL, format=fmt, backtrace=True, diagnose=True)


_init_logger()
