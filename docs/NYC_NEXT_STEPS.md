# NYC Rollout Status

## Overview

NYC rollout work has progressed across venue/source data cleanup, sync workflow preparation, production audit, `/api/sources` city_id fix, and source verification in local and production. The main remaining NYC production issue is **duplicate venue cleanup**.

## Completed

- Audited existing NYC venues and sources
- Cleaned local NYC venue/source data
- Added Brooklyn Museum, Lincoln Center, and BAM as venues
- Updated Ellis Island Hard Hat Tours source URL
- Documented Local → Production sync workflow
- Documented production NYC audit and duplicate-cleanup strategy
- Fixed `/api/sources` to use DB-backed city IDs instead of JSON city IDs
- Verified NYC sources load correctly using DB city IDs
- Verified production `/api/sources` now returns NYC sources correctly

## Current Known Issues

- Duplicate venue records for:
  - American Museum of Natural History
  - Metropolitan Museum of Art
- Possible duplicate venue issue in Paris for Musée d'Orsay
- Duplicate cleanup still needs manual review before deletion
- Sync script intentionally skips duplicate conflicts

## Remaining Next Steps

1. Inspect duplicate NYC venue pairs in production
2. Determine which duplicate has events
3. Keep the venue with events / better metadata / newer `updated_at`
4. Delete only the stale duplicate
5. Re-verify NYC venue count and names in production
6. Test NYC in the public UI
7. Test NYC source selection and discovery flow
8. Begin selective NYC scraper work only after venue state is clean

## Expected Final NYC State

- 11 NYC venues
- 12 NYC sources
- No duplicate Met
- No duplicate AMNH
- `/api/sources` works with DB city IDs
- NYC is ready for selective scraper expansion

## Suggested Future Work

- Selective NYC scraper additions (only for high-value venues that need custom logic)
- Recurring tours validation for NYC
- Public UI testing for NYC
- Cleanup of other duplicate conflicts like Musée d'Orsay
- Continued sync tooling improvements
