from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import sqlite3

app = FastAPI()


class LoginRequest(BaseModel):
    username: str
    password: str

db_path = Path(__file__).parent.parent / "demo.db"

@app.get("/")
async def read_root():
    return FileResponse(Path(__file__).parent / "index.html")

@app.post("/api/login")
async def login(payload: LoginRequest):
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
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT order_no, customer_name, total_amount, status FROM orders LIMIT 10")
        orders = [{"order_id": r[0], "customer": r[1], "amount": r[2], "status": r[3]} for r in cursor.fetchall()]
        conn.close()
        return {"success": True, "data": orders}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
