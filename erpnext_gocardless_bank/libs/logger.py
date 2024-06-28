# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import os
import logging

import frappe


# [Common]
def get_logger(log_type):
    from logging.handlers import RotatingFileHandler
    
    from erpnext_gocardless_bank import __abbr__
    
    if not log_type:
        log_type = "error"
    
    site = getattr(frappe.local, "site", None)
    if not site:
        site = "ERPNext"
    
    key = "{}-{}-{}".format(site, __abbr__, log_type)
    try:
        return frappe.loggers[key]
    except KeyError:
        pass
    
    logfile = "{}-{}.log".format(__abbr__, log_type)
    logfile = os.path.join("..", "logs", logfile)
    logger = logging.getLogger(key)
    logger.setLevel(getattr(logging, log_type.upper(), None) or logging.ERROR)
    logger.propagate = False
    handler = RotatingFileHandler(logfile, maxBytes=500_000, backupCount=20)
    handler.setLevel(getattr(logging, log_type.upper(), None) or logging.ERROR)
    handler.setFormatter(LoggingCustomFormatter())
    logger.addHandler(handler)
    frappe.loggers[key] = logger
    return logger


# [G Settings Form]
@frappe.whitelist()
def get_log_files():
    import glob
    
    from erpnext_gocardless_bank import __abbr__
    
    try:
        ret = []
        path = os.path.join("..", "logs")
        if not path.endswith("/"):
            path = path + "/"
        for f in glob.glob(path + __abbr__ + "-*.log*"):
            ret.append(f.strip("/").split("/")[-1].split(".")[0])
        
        return ret
    except Exception:
        return 0


# [G Settings Form]
@frappe.whitelist(methods=["POST"])
def load_log_file(name):
    if not name or not isinstance(name, str):
        return 0
    
    try:
        path = os.path.join("..", "logs", f"{name}.log")
        if not os.path.exists(path):
            return 0
        
        with open(path, "r") as file:
            data = file.read()
        
        return data
    except Exception:
        return 0


# [G Settings Form]
@frappe.whitelist(methods=["POST"])
def remove_log_file(name):
    if not name or not isinstance(name, str):
        return 0
    
    try:
        path = os.path.join("..", "logs", f"{name}.log")
        if not os.path.exists(path):
            return 0
        
        os.remove(path)
        return 1
    except Exception:
        return 0


# [Internal]
class LoggingCustomFormatter(logging.Formatter):
    def __init__(self):
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        super(LoggingCustomFormatter, self).__init__(fmt)

    def format(self, record):
        return super().format(record)