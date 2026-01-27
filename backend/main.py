from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import market, agent
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler

# This is our "Automatic Sync" manager
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 5th Function: The Auto-Scheduler ---
    # Add the sync task for BTC and ETH to run every 60 seconds
    scheduler.add_job(market.sync_oracle_task, 'interval', seconds=60, args=["BTC"])
    scheduler.add_job(market.sync_oracle_task, 'interval', seconds=60, args=["ETH"])
    
    scheduler.start()
    print("🚀 Automatic Oracle Sync Started (Every 60s)")
    
    yield  # Server runs here...
    
    scheduler.shutdown()
    print("🛑 Scheduler Shut Down")

app = FastAPI(title="QuotePlot Agent Web3", lifespan=lifespan)

# Important: Allow your Next.js frontend (port 3000) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect the routers
app.include_router(market.router)
app.include_router(agent.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)