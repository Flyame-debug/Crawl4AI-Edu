"""
功能：Django 项目总配置文件
用途：配置数据库、应用、中间件、语言、时区、API 分页等
关键配置：
- INSTALLED_APPS：注册哪些应用
- DATABASES：使用 SQLite（开发）或 PostgreSQL（生产）
- MIDDLEWARE：CORS 跨域支持
- LANGUAGE_CODE：中文界面
- LOGGING：日志系统配置（模块9.3）
- CRAWLER_ETHICS：爬虫伦理配置（模块8.5）
调用方：Django 启动时自动加载
"""
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = "django-insecure-ayxz2eruip8db=x!h7nnn-5+r*@$t%u7vz@7hmn%a-p^yd#y*v"
DEBUG = True
ALLOWED_HOSTS = []

# 添加项目根目录（包含 sandbox 的目录）
PROJECT_ROOT = BASE_DIR.parent.parent.parent  # E:\Crawl4AI
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BASE_DIR))  # 添加 src/backend 到路径


# Application definition
INSTALLED_APPS = [
    'simpleui',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'apps.api',
    'rest_framework',
    'corsheaders',
    'apps.stats',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "edu_backend.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # 添加模板目录
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "edu_backend.wsgi.application"

# Database
#DATABASES = {
#    "default": {
#        "ENGINE": "django.db.backends.sqlite3",
#        "NAME": BASE_DIR / "db.sqlite3",
#    }
#}
# 粘贴PG配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'crawl_db',        # 等下在pgAdmin创建的数据库名字固定这个
        'USER': 'postgres',        # PG默认超级用户名固定
        'PASSWORD': '123456', # 安装PG时手动输的密码，改成你自己的
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'OPTIONS': {
            'client_encoding': 'UTF8',  # ← 添加这一行
        },
    }
}
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# SimpleUI 配置
SIMPLEUI_HOME_INFO = False
SIMPLEUI_ANALYSIS = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS 配置
CORS_ALLOW_ALL_ORIGINS = True

# REST Framework 配置
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}


# MinIO配置样例
#192.168.138.1
MINIO_ENDPOINT = "127.0.0.1:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_SECURE = False

# ============================================================
# 模块8.5：爬虫伦理配置 - 请求延迟和并发控制
# ============================================================
CRAWLER_ETHICS = {
    'DEFAULT_DOWNLOAD_DELAY': 1.0,      # 默认请求间隔(秒)，避免高频请求压垮服务器
    'MAX_CONCURRENT_PER_DOMAIN': 5,     # 单域名最大并发数，防止同时开太多连接
    'REQUEST_TIMEOUT': 30,              # 请求超时(秒)
    'MAX_RETRIES': 3,                   # 最大重试次数
    'ENABLE_RATE_LIMIT': True,          # 是否启用限流
    'USER_AGENT': 'Crawl4AI-Bot/1.0',   # 爬虫标识，方便网站管理员联系
}

# ============================================================
# 模块9.3：日志配置 - 记录错误日志供监控和排查
# ============================================================
# 创建 logs 目录（如果不存在）
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # 详细格式：包含时间、级别、模块、进程、线程
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        # 简化格式：只包含时间、级别、消息
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        # 错误日志写入文件（供 API 读取）
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'error.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        # 所有日志写入文件（完整记录）
        'app_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        # 控制台输出（开发调试用）
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        # Django 框架日志
        'django': {
            'handlers': ['error_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        # 自定义应用日志（apps.api, apps.stats 等）
        'apps': {
            'handlers': ['app_file', 'error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # 爬虫相关日志
        'crawler': {
            'handlers': ['app_file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'error_file'],
        'level': 'INFO',
    },
}

# ============================================================
# Celery 异步任务队列配置
# ============================================================
from celery.schedules import crontab

# Broker 配置：使用 Redis 作为消息中间件（开发环境）
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
# 结果后端：也可使用 Redis
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'

# 序列化配置
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'

# 任务配置
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 单任务最大执行时间 30 分钟

# Beat 定时调度配置
CELERY_BEAT_SCHEDULE = {
    'process-conversion': {
        'task': 'apps.api.tasks.process_conversion_task',
        'schedule': crontab(minute='*/5'),  # 每5分钟执行一次
    },
}