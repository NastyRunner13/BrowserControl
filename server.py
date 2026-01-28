from contextlib import asynccontextmanager
from collections import defaultdict
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import router
from api.manager import job_manager
from core.browser_pool import BrowserPool
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("api_server")

# Simple in-memory rate limiter
class RateLimiter:
    """Simple in-memory rate limiter."""
    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.clients: dict = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request from client_ip is allowed."""
        now = time.time()
        # Clean old entries
        self.clients[client_ip] = [
            t for t in self.clients[client_ip] 
            if now - t < self.window_seconds
        ]
        # Check rate
        if len(self.clients[client_ip]) >= self.requests_per_window:
            return False
        self.clients[client_ip].append(now)
        return True

rate_limiter = RateLimiter(
    settings.RATE_LIMIT_REQUESTS, 
    settings.RATE_LIMIT_WINDOW_SECONDS
)

@asynccontextmanager
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

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting if enabled."""
    if settings.RATE_LIMIT_ENABLED:
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
    return await call_next(request)

# CORS Configuration - Use settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
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