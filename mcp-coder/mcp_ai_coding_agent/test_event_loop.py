import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

@app.post("/test")
async def test_endpoint():
    try:
        loop = asyncio.get_running_loop()
        return {"status": "success", "loop_exists": True}
    except RuntimeError:
        return {"status": "error", "loop_exists": False, "error": "no running event loop"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)