# start.py — robust launcher for Railway
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))  # Railway injects PORT
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)