#!/usr/bin/env python3
"""
Hirshhorn Museum — API-first scraper scaffold.

Probes WordPress Tribe Events + exhibition REST endpoints before HTML discovery.
Run with --probe to test viability from Railway or locally.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sys
from datetime import date, datetime, time as time_class
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup

from scripts.scraper_logging import get_scraper_logger

logger = get_scraper_logger(__name__)

HIRSHHORN_SCRAPER_KEY = 'hirshhorn'
HIRSHHORN_BASE_URL = 'https://hirshhorn.si.edu'
HIRSHHORN_REFERER = f'{HIRSHHORN_BASE_URL}/exhibitions-events/'

TRIBE_EVENTS_API = f'{HIRSHHORN_BASE_URL}/wp-json/tribe/events/v1/events'
EXHIBITION_API = f'{HIRSHHORN_BASE_URL}/wp-json/wp/v2/exhibition'
EXHIBITIONS_LISTING_URL = HIRSHHORN_REFERER

PROBE_TARGETS: Tuple[Tuple[str, str], ...] = (
    ('tribe_events', f'{TRIBE_EVENTS_API}?per_page=5'),
    ('exhibition_api', f'{EXHIBITION_API}?per_page=5&status=publish'),
    ('exhibitions_listing', EXHIBITIONS_LISTING_URL),
)

CHALLENGE_MARKERS = (
    'smithsonian request verification',
    'please continue when verification',
    'challenge-platform',
    'cf-chl',
    'turnstile',
    'captcha',
)


def _body_preview(response, max_len: int = 100) -> str:
    if response is None:
        return ''
    try:
        text = re.sub(r'\s+', ' ', (response.text or '')).strip()
    except Exception:
        return ''
    return text[:max_len]


def _challenge_indicators(text: str) -> List[str]:
    low = (text or '').lower()
    return [m for m in CHALLENGE_MARKERS if m in low]


def create_hirshhorn_session() -> Tuple[Any, bool, bool]:
    """Cloudscraper (or requests) session with Hirshhorn proxy opt-in."""
    from scripts.scraper_utils import (
        create_cloudscraper_session,
        create_scraper_session,
        scraper_proxy_opt_in,
    )

    use_proxy = scraper_proxy_opt_in(HIRSHHORN_SCRAPER_KEY)
    scraper = create_cloudscraper_session(
        base_url=HIRSHHORN_BASE_URL,
        verify_ssl=False,
        use_proxy=use_proxy,
        scraper_key=HIRSHHORN_SCRAPER_KEY,
    )
    if scraper:
        scraper.headers.update({
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': HIRSHHORN_REFERER,
            'Sec-Fetch-Site': 'same-origin',
        })
        return scraper, use_proxy, True

    logger.warning(
        'hirshhorn: cloudscraper unavailable; using requests session (scraper_key=%s)',
        HIRSHHORN_SCRAPER_KEY,
    )
    scraper = create_scraper_session(
        verify_ssl=False,
        use_proxy=use_proxy,
        scraper_key=HIRSHHORN_SCRAPER_KEY,
    )
    scraper.headers.update({
        'Accept-Encoding': 'gzip, deflate',
        'Referer': HIRSHHORN_REFERER,
    })
    return scraper, use_proxy, False


def _fetch_hirshhorn(
    url: str,
    *,
    accept: str,
    session=None,
    session_meta: Optional[Tuple[bool, bool]] = None,
    timeout: Tuple[int, int] = (15, 45),
) -> Tuple[Optional[Any], bool, bool]:
    """Low-level GET; returns (response, proxy_used, cloudscraper_used)."""
    if session is None:
        session, proxy_used, cloudscraper_used = create_hirshhorn_session()
    else:
        proxy_used, cloudscraper_used = session_meta or (False, False)

    headers = {'Accept': accept, 'Referer': HIRSHHORN_REFERER}
    try:
        response = session.get(url, headers=headers, timeout=timeout, verify=False)
        return response, proxy_used, cloudscraper_used
    except Exception as exc:
        logger.warning('hirshhorn: fetch error url=%s (%s)', url, exc)
        return None, proxy_used, cloudscraper_used


def probe_hirshhorn_endpoints() -> List[Dict[str, Any]]:
    """
    Railway-friendly diagnostic for the three Hirshhorn entry URLs.
    Logs status, content-type, proxy use, body preview, and challenge markers.
    """
    session, proxy_used, cloudscraper_used = create_hirshhorn_session()
    session_meta = (proxy_used, cloudscraper_used)
    results: List[Dict[str, Any]] = []

    logger.info(
        'hirshhorn: probe start proxy_used=%s cloudscraper_used=%s',
        proxy_used,
        cloudscraper_used,
    )

    for label, url in PROBE_TARGETS:
        accept = (
            'application/json'
            if label in ('tribe_events', 'exhibition_api')
            else 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        )
        response, proxy_used, cloudscraper_used = _fetch_hirshhorn(
            url,
            accept=accept,
            session=session,
            session_meta=session_meta,
        )

        status = getattr(response, 'status_code', None)
        content_type = (getattr(response, 'headers', None) or {}).get('content-type', '')
        preview = _body_preview(response)
        indicators = _challenge_indicators(getattr(response, 'text', '') or '')

        item_count = None
        json_ok = False
        if response is not None and status == 200 and 'json' in content_type.lower():
            try:
                payload = response.json()
                json_ok = True
                if label == 'tribe_events' and isinstance(payload, dict):
                    item_count = len(payload.get('events') or [])
                elif label == 'exhibition_api' and isinstance(payload, list):
                    item_count = len(payload)
            except (json.JSONDecodeError, ValueError):
                json_ok = False

        row = {
            'label': label,
            'url': url,
            'status': status,
            'content_type': content_type,
            'proxy_used': proxy_used,
            'cloudscraper_used': cloudscraper_used,
            'body_preview': preview,
            'challenge_indicators': indicators,
            'json_ok': json_ok,
            'item_count': item_count,
        }
        results.append(row)

        logger.info(
            'hirshhorn: probe %s status=%s content_type=%s proxy_used=%s '
            'cloudscraper_used=%s json_ok=%s item_count=%s challenge=%s body_preview=%r',
            label,
            status,
            content_type,
            proxy_used,
            cloudscraper_used,
            json_ok,
            item_count,
            indicators or 'none',
            preview,
        )

    viable = summarize_probe_viability(results)
    logger.info('hirshhorn: probe summary %s', viable['verdict'])
    for line in viable['details']:
        logger.info('   %s', line)

    return results


def summarize_probe_viability(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Interpret probe rows for operators."""
    by_label = {r['label']: r for r in results}
    tribe_ok = (
        by_label.get('tribe_events', {}).get('status') == 200
        and by_label.get('tribe_events', {}).get('json_ok')
    )
    exh_api_ok = (
        by_label.get('exhibition_api', {}).get('status') == 200
        and by_label.get('exhibition_api', {}).get('json_ok')
    )
    listing = by_label.get('exhibitions_listing', {})
    listing_ok = listing.get('status') == 200 and not listing.get('challenge_indicators')

    details = []
    if tribe_ok:
        details.append('tribe_events API: OK — tours/programs via JSON')
    else:
        details.append('tribe_events API: blocked or non-JSON')

    if exh_api_ok:
        details.append('exhibition_api: OK — exhibitions via JSON')
    else:
        details.append('exhibition_api: blocked or non-JSON')

    if listing_ok:
        details.append('exhibitions_listing HTML: OK — JSON-LD fallback possible')
    else:
        details.append('exhibitions_listing HTML: blocked or challenge page')

    if tribe_ok or exh_api_ok:
        verdict = 'api_viable'
    elif listing_ok:
        verdict = 'listing_only'
    else:
        verdict = 'all_blocked'

    return {
        'verdict': verdict,
        'tribe_ok': tribe_ok,
        'exhibition_api_ok': exh_api_ok,
        'listing_ok': listing_ok,
        'details': details,
    }


