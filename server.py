from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.manager import job_manager
from core.browser_pool import BrowserPool
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("api_server")

asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the API with job cleanup.
    """
    # STARTUP
    logger.info("🚀 Starting BrowserControl API...")
    
    # Initialize browser pool
    pool = BrowserPool(
        max_browsers=settings.MAX_BROWSERS,
        headless=settings.HEADLESS
    )
    
    try:
        await pool.initialize()
        app.state.browser_pool = pool
        logger.info("✅ Browser Pool initialized and ready.")
        
        # NEW: Start job cleanup loop
        await job_manager.start_cleanup_loop()
        logger.info("✅ Job cleanup loop started")
        
        yield  # Application runs here
        
    finally:
        # SHUTDOWN
        logger.info("🛑 Shutting down BrowserControl API...")
        
        # NEW: Stop cleanup loop first
        await job_manager.stop_cleanup_loop()
        logger.info("✅ Job cleanup loop stopped")
        
        await pool.cleanup()
        logger.info("✅ Browser Pool cleaned up.")

app = FastAPI(
    title="BrowserControl API",
    description="Enterprise-grade AI Browser Automation API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint that also reports pool stats."""
    pool: BrowserPool = app.state.browser_pool
    return {
        "status": "healthy",
        "pool_stats": pool.get_stats()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)