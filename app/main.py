"""
Telegram Football Manager - FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, set_request_id, clear_request_id
from app.core.database import init_db, close_db, check_db_health
from app.core.cache import init_cache, close_cache, get_redis_client
from app.api.routes import api_router
from app.api.websocket import handle_match_websocket
from app.utils.exceptions import TFMException

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    try:
        # Initialize database
        logger.info("Initializing database connections...")
        await init_db()
        
        # Initialize Redis cache
        logger.info("Initializing Redis cache...")
        await init_cache()
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    
    try:
        # Close database connections
        logger.info("Closing database connections...")
        await close_db()
        
        # Close Redis connections
        logger.info("Closing Redis connections...")
        await close_cache()
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Telegram Football Manager game - A simplified 2D Football Manager running as a Telegram Web App",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS - allow all origins for development. We use a regex to
# allow ANY origin (including `file://` which browsers report as the
# string "null"), and we set allow_credentials=False to satisfy the
# browser's wildcard rule.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request ID and timing middleware
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """
    Add request ID tracking and process time measurement to all requests.
    
    This middleware:
    1. Generates or extracts request ID for tracing
    2. Sets request ID in logging context
    3. Measures request processing time
    4. Adds headers to response (X-Request-ID, X-Process-Time)
    5. Logs request completion with timing
    """
    # Generate or extract request ID
    request_id = request.headers.get("X-Request-ID") or set_request_id()
    
    # Set request ID in context for logging
    set_request_id(request_id)
    
    # Log request start
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
        }
    )
    
    try:
        # Process request and measure time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request completion
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            }
        )
        
        return response
    
    except Exception as e:
        # Log request error
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
            },
            exc_info=True
        )
        raise
    
    finally:
        # Clear request ID from context
        clear_request_id()


# Exception handlers
@app.exception_handler(TFMException)
async def tfm_exception_handler(request: Request, exc: TFMException):
    """Handle custom TFM exceptions"""
    logger.error(f"TFM Exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors(),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        }
    )


# Include API routes
app.include_router(api_router)

# Include WebSocket router
from app.api.ws_router import router as ws_router
app.include_router(ws_router)


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_healthy = await check_db_health()
        
        # Check Redis connection
        redis = await get_redis_client()
        await redis.ping()
        cache_healthy = True
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "error": str(e),
            }
        )
    
    # Determine overall health status
    overall_healthy = db_healthy and cache_healthy
    status_code = 200 if overall_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": "healthy" if db_healthy else "unhealthy",
            "cache": "healthy" if cache_healthy else "unhealthy",
        }
    )


# WebSocket endpoint for match streaming
@app.websocket("/ws/match/{match_id}")
async def websocket_match_endpoint(websocket: WebSocket, match_id: str):
    """
    WebSocket endpoint for real-time match event streaming
    
    Args:
        websocket: WebSocket connection
        match_id: Match ID to stream
    """
    redis = await get_redis_client()
    
    try:
        await handle_match_websocket(websocket, match_id, redis)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for match {match_id}")
    except Exception as e:
        logger.error(f"WebSocket error for match {match_id}: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
