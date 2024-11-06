import logging
from logtail import LogtailHandler
from flask import current_app

def configure_logger():
    handler = LogtailHandler(source_token=current_app.config['LOGTAIL_TOKEN'])
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.addHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s"
    )

    return logger