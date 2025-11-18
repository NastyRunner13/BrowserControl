import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings and configuration."""
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Validation on load
    if not GROQ_API_KEY or "your_groq_api_key" in GROQ_API_KEY:
        # Don't raise error on import to allow testing, but warn loudly
        print("WARNING: GROQ_API_KEY is not set or invalid in .env")
    
    # Browser Configuration
    MAX_BROWSERS = int(os.getenv("MAX_BROWSERS", "5"))
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    
    # LLM Configuration
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    
    # Execution Configuration
    DEFAULT_TASK_TIMEOUT = int(os.getenv("DEFAULT_TASK_TIMEOUT", "300"))
    DEFAULT_RETRY_COUNT = int(os.getenv("DEFAULT_RETRY_COUNT", "3"))
    INTELLIGENCE_RATIO = float(os.getenv("INTELLIGENCE_RATIO", "0.3"))
    
    # Paths
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")
    LOG_DIR = os.getenv("LOG_DIR", "./logs")

settings = Settings()