import sys
import time

class Logger:
    def _log(self, level: str, message: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [{level}] {message}", flush=True)

    def debug(self, message: str):
        self._log("DEBUG", message)

    def info(self, message: str):
        self._log("INFO", message)

    def warning(self, message: str):
        self._log("WARN", message)

    def error(self, message: str):
        self._log("ERROR", message)

# singleton-style logger, matches `from logger import logger`
logger = Logger()
