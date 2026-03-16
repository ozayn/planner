#!/usr/bin/env python3
"""
Central scraper logging helper.
Provides consistent logger setup for scraper-related modules.
Use SCRAPER_DEBUG=1 to enable DEBUG-level scraper logs.
"""

import os
import logging


def get_scraper_logger(name: str) -> logging.Logger:
    """
    Return a logger for scraper modules with consistent setup.
    - INFO by default (clean operational logs)
    - DEBUG when SCRAPER_DEBUG=1 (verbose debugging)
    """
    logger = logging.getLogger(name)
    if os.environ.get('SCRAPER_DEBUG', '').strip().lower() in ('1', 'true', 'yes'):
        logger.setLevel(logging.DEBUG)
        # Add a handler for DEBUG when SCRAPER_DEBUG is set (root handler may filter DEBUG)
        if not any(h for h in logger.handlers if getattr(h, '_scraper_debug_handler', False)):
            _h = logging.StreamHandler()
            _h.setLevel(logging.DEBUG)
            _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
            _h._scraper_debug_handler = True  # type: ignore[attr-defined]
            logger.addHandler(_h)
            logger.propagate = False  # avoid duplicate to root when we have our own handler
    return logger
