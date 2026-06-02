"""Application configuration loaded from AWS Secrets Manager."""
from pydantic_settings import BaseSettings
from functools import lru_cache
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    secrets = {}
    for secret_name in ['teamapp/prod/jwt', 'teamapp/prod/ai', 'teamapp/prod/db']:
        response = client.get_secret_value(SecretId=secret_name)
        secrets.update(json.loads(response['SecretString']))
    return secrets

_secrets = get_secrets()

class Settings(BaseSettings):
    SUPABASE_URL: str = _secrets.get('SUPABASE_URL', '')
    SUPABASE_KEY: str = _secrets.get('SUPABASE_KEY', '')
    SUPABASE_SERVICE_KEY: str = _secrets.get('SUPABASE_SERVICE_KEY', '')
    GEMINI_API_KEY: str = _secrets.get('GEMINI_API_KEY', '')
    JWT_SECRET: str = _secrets.get('JWT_SECRET', '')
    REFRESH_SECRET: str = _secrets.get('REFRESH_SECRET', '')
    APP_NAME: str = "TeamTeam Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    CORS_ORIGINS: str = _secrets.get('CORS_ORIGINS', '*')

    model_config = {
        "extra": "ignore",
    }

@lru_cache()
def get_settings() -> Settings:
    return Settings()