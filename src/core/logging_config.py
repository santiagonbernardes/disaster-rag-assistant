"""Centralized logging configuration for the Disaster RAG Assistant application."""

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the entire application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(".logs")
    log_dir.mkdir(exist_ok=True)

    # Configure log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler for all logs
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            # Rotating file handler for errors
            logging.handlers.RotatingFileHandler(
                log_dir / "errors.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            ),
        ],
    )

    # Configure error handler to only log warnings and above
    error_handler = [
        h
        for h in logging.root.handlers
        if "errors.log" in str(getattr(h, "baseFilename", ""))
    ]
    if error_handler:
        error_handler[0].setLevel(logging.WARNING)

    # Set specific log levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
