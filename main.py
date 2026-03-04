import uvicorn
from web.api import app
from core.common.db import init_db

# 初始化数据库
init_db()

if __name__ == "__main__":
    # 启动FastAPI服务，默认端口8000
    uvicorn.run(app, host="0.0.0.0", port=8000)