def fetch_hirshhorn_json(
    url: str,
    *,
    session=None,
    session_meta: Optional[Tuple[bool, bool]] = None,
) -> Tuple[Optional[Any], Dict[str, Any]]:
    """
    Fetch a Hirshhorn JSON endpoint.
    Returns (parsed JSON or None, metadata dict).
    """
    response, proxy_used, cloudscraper_used = _fetch_hirshhorn(
        url,
        accept='application/json',
        session=session,
        session_meta=session_meta,
    )
    meta = {
        'url': url,
        'status': getattr(response, 'status_code', None),
        'content_type': (getattr(response, 'headers', None) or {}).get('content-type', ''),
        'proxy_used': proxy_used,
        'cloudscraper_used': cloudscraper_used,
        'body_preview': _body_preview(response),
        'challenge_indicators': _challenge_indicators(getattr(response, 'text', '') or ''),
    }
    if response is None or meta['status'] != 200:
        logger.warning('hirshhorn: json fetch failed meta=%s', meta)
        return None, meta
    if 'json' not in (meta['content_type'] or '').lower():
        logger.warning('hirshhorn: expected JSON content_type=%s', meta['content_type'])
        return None, meta
    try:
        return response.json(), meta
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning('hirshhorn: json decode failed (%s)', exc)
        return None, meta


