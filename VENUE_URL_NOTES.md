# Venue URL Validation Notes

This document tracks known issues and characteristics of venue URLs discovered during validation.

## Summary
- **Total Venues**: 201
- **Valid URLs**: 109
- **Fixed URLs**: 75
- **Invalid URLs**: 34
- **Failed to Fix**: 15
- **Skipped**: 2

## Known URL Corrections

### Fixed URLs
- **Kennedy Center**: `kennedycenter.com` → `kennedy-center.org`
- **Library of Congress**: `libraryofcongress.com` → `loc.gov`
- **Philadelphia Museum of Art**: `philadelphiamuseumofart.com` → `visitpham.org` (rebranded)
- **Franklin Institute**: `franklininstitute.com` → `fi.edu`
- **Liberty Bell Center**: `libertybellcenter.com` → `nps.gov/inde/planyourvisit/libertybellcenter.htm`
- **Georgetown**: `georgetown.org` → `georgetown.com`
- **Musée d'Orsay**: Fixed special characters in URL
- **Musée du Louvre**: Fixed special characters in URL

## URL Characteristics by Venue

### SSL Certificate Issues (URLs work but have SSL problems)
These venues have valid URLs but SSL certificate verification issues:
- **National Portrait Gallery**: `npg.si.edu` - SSL cert issue, but URL works
- **Smithsonian Hirshhorn Museum**: `hirshhorn.si.edu` - SSL cert issue, but URL works
- **Smithsonian National Museum of African American History and Culture**: `nmaahc.si.edu` - SSL cert issue, but URL works
- **Smithsonian National Museum of American History**: `americanhistory.si.edu` - SSL cert issue, but URL works

### Bot Protection (403 Errors)
These venues return 403 but URLs are correct (bot protection):
- **National Gallery of Art**: `nga.gov` - Returns 403 (bot protection), but URL is correct

### Closed/Permanently Unavailable
- **Newseum**: Closed permanently (no valid URL)

### Redirects
Many venues redirect to slightly different URLs (www vs non-www, trailing slashes, etc.):
- **Capitol Hill Arts Workshop**: Redirects to `chaw.org/`
- **Ford's Theatre**: Redirects to `fords.org/`
- **Smithsonian National Museum of Asian Art**: Redirects to `asia.si.edu/`
- **Embassy of Spain**: Redirects to full embassy page
- **Embassy of Brazil**: Redirects to new government domain

### Timeout/Connection Issues
Some venues have intermittent connection issues:
- **Embassy of Australia**: `usa.embassy.gov.au` - Timeout issues
- **Newseum**: Timeout (closed)

### HTTP 404 Errors
- **Dupont Circle**: `nps.gov/rocr/planyourvisit/dupont-circle.htm` - 404 (page may have moved)

## Recommendations

1. **SSL Issues**: These are false positives - the URLs work, just have certificate verification issues. Keep URLs as-is.

2. **Bot Protection (403)**: URLs are correct, but sites block automated requests. Consider:
   - Using cloudscraper (already implemented)
   - Using LLM fallback (already implemented)
   - Keeping URLs as-is

3. **Redirects**: Update URLs to final destination to avoid unnecessary redirects.

4. **Closed Venues**: Mark as inactive or remove from active scraping.

5. **404 Errors**: Research correct URLs or mark venues as needing manual review.

## Next Steps

1. Re-run validation with enhanced tracking to capture all URL details
2. Update venues.json with all fixed URLs
3. Create a maintenance schedule to re-validate URLs periodically
4. Document any venues that need manual review
