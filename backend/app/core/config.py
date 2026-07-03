from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Union
import os
import json


def _parse_cors_origins(v: Union[str, List[str], None]) -> List[str]:
    """Parse CORS origins from environment variable - handles both JSON and comma-separated strings"""
    # Handle None or empty string
    if v is None or (isinstance(v, str) and not v.strip()):
        return ["http://localhost:3000", "https://flowmindai.com"]
    
    if isinstance(v, str):
        # Try to parse as JSON first (for JSON array format)
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if origin]
        except (json.JSONDecodeError, ValueError, TypeError):
            # If not JSON, treat as comma-separated string
            pass
        
        # If not JSON, treat as comma-separated string
        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        if origins:
            return origins
        # If empty after splitting, return default
        return ["http://localhost:3000", "https://flowmindai.com"]
    elif isinstance(v, list):
        # Already a list, just ensure strings
        return [str(origin).strip() for origin in v if origin]
    
    # Fallback to default
    return ["http://localhost:3000", "https://flowmindai.com"]


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_VERSION: str = "v1"
    PROJECT_NAME: str = "FlowMind AI API"
    DESCRIPTION: str = "FlowMind AI Workflow Automation Backend"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-here-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = "flowmind-ai-123"
    FIREBASE_PRIVATE_KEY_ID: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    FIREBASE_CLIENT_ID: str = ""
    FIREBASE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    FIREBASE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    FIREBASE_AUTH_PROVIDER_CERT_URL: str = "https://www.googleapis.com/oauth2/v1/certs"
    FIREBASE_CLIENT_CERT_URL: str = ""
    FIREBASE_STORAGE_BUCKET: str = "flowmind-ai-123.firebasestorage.app"
    
    # Email Configuration (Optional)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@flowmindai.com"
    
    # Stripe Configuration
    STRIPE_SECRET_KEY: str = "sk_test_example"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_example" 
    STRIPE_WEBHOOK_SECRET: str = "whsec_example"
    
    # CORS Configuration
    # Can be set via environment variable as:
    # - Comma-separated string: CORS_ORIGINS="http://localhost:3000,https://flowmindai.com"
    # - JSON array: CORS_ORIGINS='["http://localhost:3000","https://flowmindai.com"]'
    # Note: localhost:3000 is automatically added in main.py for local development
    # Store as string to avoid JSON parsing issues, then convert in validator
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,https://flowmindai.com"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @model_validator(mode='after')
    def parse_cors_origins(self):
        """Convert CORS_ORIGINS from string to list after model creation"""
        if isinstance(self.CORS_ORIGINS, str):
            # This is a workaround - we'll store the parsed value
            parsed = _parse_cors_origins(self.CORS_ORIGINS)
            # Use object.__setattr__ to bypass Pydantic's immutability
            object.__setattr__(self, 'CORS_ORIGINS', parsed)
        elif isinstance(self.CORS_ORIGINS, list):
            # Already a list, ensure it's properly formatted
            parsed = _parse_cors_origins(self.CORS_ORIGINS)
            object.__setattr__(self, 'CORS_ORIGINS', parsed)
        return self
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields like REDIS_URL from .env


# Create settings instance
settings = Settings()


def get_firebase_credentials():
    """Get Firebase credentials as a dictionary for Firebase Admin SDK"""
    # Check if a single FIREBASE_CREDENTIALS JSON string is provided in the env
    env_creds = os.getenv("FIREBASE_CREDENTIALS")
    if env_creds:
        try:
            creds = json.loads(env_creds)
            if isinstance(creds, dict) and "private_key" in creds:
                creds["private_key"] = creds["private_key"].replace('\\n', '\n')
                return creds
        except Exception:
            # Fall back to individual settings if JSON parsing fails
            pass

    # Fall back to individual settings fields
    private_key = settings.FIREBASE_PRIVATE_KEY or ""
    if private_key:
        private_key = private_key.strip()
        # Strip surrounding quotes some dashboards (e.g. Render) preserve literally
        if len(private_key) >= 2 and private_key[0] == private_key[-1] and private_key[0] in ('"', "'"):
            private_key = private_key[1:-1]
        private_key = private_key.replace('\\n', '\n')

    return {
        "type": "service_account",
        "project_id": settings.FIREBASE_PROJECT_ID,
        "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
        "private_key": private_key,
        "client_email": settings.FIREBASE_CLIENT_EMAIL,
        "client_id": settings.FIREBASE_CLIENT_ID,
        "auth_uri": settings.FIREBASE_AUTH_URI,
        "token_uri": settings.FIREBASE_TOKEN_URI,
        "auth_provider_x509_cert_url": settings.FIREBASE_AUTH_PROVIDER_CERT_URL,
        "client_x509_cert_url": settings.FIREBASE_CLIENT_CERT_URL,
    }