import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bff53de6dfc3ba18e18ce7d7796d9e90c5efa95c3a31ea4d'
    
    # PythonAnywhere-specific database configuration
    if os.environ.get('PYTHONANYWHERE_DOMAIN'):
        # Production settings for PythonAnywhere
        MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'aayushthapa123.mysql.pythonanywhere-services.com'
        MYSQL_USER = os.environ.get('MYSQL_USER') or 'aayushthapa123'
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''  # Your MySQL password from PythonAnywhere
        MYSQL_DB = os.environ.get('MYSQL_DB') or 'aayushthapa123$digital_journal'
        SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    else:
        # Development settings
        MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
        MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
        MYSQL_DB = os.environ.get('MYSQL_DB') or 'digital_journal'
        SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)