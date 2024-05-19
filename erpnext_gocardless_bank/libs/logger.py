# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import os
import logging
from logging.handlers import RotatingFileHandler

import frappe

from erpnext_gocardless_bank import __abbr__


# [Common]
def get_logger(logType):
    if not logType:
        logType = "error"
    site = getattr(frappe.local, "site", None)
    if not site:
        site = "ERPNext"
    
    logger_name = "{}-{}-{}".format(__abbr__, site, logType)
    
    try:
        return frappe.loggers[logger_name]
    except KeyError:
        pass
    
    logfile = "{}-{}.log".format(__abbr__, logType)
    logfile = os.path.join("..", "logs", logfile)
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, logType.upper(), None) or logging.ERROR)
    logger.propagate = False
    handler = RotatingFileHandler(logfile, maxBytes=100_000, backupCount=20)
    handler.setLevel(getattr(logging, logType.upper(), None) or logging.ERROR)
    handler.setFormatter(LoggingCustomFormatter())
    logger.addHandler(handler)
    frappe.loggers[logger_name] = logger
    return logger


# [G Settings Form]
@frappe.whitelist(methods=["GET"])
def get_log_files():
    import glob
    
    ret = []
    exp = "{}-*.log*".format(__abbr__)
    path = os.path.join("..", "logs")
    if not path.endswith("/"):
        path = path + "/"
    for files in glob.glob(path + exp):
        for f in files:
            ret.append(f.strip("/").split("/")[-1])
    
    return ret


# [G Settings Form]
@frappe.whitelist(methods=["POST"])
def load_log_file(filename):
    if (
        not filename or
        not isinstance(filename, str) or
        not filename.startswith(__abbr__)
    ):
        return 0
    
    path = os.path.join("..", "logs", filename)
    if not os.path.exists(path):
        return ""
    
    with open(path, "r") as file:
        data = file.read()
    
    return data


# [G Settings Form]
@frappe.whitelist(methods=["POST"])
def remove_log_file(filename):
    if (
        not filename or
        not isinstance(filename, str) or
        not filename.startswith(__abbr__)
    ):
        return 0
    
    path = os.path.join("..", "logs", filename)
    if not os.path.exists(path):
        return 0
    
    os.remove(path)
    return 1


# [Internal]
class LoggingCustomFormatter(logging.Formatter):
    def __init__(self):
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        super(LoggingCustomFormatter, self).__init__(fmt)

    def format(self, record):
        return super().format(record)