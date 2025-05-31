import logging
import sys
import os # <--- Add this import
from logging.handlers import RotatingFileHandler # <--- Example for file handler, can be basic FileHandler too

# Define log directory and file
LOG_DIR = "backend/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logging():
    """
    Configures logging for the application.
    Outputs to console and a file with a detailed format.
    """
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True) # <--- Add this line

    # Define the log format
    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s"
    )

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Create a handler for console output (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    
    # Create a file handler
    # Using RotatingFileHandler as an example for better log management
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=2) # 5MB per file, 2 backups
    # Or use basic FileHandler:
    # file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(log_formatter)

    # Add handlers to the root logger
    # Avoid adding handlers multiple times
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler) # <--- Add file handler
    else:
        # If handlers exist, ensure file handler is added if not already present
        # This logic might need refinement depending on how often setup_logging can be called
        has_file_handler = any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
        if not has_file_handler:
            root_logger.addHandler(file_handler)
        # Ensure console handler is also present
        has_console_handler = any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in root_logger.handlers)
        if not has_console_handler:
             root_logger.addHandler(console_handler)


    # Configure specific loggers if needed
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Logging configured successfully (console and file).")

if __name__ == "__main__":
    setup_logging()
    logging.info("This is an info message from root.")
    logging.getLogger("app.test").warning("This is a warning from app.test.")
    try:
        1/0
    except ZeroDivisionError:
        logging.getLogger("app.error").error("A handled error occurred.", exc_info=True)
