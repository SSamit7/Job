from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "apps.accounts",
    "apps.jobs",
    "apps.applications",
    "apps.contracts",
    "apps.payments",
    "apps.reviews",
    "apps.core",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:home"

# Platform business rule: commission % held on every completed job payment
PLATFORM_COMMISSION_PERCENT = 10

# --- Payment gateway settings ---
# Used to build absolute success/failure/return URLs the user's browser gets
# redirected back to after paying at eSewa/Khalti. Safe as localhost for dev -
# these are browser redirects, not server-to-server calls, so the gateway
# never needs to reach this URL itself. Set to your real domain in production.
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://127.0.0.1:8000")

# eSewa ePay v2. EPAYTEST / this exact secret key are eSewa's own PUBLISHED
# sandbox test credentials (developer.esewa.com.np) - safe to ship as
# defaults, no signup needed to test with them. For production: get your
# real merchant code + secret key from the eSewa Merchant Dashboard, and
# switch the two URLs below to the *.esewa.com.np (non-uat/non-rc) hosts.
ESEWA_MERCHANT_CODE = os.getenv("ESEWA_MERCHANT_CODE", "EPAYTEST")
ESEWA_SECRET_KEY = os.getenv("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
ESEWA_PAYMENT_URL = os.getenv("ESEWA_PAYMENT_URL", "https://rc-epay.esewa.com.np/api/epay/main/v2/form")
ESEWA_STATUS_CHECK_URL = os.getenv("ESEWA_STATUS_CHECK_URL", "https://uat.esewa.com.np/api/epay/transaction/status/")

# Khalti KPG-2 ePayment. Unlike eSewa, Khalti has no universal public test
# key - sign up free at https://test-admin.khalti.com, grab your sandbox
# secret key from that dashboard, and put it in .env as KHALTI_SECRET_KEY.
# Left blank by default; the Khalti option tells the worker it isn't set up
# yet rather than pretending to work.
KHALTI_SECRET_KEY = os.getenv("KHALTI_SECRET_KEY", "")
KHALTI_INITIATE_URL = os.getenv("KHALTI_INITIATE_URL", "https://dev.khalti.com/api/v2/epayment/initiate/")
KHALTI_LOOKUP_URL = os.getenv("KHALTI_LOOKUP_URL", "https://dev.khalti.com/api/v2/epayment/lookup/")

# --- Email (the "off-app" notification channel) ---
# Console backend by default: notification emails just print to the
# runserver terminal - nothing to configure, easy to see it's working.
# For real delivery, set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# in .env plus EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / EMAIL_PORT
# / EMAIL_USE_TLS (e.g. via SendGrid, Mailgun, or Gmail SMTP).
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@jobplatform.local")

# True SMS/push notifications ("their phone") need a provider like Twilio
# (SMS) or Firebase Cloud Messaging (push) and their own API credentials -
# not wired in here since none are available. Email above is the realistic
# stand-in until those are added.
