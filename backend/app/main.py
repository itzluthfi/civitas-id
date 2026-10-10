import asyncio
import sys
import logging
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.pddikti_client import pddikti_client
from .api.pddikti_router import router as pddikti_router
from .api.document_router import router as document_router
from .bot import telegram_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("civitas.main")

bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing CivitasID engine...")
    try:
        await pddikti_client.start()
        logger.info("PDDIKTI client initialized successfully.")
    except Exception as e:
        logger.warning(f"PDDIKTI initial warmup deferred: {e}")

    # Optional Telegram Bot background runner
    if settings.ENABLE_TELEGRAM_BOT and settings.TELEGRAM_BOT_TOKEN:
        logger.info("Launching Telegram Bot background service...")
        global bot_task
        bot_task = asyncio.create_task(telegram_service.start_bot(settings.TELEGRAM_BOT_TOKEN))

    yield

    # Shutdown
    logger.info("Shutting down CivitasID services...")
    if bot_task:
        bot_task.cancel()
    await pddikti_client.stop()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-performance, anti-bot bypassed PDDIKTI lookup & academic document generator suite.",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(pddikti_router)
app.include_router(document_router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "telegram_bot_active": bool(settings.ENABLE_TELEGRAM_BOT and settings.TELEGRAM_BOT_TOKEN)
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
