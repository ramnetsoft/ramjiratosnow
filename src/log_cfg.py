import logging
import os
import sys
from settings import get_log_level
"""
All lambda methods use this loging config.
Provides a single place where all log config/level/formatting is setup so that one
can see source file, line numbers, and any other desired log fields. 
"""

logger = logging.getLogger()
for h in logger.handlers:
    logger.removeHandler(h)
h = logging.StreamHandler(sys.stdout)
# use whatever format you want here
FORMAT = '%(asctime)-15s %(process)d-%(thread)d %(name)s [%(filename)s:%(lineno)d] :%(levelname)8s: %(message)s'
h.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(h)
logger.setLevel(get_log_level())
# Suppress the more verbose modules
logging.getLogger('__main__').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.WARN)

