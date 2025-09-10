import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    if os.getenv('ENVIRONMENT') == 'production':
        SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///users.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_super_secret_key_change_in_production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt_secret_key_change_in_production')
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # API Keys
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # Model Configuration
    MODEL_RETRAIN_INTERVAL = int(os.getenv('MODEL_RETRAIN_INTERVAL', '3600'))  # 1 hour
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }