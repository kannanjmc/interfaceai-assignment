"""
Configuration management for the computer-use automation system.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # LLM Configuration
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Target Application
    target_app_url: str = "http://localhost:5000"
    target_app_type: str = "legacy_web"
    
    # Safety Configuration
    allowed_domains: str = "localhost,127.0.0.1"
    allowed_actions: str = "click,type,navigate,wait,extract,select"
    risky_actions: str = "submit,delete,confirm"
    
    # Agent Configuration
    max_steps: int = 50
    timeout_seconds: int = 300
    human_handoff_enabled: bool = True
    
    # Evidence Configuration
    evidence_dir: str = "evidence"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_openai_key(self) -> str:
        """Get OpenAI API key."""
        key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY not set in environment or .env file")
        return key
    
    def get_llm_key(self) -> str:
        """Get the appropriate API key based on provider."""
        if self.llm_provider == "openai":
            return self.get_openai_key()
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}. Currently only 'openai' is supported.")
    
    def get_model(self) -> str:
        """Get the model name for the configured provider."""
        if self.llm_provider == "openai":
            return self.openai_model
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}. Currently only 'openai' is supported.")


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
