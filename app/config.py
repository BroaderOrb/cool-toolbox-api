from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # CORS allowed origins (add your frontend URLs here)
    allowed_origins: List[str] = [
        "https://cool-toolbox.com",
        "https://www.cool-toolbox.com",
        "http://localhost:5173",        # Vite dev  
        "http://localhost:3000"  # local frontend
    ]

    # Supabase config
    supabase_url: str
    supabase_service_key: str

    # NEW (optional): CoinGecko API key support
    coingecko_api_key: str | None = None
    
    # Load .env file automatically if present
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

# Create a single settings instance
settings = Settings() 
