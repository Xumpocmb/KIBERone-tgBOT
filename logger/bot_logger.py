import logging.config
from logging import getLogger
import json

with open('logger/logging.conf') as file:
    config = json.load(file)

logging.config.dictConfig(config)
logger = getLogger(__name__)
