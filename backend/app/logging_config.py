import logging
import sys

def setup_logging():
    """
    Configures logging for the application.
    Outputs to console with a detailed format.
    """
    # Define the log format
    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s"
    )

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set default level for root logger

    # Create a handler for console output (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    
    # Add the console handler to the root logger
    # Avoid adding handlers multiple times if setup_logging is called more than once
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    # Configure specific loggers if needed (examples)
    logging.getLogger("app").setLevel(logging.INFO) # General app logs
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Access logs can be noisy, set to WARNING or INFO
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING) # To avoid verbose SQL logs by default

    # You can redirect specific third-party library logs if they are too noisy
    # logging.getLogger("some_noisy_library").setLevel(logging.WARNING)

    logging.info("Logging configured successfully.")

if __name__ == "__main__":
    # Example of how logs would look
    setup_logging()
    logging.info("This is an info message from root.")
    logging.getLogger("app.test").warning("This is a warning from app.test.")
    try:
        1/0
    except ZeroDivisionError:
        logging.getLogger("app.error").error("A handled error occurred.", exc_info=True)
