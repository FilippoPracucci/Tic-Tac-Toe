import logging


logging.basicConfig(level=logging.DEBUG)
def logger(name: str) -> logging.Logger:
    return logging.getLogger(f"[{name}]")
