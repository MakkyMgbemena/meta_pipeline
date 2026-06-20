import logging

LOG_PATH = "pipeline.log"

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
    # CONSOLE HANDLER
    # ---------------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # ---------------------------------------------------------
    # ATTACH HANDLERS
    # ---------------------------------------------------------
    logger.addHandler(console_handler)

    return logger