def _strip_html(text: str) -> str:
    if not text:
        return ''
    return BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)


def _parse_datetime_fields(value: str) -> Tuple[Optional[date], Optional[time_class]]:
    if not value:
        return None, None
    value = value.strip()
    try:
        if 'T' in value:
            value = value.replace('T', ' ', 1)
        if ' ' in value and ':' in value:
            dt = datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
            return dt.date(), dt.time()
        dt = datetime.strptime(value[:10], '%Y-%m-%d')
        return dt.date(), None
    except ValueError:
        return None, None


def _map_tribe_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = (raw.get('title') or '').strip()
    url = raw.get('url') or ''
    start_date, start_time = _parse_datetime_fields(raw.get('start_date') or '')
    end_date, end_time = _parse_datetime_fields(raw.get('end_date') or '')
    description = _strip_html(raw.get('description') or raw.get('excerpt') or '')

    event_type = 'tour'
    blob = f'{title} {description}'.lower()
    if 'exhibition' in blob and 'tour' not in blob:
        event_type = 'exhibition'
    elif 'talk' in blob or 'lecture' in blob:
        event_type = 'talk'
    elif 'film' in blob or 'screening' in blob:
        event_type = 'film'

    image = raw.get('image') or {}
    image_url = image.get('url') if isinstance(image, dict) else None

    return {
        'title': html.unescape(title),
        'url': url,
        'start_date': start_date,
        'start_time': start_time,
        'end_date': end_date,
        'end_time': end_time,
        'description': description,
        'event_type': event_type,
        'image_url': image_url,
        'source': 'website',
        'source_url': url or TRIBE_EVENTS_API,
        'organizer': 'Smithsonian Hirshhorn Museum and Sculpture Garden',
    }


def _map_exhibition_post(raw: Dict[str, Any]) -> Dict[str, Any]:
    title_field = raw.get('title') or {}
    title = title_field.get('rendered') if isinstance(title_field, dict) else title_field
    title = html.unescape(_strip_html(str(title or '')))
    link = raw.get('link') or ''
    excerpt = _strip_html(
        (raw.get('excerpt') or {}).get('rendered', '')
        if isinstance(raw.get('excerpt'), dict)
        else ''
    )

    return {
        'title': title,
        'url': link,
        'description': excerpt,
        'event_type': 'exhibition',
        'source': 'website',
        'source_url': link or EXHIBITION_API,
        'organizer': 'Smithsonian Hirshhorn Museum and Sculpture Garden',
    }


def _events_from_listing_jsonld(html_text: str) -> List[Dict[str, Any]]:
    """Minimal fallback: JSON-LD Event blocks on exhibitions-events page."""
    events: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html_text, 'html.parser')
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
        except (json.JSONDecodeError, TypeError):
            continue
        items: List[Any]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and '@graph' in data:
            items = data['@graph']
        else:
            items = [data]
        for item in items:
            if not isinstance(item, dict) or item.get('@type') != 'Event':
                continue
            start_date, start_time = _parse_datetime_fields(item.get('startDate') or '')
            events.append({
                'title': html.unescape(_strip_html(item.get('name') or '')),
                'url': item.get('url') or EXHIBITIONS_LISTING_URL,
                'start_date': start_date,
                'start_time': start_time,
                'description': _strip_html(item.get('description') or ''),
                'event_type': 'event',
                'source': 'website',
                'source_url': EXHIBITIONS_LISTING_URL,
                'organizer': 'Smithsonian Hirshhorn Museum and Sculpture Garden',
            })
    return events


