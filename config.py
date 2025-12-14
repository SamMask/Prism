import os

class Config:
    """
    Base Configuration
    """
    # 專案根目錄
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # 資料庫路徑
    DATABASE = os.environ.get('DATABASE_PATH') or os.path.join(BASE_DIR, 'knowledge.db')

    # 上傳檔案目錄
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'static', 'uploads')

    # 最大上傳大小 (5MB)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # 允許的圖片格式
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

    # JSON 回應支援 Unicode (顯示中文)
    JSON_AS_ASCII = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    DATABASE = ':memory:'  # Use in-memory SQLite for testing
    UPLOAD_FOLDER = os.path.join(Config.BASE_DIR, 'static', 'test_uploads')

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
