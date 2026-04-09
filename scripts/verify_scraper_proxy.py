#!/usr/bin/env python3
"""
Verify Webshare proxy configuration: session bootstrap + public egress IP.

Uses the same session helpers as scrapers. Does not print proxy passwords.

Usage:
  SCRAPER_PROXY_SESSION_LOG=1 ./venv/bin/python scripts/verify_scraper_proxy.py
  SCRAPER_PROXY_SESSION_LOG=1 ./venv/bin/python scripts/verify_scraper_proxy.py --key big_onion
  ./venv/bin/python scripts/verify_scraper_proxy.py --force-proxy   # attach WEBSHARE if set, ignore opt-in

Environment:
  WEBSHARE_PROXY_URL or WEBSHARE_PROXY_HTTP/HTTPS — required for proxy_applied=True
  SCRAPER_PROXY_SESSION_LOG=1 — show INFO bootstrap line on Railway/local (see session.py rules)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.scraper_utils.session import (  # noqa: E402
    create_scraper_session,
    probe_public_ip_with_session,
    scraper_proxy_opt_in,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Webshare proxy + egress IP echo")
    parser.add_argument(
        "--key",
        default=os.environ.get("SCRAPER_PROXY_VERIFY_KEY", "nga"),
        help="Scraper key for scraper_proxy_opt_in() (default: nga or SCRAPER_PROXY_VERIFY_KEY)",
    )
    parser.add_argument(
        "--force-proxy",
        action="store_true",
        help="Set use_proxy=True if WEBSHARE_* is set (bypass opt-in; tests raw env attachment)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    opt_in = scraper_proxy_opt_in(args.key)
    use_proxy = True if args.force_proxy else opt_in

    print(f"scraper_proxy_opt_in({args.key!r}) -> {opt_in}")
    print(f"use_proxy for session -> {use_proxy}" + (" (forced)" if args.force_proxy else ""))

    session = create_scraper_session(
        verify_ssl=True,
        use_retries=False,
        use_proxy=use_proxy,
        scraper_key=args.key,
    )
    ip = probe_public_ip_with_session(session)
    if ip:
        print(f"egress_ip_echo -> {ip}")
    else:
        print("egress_ip_echo -> (failed; check network or proxy)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
