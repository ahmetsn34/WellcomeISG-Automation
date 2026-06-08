"""Configuration constants for Wellcome Automation GUI."""

# URLs
LOGIN_URL = "https://wellcome.azurewebsites.net/pnlwell/login/"

# Email Configuration
GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993

# Timeouts (seconds)
INITIAL_SERVER_DELAY = 3  # Delay before first Gmail connection
PAGE_LOAD_TIMEOUT = 5
ELEMENT_INTERACTION_RETRIES = 5
ELEMENT_INTERACTION_DELAY = 1
MAIL_CHECK_INTERVAL = 4
DEFAULT_LOGIN_TIMEOUT = 20
DEFAULT_MAIL_WAIT_TIMEOUT = 40

# Retry Configuration
DEFAULT_MAIL_RETRY_ATTEMPTS = 10
DEFAULT_ELEMENT_RETRY_ATTEMPTS = 5

# UI Configuration
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 750
TITLE = "Wellcome Advanced Automation Panel v3.0"

# Form Element IDs
FORM_IDS = {
    "firm_code": "FirmCode",
    "username": "Username",
    "password": "Password",
    "login_button": "loginButton",
    "verification_code": "VerificationCode"
}

# CSS Selectors
VERIFICATION_BUTTON_CSS = "a.btn.btn-sms-verification.btn-block.btn-lg.btn-primary.text-uppercase"
VERIFICATION_BUTTON_XPATH = "//a[contains(text(), 'Doğrula ve Giriş Yap')]"

# Log Tags
LOG_TAGS = {
    "normal": "normal",
    "system": "system",
    "success": "success",
    "error": "error",
    "warning": "warning"
}

# Report Settings
REPORT_FILENAME_FORMAT = "Wellcome_Login_Report_{timestamp}.xlsx"

# Chrome Options
DISABLE_IMAGES = 2  # Disable image loading for performance
