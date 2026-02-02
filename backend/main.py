import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import market, agent
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# This is our "Automatic Sync" manager
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the global client
    global market_client
    market.http_client = httpx.AsyncClient()
    yield
    # Shutdown gracefully
    await market.http_client.aclose()

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