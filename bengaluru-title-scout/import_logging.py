import logging
import sys

# Configure logging to output to stdout with INFO level
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

log.info("This is a test log message")
sys.stdout.flush()  # Force flush the buffer