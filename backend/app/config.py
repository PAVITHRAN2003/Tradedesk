from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "tradedesk"
    jwt_secret: str = "change-me"
    jwt_alg: str = "HS256"
    access_minutes: int = 15
    refresh_days_session: int = 1      # "remember me" unchecked
    refresh_days_remember: int = 30    # "remember me" checked
    cookie_secure: bool = False        # set true behind HTTPS
    cors_origins: str = "http://localhost:5173"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    bright_data_tools: str = "search_engine,scrape_as_markdown"
    tool_output_max_chars: int = 2000
    groq_max_tokens: int = 2000
    market_data_source: str = "yfinance"  # or "web" to use Bright Data for prices too
    bright_data_api_token: str = ""
    web_unlocker_zone: str = "unblocker"
    browser_zone: str = "scraping_browser"


settings = Settings()