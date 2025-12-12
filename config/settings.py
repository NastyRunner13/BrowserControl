import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings and configuration with validation."""
    
    # ==========================================
    # API KEYS
    # ==========================================
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # ==========================================
    # BROWSER CONFIGURATION
    # ==========================================
    MAX_BROWSERS = int(os.getenv("MAX_BROWSERS", "5"))
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    
    # ==========================================
    # LLM CONFIGURATION
    # ==========================================
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    
    # Vision LLM
    VISION_MODEL = os.getenv("VISION_MODEL", "llama-3.2-90b-vision-preview")
    VISION_ENABLED = os.getenv("VISION_ENABLED", "false").lower() == "true"
    
    # Supported vision models
    SUPPORTED_VISION_MODELS = [
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview"
    ]
    
    # ==========================================
    # EXECUTION CONFIGURATION
    # ==========================================
    DEFAULT_TASK_TIMEOUT = int(os.getenv("DEFAULT_TASK_TIMEOUT", "300"))
    DEFAULT_RETRY_COUNT = int(os.getenv("DEFAULT_RETRY_COUNT", "3"))
    INTELLIGENCE_RATIO = float(os.getenv("INTELLIGENCE_RATIO", "0.3"))
    
    # ==========================================
    # NEW FEATURES CONFIGURATION
    # ==========================================
    
    # Dynamic Agent
    ENABLE_DYNAMIC_AGENT = os.getenv("ENABLE_DYNAMIC_AGENT", "true").lower() == "true"
    MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "50"))
    AGENT_HISTORY_LENGTH = int(os.getenv("AGENT_HISTORY_LENGTH", "5"))
    
    # Self-Correction
    ENABLE_SELF_CORRECTION = os.getenv("ENABLE_SELF_CORRECTION", "true").lower() == "true"
    MAX_CORRECTION_ATTEMPTS = int(os.getenv("MAX_CORRECTION_ATTEMPTS", "2"))
    
    # Vision Settings
    ENABLE_VISION_FALLBACK = os.getenv("ENABLE_VISION_FALLBACK", "true").lower() == "true"
    VISION_CACHE_ENABLED = os.getenv("VISION_CACHE_ENABLED", "true").lower() == "true"
    VISION_MAX_MARKERS = int(os.getenv("VISION_MAX_MARKERS", "50"))
    
    # Persistent Context
    ENABLE_PERSISTENT_CONTEXT = os.getenv("ENABLE_PERSISTENT_CONTEXT", "false").lower() == "true"
    STORAGE_STATE_PATH = os.getenv("STORAGE_STATE_PATH", "./storage_state.json")
    
    # Cost Control
    MAX_LLM_CALLS_PER_TASK = int(os.getenv("MAX_LLM_CALLS_PER_TASK", "100"))
    
    # ==========================================
    # PATHS
    # ==========================================
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")
    LOG_DIR = os.getenv("LOG_DIR", "./logs")
    
    # ==========================================
    # FEATURE FLAGS
    # ==========================================
    @staticmethod
    def get_feature_flags() -> dict:
        """Get current feature flag status."""
        return {
            "vision_enabled": Settings.VISION_ENABLED,
            "dynamic_agent": Settings.ENABLE_DYNAMIC_AGENT,
            "self_correction": Settings.ENABLE_SELF_CORRECTION,
            "persistent_context": Settings.ENABLE_PERSISTENT_CONTEXT,
            "vision_fallback": Settings.ENABLE_VISION_FALLBACK
        }
    
    # ==========================================
    # ENHANCED VALIDATION
    # ==========================================
    @staticmethod
    def validate_configuration():
        """Validate critical configuration settings."""
        errors = []
        warnings = []
        
        # 1. Check API key
        if not Settings.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is not set in .env file")
        elif Settings.GROQ_API_KEY == "your_groq_api_key_here":
            errors.append("GROQ_API_KEY is still set to placeholder value")
        elif len(Settings.GROQ_API_KEY) < 20:
            warnings.append("GROQ_API_KEY seems too short - verify it's correct")
        
        # 2. Check vision model compatibility
        if Settings.VISION_ENABLED:
            if not Settings.VISION_MODEL:
                errors.append("VISION_MODEL must be set when VISION_ENABLED=true")
            elif Settings.VISION_MODEL not in Settings.SUPPORTED_VISION_MODELS:
                errors.append(
                    f"Unsupported VISION_MODEL: {Settings.VISION_MODEL}. "
                    f"Supported models: {', '.join(Settings.SUPPORTED_VISION_MODELS)}"
                )
        
        # 3. Validate numeric settings
        if Settings.MAX_AGENT_STEPS < 1:
            errors.append("MAX_AGENT_STEPS must be at least 1")
        
        if Settings.MAX_BROWSERS < 1 or Settings.MAX_BROWSERS > 50:
            errors.append("MAX_BROWSERS must be between 1 and 50")
        
        if Settings.MAX_LLM_CALLS_PER_TASK < 1:
            errors.append("MAX_LLM_CALLS_PER_TASK must be at least 1")
        
        if not (0 <= Settings.INTELLIGENCE_RATIO <= 1):
            errors.append("INTELLIGENCE_RATIO must be between 0.0 and 1.0")
        
        if Settings.BROWSER_TIMEOUT < 5000:
            warnings.append("BROWSER_TIMEOUT is very low - may cause timeouts")
        
        # 4. Security warnings
        if Settings.ENABLE_PERSISTENT_CONTEXT:
            warnings.append(
                "⚠️  PERSISTENT_CONTEXT is enabled. This stores auth tokens on disk. "
                "Only use in trusted environments."
            )
        
        # Print warnings
        if warnings:
            print("\n⚠️  Configuration Warnings:")
            for warning in warnings:
                print(f"   - {warning}")
        
        # Raise errors if any
        if errors:
            error_msg = "\n❌ Configuration Errors:\n" + "\n".join(f"   - {e}" for e in errors)
            raise ValueError(error_msg)
        
        print("✅ Configuration validated successfully")
        return True

settings = Settings()

# Validate on module load
try:
    settings.validate_configuration()
except ValueError as e:
    print(f"\n{e}")
    print("\n💡 Fix these issues in your .env file before running.")