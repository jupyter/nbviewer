import os
import sys
import logging

from gist import app as gist

# No use for __main__ if running gunicorn

log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'WARN'))
gist.logger.setLevel(log_level)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(log_level)
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s: %(message)s '
))
gist.logger.addHandler(handler)
