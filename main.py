import json
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import market, agent, pages
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tasks import (
    continuous_oracle_sync, 
    evaluate_predictions_task, 
    update_social_sentiment_from_datasets,
    continuous_regulatory_monitor,
    continuous_pricing_monitor,
    continuous_alternative_data_sync
)
from dotenv import load_dotenv


load_dotenv()
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

# --- 2. Lifespan with Heartbeat ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()

    print("🚀 [LUCY] Starting Autonomous Brain Loops...")

    # Start autonomous loops
    scheduler.add_job(
        continuous_oracle_sync, 
        'interval', 
        minutes=2,         # 👈 FIX: Changed from 30s to 2m to protect the thread pool
        id='oracle_sync', 
        args=[manager], 
        max_instances=1,   # 👈 FIX: Changed from 3 to 1 to prevent overlapping resource exhaustion
        coalesce=True      # 🛡️ Skips missed runs if the server was down
    )
    scheduler.add_job(
        evaluate_predictions_task, 
        'interval', 
        minutes=5, 
        id='evaluate_predictions', 
        args=[manager],
        max_instances=1,   # 👈 FIX: Dropped to 1 to prevent compounding DB operations
        coalesce=True      # 🛡️ Skips missed runs if the server was down
    )
    scheduler.add_job(
        update_social_sentiment_from_datasets, 
        'interval', 
        hours=6, 
        id='social_sentiment_sync',
        max_instances=1,
        coalesce=True
    )
    scheduler.add_job(
        continuous_regulatory_monitor,
        'interval',
        hours=1,
        id='regulatory_alerts_sync',
        args=[manager],
        max_instances=1,
        coalesce=True
    )
    scheduler.add_job(
        continuous_pricing_monitor,
        'interval',
        hours=12,
        id='competitive_pricing_sync',
        args=[manager],
        max_instances=1,
        coalesce=True
    )
    scheduler.add_job(
        continuous_alternative_data_sync,
        'interval',
        hours=24,
        id='alternative_data_sync',
        args=[manager],
        max_instances=1,
        coalesce=True
    )
    scheduler.start()

    print("✅ [LUCY] Scheduler started successfully.")

    yield
    
    print("🛑 [LUCY] Shutting down scheduler...")
    scheduler.shutdown()

_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Lucy Agent Web3", lifespan=lifespan)

# --- 3. Middleware & Routers (STILL ACTIVE!) ---
_frontend_url = os.getenv("FRONTEND_URL")
_cors_origins = [_frontend_url] if _frontend_url else []
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

# UI (Jinja2 + HTMX) and JSON API
app.include_router(pages.router)
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