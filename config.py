import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/quprdigital')
    
    # Session configuration
    SESSION_TYPE = 'mongodb'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'qupr:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Company details
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Qupr Digital')
    COMPANY_GSTIN = os.getenv('COMPANY_GSTIN', '')
    COMPANY_ADDRESS = os.getenv('COMPANY_ADDRESS', '')
    COMPANY_EMAIL = os.getenv('COMPANY_EMAIL', '')
    COMPANY_PHONE = os.getenv('COMPANY_PHONE', '')
    
    # Database
    DB_NAME = 'quprdigital'
    
    # Invoice
    INVOICE_PREFIX = 'INV'
    INVOICE_TEMPLATE_VERSION = 'v1'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
