from loguru import logger
import sys


logger.remove()
logger.add(
    sys.stderr,
    format="{time} {level} {file}:{line} {message}",
    level="INFO"
)
logger.add(
    "bot.log",
    format="{time} {level} {file}:{line} {message}",
    level="DEBUG",
    rotation="10 MB",
    compression="zip"
)


def get_logger():
    return logger