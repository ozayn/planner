"""
Shared DB lookups for scrapers — resolve cities, venues, and sources by natural keys.

Do not hardcode local/JSON numeric IDs: production PostgreSQL may use different ids than SQLite.

Typical pattern:
  city = resolve_city_by_name(db, City, "New York", "New York")
  venue = resolve_venue_in_city(db, Venue, city.id, website_contains=["example.org"], name_contains=["Example Museum"])
  source = resolve_source_in_city(db, Source, city.id, handle_ilike=["@handle"], name_contains=["Example"])
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Type


def resolve_city_by_name(
    db,
    City: Type[Any],
    name: str,
    state: Optional[str] = None,
) -> Optional[Any]:
    """
    Find a city row by case-insensitive name. If ``state`` is non-empty, prefer
    name + state match, then fall back to name-only (same row shape as local JSON).
    """
    name_l = (name or "").strip().lower()
    if not name_l:
        return None
    state_l = (state or "").strip().lower() if state else ""
    if state_l:
        city = City.query.filter(
            db.func.lower(City.name) == name_l,
            db.func.lower(db.func.coalesce(City.state, "")) == state_l,
        ).first()
        if city:
            return city
    return City.query.filter(db.func.lower(City.name) == name_l).first()


def resolve_venue_in_city(
    db,
    Venue: Type[Any],
    city_id: int,
    *,
    website_contains: Optional[Sequence[str]] = None,
    name_contains: Optional[Sequence[str]] = None,
) -> Optional[Any]:
    """
    Find a venue in ``city_id`` by OR of URL substrings and/or name substrings (ilike).
    """
    clauses = []
    for s in website_contains or []:
        s = (s or "").strip()
        if s:
            clauses.append(Venue.website_url.ilike(f"%{s}%"))
    for s in name_contains or []:
        s = (s or "").strip()
        if s:
            clauses.append(Venue.name.ilike(f"%{s}%"))
    if not clauses:
        return None
    return Venue.query.filter(Venue.city_id == city_id).filter(db.or_(*clauses)).first()


def resolve_source_in_city(
    db,
    Source: Type[Any],
    city_id: int,
    *,
    handle_contains: Optional[Sequence[str]] = None,
    name_contains: Optional[Sequence[str]] = None,
) -> Optional[Any]:
    """
    Find a source in ``city_id`` by OR of handle substrings and/or name substrings (ilike).
    """
    clauses = []
    for s in handle_contains or []:
        s = (s or "").strip()
        if s:
            clauses.append(Source.handle.ilike(f"%{s}%"))
    for s in name_contains or []:
        s = (s or "").strip()
        if s:
            clauses.append(Source.name.ilike(f"%{s}%"))
    if not clauses:
        return None
    return Source.query.filter(Source.city_id == city_id).filter(db.or_(*clauses)).first()
