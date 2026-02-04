import httpx
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routers import market, agent
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tasks import continuous_oracle_sync, evaluate_predictions_task

# --- 1. WebSocket Manager for the Thought Stream ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # Sending a structured JSON "thought"
        payload = json.dumps({"type": "thought", "content": message})
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except:
                pass # Handle stale connections safely

manager = ConnectionManager()
scheduler = AsyncIOScheduler()

# --- 2. Lifespan with Heartbeat ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start autonomous loops
    scheduler.add_job(
        continuous_oracle_sync, 
        'interval', 
        seconds=30, 
        id='oracle_sync', 
        args=[manager], 
        max_instances=3, # 🛡️ Prevents overlapping runs
        coalesce=True    # 🛡️ Skips missed runs if the server was down
    )
    scheduler.add_job(
        evaluate_predictions_task, 
        'interval', 
        minutes=5, 
        id='evaluate_predictions', 
        args=[manager],
        max_instances=3, # 🛡️ Prevents overlapping runs
        coalesce=True    # 🛡️ Skips missed runs if the server was down
    )
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(title="Lucy Agent Web3", lifespan=lifespan)

# --- 3. Middleware & Routers (STILL ACTIVE!) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# User can still hit these for questions/data
app.include_router(market.router)
app.include_router(agent.router)

# --- 4. The Live WebSocket Log Endpoint ---
@app.websocket("/ws/thoughts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep the connection open
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)