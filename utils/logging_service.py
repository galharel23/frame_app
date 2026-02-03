# utils/logging_service.py
import logging
import sys
from datetime import datetime
from pathlib import Path

# Create logs directory next to the executable or script
if getattr(sys, "frozen", False):
    # If running as compiled EXE
    base_dir = Path(sys.executable).parent
else:
    # If running as script
    base_dir = Path(__file__).parent.parent

log_dir = base_dir / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Create log file with timestamp
log_file = log_dir / f"tekenframe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(str(log_file), encoding="utf-8"), logging.StreamHandler()],  # Also print to console
)

# Get logger for the app
logger = logging.getLogger("TekenFrame")


def get_logger(name):
    """Get a logger instance for a specific module"""
    return logging.getLogger(f"TekenFrame.{name}")


# Log startup info
logger.info("=" * 80)
logger.info("TekenFrame Application Started")
logger.info(f"Log file: {log_file}")
logger.info("=" * 80)
