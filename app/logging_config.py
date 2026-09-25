"""
Configuración de logging con rotación de archivos.

Genera en ./logs/:
    - app.log    → todo desde INFO
    - error.log  → solo ERROR y superiores
Ambos rotan a los 10 MB y guardan 5 históricos.
"""

import logging
import logging.handlers
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / 'logs'


def setup_logging(app):
    LOG_DIR.mkdir(exist_ok=True)

    level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'app.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    error_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / 'error.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    error_handler.setFormatter(fmt)
    error_handler.setLevel(logging.ERROR)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(level)

    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console)
    app.logger.setLevel(level)

    # Werkzeug y Waitress: menos ruido
    logging.getLogger('werkzeug').setLevel(
        logging.INFO if app.config.get('DEBUG') else logging.WARNING
    )
    return app