import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_PATH = "pipeline.log"

# Ensure log file exists
Path(".").mkdir(exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """
    Creates a consistent logger for all agents and core modules.
    Includes:
    - timestamps
    - module/agent name
    - rotating file handler
    - console output
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # ---------------------------------------------------------
    # FORMATTER
    # ---------------------------------------------------------
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---------------------------------------------------------
    # FILE HANDLER (rotating)
    # ---------------------------------------------------------
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=2_000_000,  # 2MB per log file
        backupCount=5,       # keep 5 backups
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # ---------------------------------------------------------
    # CONSOLE HANDLER
    # ---------------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # ---------------------------------------------------------
    # ATTACH HANDLERS
    # ---------------------------------------------------------
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
