import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///sand.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    VAT_RATE = float(os.getenv("VAT_RATE", 0.05))  # 5%
    APP_NAME = os.getenv("APP_NAME", "مكتب سند")