def scrape_hirshhorn_tours(
    *,
    per_page: int = 50,
    start_date: Optional[str] = None,
    session=None,
    session_meta: Optional[Tuple[bool, bool]] = None,
) -> List[Dict[str, Any]]:
    """Tours/programs from Tribe Events REST API (scaffold — no DB write)."""
    if session is None:
        session, proxy_used, cloudscraper_used = create_hirshhorn_session()
        session_meta = (proxy_used, cloudscraper_used)

    params = f'per_page={per_page}'
    if start_date:
        params += f'&start_date={start_date}'
    url = f'{TRIBE_EVENTS_API}?{params}'

    payload, meta = fetch_hirshhorn_json(url, session=session, session_meta=session_meta)
    if not payload or not isinstance(payload, dict):
        logger.info('hirshhorn: tours API unavailable status=%s', meta.get('status'))
        return []

    raw_events = payload.get('events') or []
    mapped = [_map_tribe_event(ev) for ev in raw_events if isinstance(ev, dict)]
    logger.info(
        'hirshhorn: tribe API returned %d events (mapped %d)',
        len(raw_events),
        len(mapped),
    )
    return mapped


def scrape_hirshhorn_exhibitions(
    *,
    per_page: int = 20,
    session=None,
    session_meta: Optional[Tuple[bool, bool]] = None,
) -> List[Dict[str, Any]]:
    """Exhibitions from wp/v2/exhibition, with listing JSON-LD fallback."""
    if session is None:
        session, proxy_used, cloudscraper_used = create_hirshhorn_session()
        session_meta = (proxy_used, cloudscraper_used)

    url = f'{EXHIBITION_API}?per_page={per_page}&status=publish'
    payload, meta = fetch_hirshhorn_json(url, session=session, session_meta=session_meta)

    if isinstance(payload, list) and payload:
        mapped = [_map_exhibition_post(item) for item in payload if isinstance(item, dict)]
        logger.info('hirshhorn: exhibition API returned %d items', len(mapped))
        return mapped

    logger.info(
        'hirshhorn: exhibition API unavailable status=%s — trying listing JSON-LD',
        meta.get('status'),
    )
    response, _, _ = _fetch_hirshhorn(
        EXHIBITIONS_LISTING_URL,
        accept='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        session=session,
        session_meta=session_meta,
    )
    if response is None or response.status_code != 200:
        logger.warning('hirshhorn: listing fallback failed status=%s', getattr(response, 'status_code', None))
        return []

    fallback = _events_from_listing_jsonld(response.text)
    logger.info('hirshhorn: listing JSON-LD fallback returned %d events', len(fallback))
    return fallback


def scrape_all_hirshhorn_events(
    *,
    tour_start_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    API-first aggregate (scaffold). Runs probe summary, then best-effort fetch.
    Not wired to admin/cron yet.
    """
    session, proxy_used, cloudscraper_used = create_hirshhorn_session()
    session_meta = (proxy_used, cloudscraper_used)

    tours = scrape_hirshhorn_tours(
        start_date=tour_start_date,
        session=session,
        session_meta=session_meta,
    )
    exhibitions = scrape_hirshhorn_exhibitions(session=session, session_meta=session_meta)

    combined = exhibitions + tours
    logger.info(
        'hirshhorn: scrape_all total=%d (exhibitions=%d tours=%d)',
        len(combined),
        len(exhibitions),
        len(tours),
    )
    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description='Hirshhorn API-first probe and scaffold scraper')
    parser.add_argument(
        '--probe',
        action='store_true',
        help='Probe tribe/exhibition/listing endpoints (default)',
    )
    parser.add_argument(
        '--scrape',
        action='store_true',
        help='Run minimal API-first scrape (no DB write)',
    )
    parser.add_argument(
        '--tour-start-date',
        default=date.today().isoformat(),
        help='start_date filter for tribe events API (YYYY-MM-DD)',
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if args.scrape:
        events = scrape_all_hirshhorn_events(tour_start_date=args.tour_start_date)
        for event in events[:10]:
            logger.info(
                '  - %s | %s | %s | %s',
                (event.get('title') or '')[:60],
                event.get('start_date'),
                event.get('event_type'),
                event.get('url'),
            )
        return 0 if events else 1

    probe_hirshhorn_endpoints()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
