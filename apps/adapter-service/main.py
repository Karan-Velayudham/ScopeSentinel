import uvicorn
from fastapi import FastAPI
import structlog

from routers import tools, connections, oauth, connectors
from core.connection_manager import connection_manager

logger = structlog.get_logger()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ScopeSentinel Adapter Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tools.router)
app.include_router(connections.router)
app.include_router(oauth.router)
app.include_router(connectors.router)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("adapter_service.shutting_down")
    await connection_manager.close_all()

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
