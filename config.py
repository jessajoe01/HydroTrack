import os

class Config:
    SECRET_KEY = 'smartwater-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///smartwater.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email config (for alerts and supplier notifications)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your_email@gmail.com'
    MAIL_PASSWORD = 'your_app_password'