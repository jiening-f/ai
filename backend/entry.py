"""
启动入口 — 异常捕获 + 崩溃日志
"""
import sys
import os
import traceback
from datetime import datetime

def main():
    try:
        import server
        import uvicorn
        print("服务启动: http://127.0.0.1:8765")
        uvicorn.run(server.app, host="127.0.0.1", port=8765)
    except Exception:
        log_dir = os.environ.get("TEMP", os.path.expanduser("~"))
        log_file = os.path.join(log_dir, "ai-game-tool-startup.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"崩溃时间: {datetime.now()}\n")
            f.write(traceback.format_exc())
        print(f"启动失败，日志已写入: {log_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()
