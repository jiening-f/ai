"""
游戏全能脚本 — 桌面版启动器
双击此 exe 直接打开桌面窗口，无需浏览器
"""
import os
import sys
import threading
import urllib.request

def start_server():
    """启动后端服务"""
    from server import app
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")

def wait_for_server():
    """等待服务就绪"""
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=1)
            return True
        except:
            import time
            time.sleep(0.5)
    return False

def main():
    # 启动后端线程
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    if not wait_for_server():
        print("服务启动失败")
        return

    import webview
    # 创建原生桌面窗口
    webview.create_window(
        title="游戏全能脚本",
        url="http://127.0.0.1:8765/page-basic/",
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
        text_select=True,
    )
    webview.start()

if __name__ == "__main__":
    main()
