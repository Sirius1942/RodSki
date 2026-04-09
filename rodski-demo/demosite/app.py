"""RodSki Demo Site - FastAPI Backend

提供以下页面和 API：
- /             主页 SPA（登录、仪表盘、功能测试）
- /upload       文件上传测试页
- /locator-test 定位器测试页
- /multi-window 多窗口测试页
- /multi-window/popup 弹出窗口
- /iframe-test  iframe 测试页
- /iframe-content iframe 内嵌内容页
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import sqlite3

app = FastAPI(title="RodSki Demo Site")

DEMOSITE_DIR = Path(__file__).parent
db_path = DEMOSITE_DIR.parent / "demo.db"


class LoginRequest(BaseModel):
    username: str
    password: str


# ──────────────────────────────────────────────
# Existing endpoints
# ──────────────────────────────────────────────

@app.get("/")
async def read_root():
    """Serve main SPA (login, dashboard, function test)."""
    return FileResponse(DEMOSITE_DIR / "index.html")


@app.post("/api/login")
async def login(payload: LoginRequest):
    """Handle login. admin/123456 succeeds."""
    if payload.username == "admin" and payload.password == "123456":
        return {
            "success": True,
            "status": 200,
            "data": {"token": "demo_token_123"},
            "message": "登录成功"
        }
    return {"success": False, "status": 401, "message": "用户名或密码错误"}


@app.get("/api/orders")
async def get_orders():
    """Return order list from SQLite."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT order_no, customer_name, total_amount, status FROM orders LIMIT 10"
        )
        orders = [
            {"order_id": r[0], "customer": r[1], "amount": r[2], "status": r[3]}
            for r in cursor.fetchall()
        ]
        conn.close()
        return {"success": True, "data": orders}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}


# ──────────────────────────────────────────────
# New endpoints
# ──────────────────────────────────────────────

@app.get("/upload")
async def upload_page():
    """Serve upload.html."""
    return FileResponse(DEMOSITE_DIR / "upload.html")


@app.post("/api/upload")
async def handle_upload(file: UploadFile = File(...)):
    """Handle file upload, return filename and size."""
    content = await file.read()
    return {
        "success": True,
        "filename": file.filename,
        "size": len(content),
    }


@app.get("/locator-test")
async def locator_test_page():
    """Serve locator_test.html."""
    return FileResponse(DEMOSITE_DIR / "locator_test.html")


@app.get("/multi-window")
async def multi_window_page():
    """Serve multi_window.html."""
    return FileResponse(DEMOSITE_DIR / "multi_window.html")


@app.get("/multi-window/popup")
async def popup_page():
    """Serve popup.html."""
    return FileResponse(DEMOSITE_DIR / "popup.html")


@app.get("/iframe-test")
async def iframe_test_page():
    """Serve iframe_test.html."""
    return FileResponse(DEMOSITE_DIR / "iframe_test.html")


@app.get("/iframe-content")
async def iframe_content_page():
    """Serve iframe_content.html."""
    return FileResponse(DEMOSITE_DIR / "iframe_content.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
