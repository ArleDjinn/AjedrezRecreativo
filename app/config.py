import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ajedrezrecreativo.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD = True

    # Webpay (se cargan desde .env)
    WEBPAY_COMMERCE_CODE = os.getenv("WEBPAY_COMMERCE_CODE")
    WEBPAY_API_KEY = os.getenv("WEBPAY_API_KEY")

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class ProductionConfig(BaseConfig):
    DEBUG = False

def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    return DevelopmentConfig if env == "development" else ProductionConfig
