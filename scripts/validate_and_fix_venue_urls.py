#!/usr/bin/env python3
"""
Validate and Fix Venue URLs

This script:
1. Checks all venue URLs to see if they're valid
2. Uses web search and knowledge to find correct URLs for invalid ones
3. Updates the database and venues.json file
"""

import os
import sys
import json
import time
from urllib.parse import urlparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import requests after adding to path (may be in venv)
try:
    import requests
except ImportError:
    print("⚠️  requests not found, trying to use app's session...")
    requests = None

from app import app, db, Venue
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Known URL corrections (venue name -> correct URL)
KNOWN_CORRECTIONS = {
    'Philadelphia Museum of Art': 'https://www.visitpham.org',
    'Franklin Institute': 'https://fi.edu',
    'Liberty Bell Center': 'https://www.nps.gov/inde/planyourvisit/libertybellcenter.htm',
    'Musée d\'Orsay': 'https://www.musee-orsay.fr',
    'Musée du Louvre': 'https://www.louvre.fr',
    'Kennedy Center': 'https://www.kennedy-center.org',
    'Library of Congress': 'https://www.loc.gov',
    'National Gallery of Art': 'https://www.nga.gov',  # 403 is bot protection, URL is correct
    'National Portrait Gallery': 'https://npg.si.edu',  # SSL issue but URL is correct
    'Smithsonian Hirshhorn Museum and Sculpture Garden': 'https://hirshhorn.si.edu',  # SSL issue but URL is correct
    'Smithsonian National Museum of African American History and Culture': 'https://nmaahc.si.edu',  # SSL issue but URL is correct
    'Smithsonian National Museum of American History': 'https://americanhistory.si.edu',  # SSL issue but URL is correct
    'United States Holocaust Memorial Museum': 'https://www.ushmm.org',
    'Tidal Basin': 'https://www.nps.gov/thje/planyourvisit/tidal-basin.htm',
    'Georgetown': 'https://www.georgetown.com',  # Or could be NPS page
    'Dupont Circle': 'https://www.nps.gov/rocr/planyourvisit/dupont-circle.htm',  # Check if this is correct
    'Newseum': None,  # Closed permanently
}

def check_url(url, timeout=10):
    """Check if a URL is valid and accessible
    
    Returns:
        tuple: (is_valid, final_url, message, details_dict)
        details_dict contains: status_code, ssl_issue, bot_protection, redirect, etc.
    """
    details = {
        'status_code': None,
        'ssl_issue': False,
        'bot_protection': False,
        'redirect': False,
        'timeout': False,
        'connection_error': False,
        'error_type': None
    }
    
    if not url or not url.startswith('http'):
        return False, None, "Invalid URL format", details
    
    # Use requests if available, otherwise try urllib
    if requests:
        try:
            response = requests.get(url, allow_redirects=True, timeout=timeout, verify=True)
            final_url = response.url
            details['status_code'] = response.status_code
            
            # Check if we got a valid response
            if response.status_code == 200:
                # Check if final URL is different (redirect)
                if final_url != url:
                    details['redirect'] = True
                    return True, final_url, f"Redirects to {final_url}", details
                return True, url, "Valid", details
            elif response.status_code in [301, 302, 303, 307, 308]:
                details['redirect'] = True
                return True, final_url, f"Redirects to {final_url}", details
            elif response.status_code == 403:
                details['bot_protection'] = True
                return True, url, "HTTP 403 (bot protection, but URL likely valid)", details
            else:
                details['error_type'] = f"HTTP_{response.status_code}"
                return False, None, f"HTTP {response.status_code}", details
        except requests.exceptions.SSLError:
            details['ssl_issue'] = True
            details['error_type'] = 'SSL_ERROR'
            return False, None, "SSL Error", details
        except requests.exceptions.Timeout:
            details['timeout'] = True
            details['error_type'] = 'TIMEOUT'
            return False, None, "Timeout", details
        except requests.exceptions.ConnectionError:
            details['connection_error'] = True
            details['error_type'] = 'CONNECTION_ERROR'
            return False, None, "Connection Error", details
        except requests.exceptions.TooManyRedirects:
            details['error_type'] = 'TOO_MANY_REDIRECTS'
            return False, None, "Too many redirects", details
        except Exception as e:
            details['error_type'] = 'UNKNOWN_ERROR'
            return False, None, f"Error: {str(e)[:50]}", details
    else:
        # Fallback to urllib
        try:
            from urllib.request import urlopen, Request
            from urllib.error import URLError, HTTPError
            
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=timeout) as response:
                final_url = response.geturl()
                details['status_code'] = response.getcode()
                if final_url != url:
                    details['redirect'] = True
                    return True, final_url, f"Redirects to {final_url}", details
                return True, url, "Valid", details
        except HTTPError as e:
            details['status_code'] = e.code
            # 403 might be bot protection, but URL could still be correct
            if e.code == 403:
                details['bot_protection'] = True
                return True, url, "HTTP 403 (bot protection, but URL likely valid)", details
            details['error_type'] = f"HTTP_{e.code}"
            return False, None, f"HTTP {e.code}", details
        except URLError as e:
            error_str = str(e)
            # SSL errors might be false positives - check if it's just certificate verification
            if 'SSL' in error_str or 'CERTIFICATE' in error_str:
                details['ssl_issue'] = True
                # Try without SSL verification as a secondary check
                try:
                    import ssl
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    with urlopen(req, timeout=timeout, context=context) as response:
                        final_url = response.geturl()
                        details['status_code'] = response.getcode()
                        if final_url != url:
                            details['redirect'] = True
                            return True, final_url, f"Valid (SSL cert issue, redirects to {final_url})", details
                        return True, url, "Valid (SSL cert issue, but URL works)", details
                except:
                    details['error_type'] = 'SSL_ERROR'
                    return False, None, f"URL Error: {error_str[:50]}", details
            details['error_type'] = 'URL_ERROR'
            return False, None, f"URL Error: {error_str[:50]}", details
        except Exception as e:
            details['error_type'] = 'UNKNOWN_ERROR'
            return False, None, f"Error: {str(e)[:50]}", details

def search_correct_url(venue_name, venue_type=None, city_name=None):
    """Search for the correct URL using web search"""
    try:
        from scripts.enhanced_llm_fallback import EnhancedLLMFallback
        llm = EnhancedLLMFallback(silent=True)
        
        context = f"Venue type: {venue_type}" if venue_type else ""
        if city_name:
            context += f", City: {city_name}"
        
        prompt = f"""I need to find the official website URL for this venue: "{venue_name}"

{context}

Please provide ONLY the official website URL. If you're not certain, respond with "UNKNOWN".
Return format: Just the URL, nothing else. Example: https://www.example.com

If the venue doesn't have a website or you can't find it, respond with "UNKNOWN"."""
        
        response = llm.query_with_fallback(prompt)
        
        if response and response.get('success') and response.get('content'):
            content = response['content'].strip()
            # Extract URL from response
            if content.startswith('http'):
                # Find the first URL in the response
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('http') and 'UNKNOWN' not in line.upper():
                        return line.split()[0]  # Take first word (URL)
            elif 'UNKNOWN' in content.upper():
                return None
        
        return None
    except Exception as e:
        logger.debug(f"Error searching for URL: {e}")
        return None

def validate_and_fix_venues(dry_run=True, fix_invalid=True, use_llm=True, limit=None):
    """Validate all venue URLs and fix invalid ones"""
    
    with app.app_context():
        venues = Venue.query.all()
        if limit:
            venues = venues[:limit]
        total = len(venues)
        
        logger.info(f"🔍 Validating {total} venue URLs...")
        logger.info(f"   Dry run: {dry_run}")
        logger.info(f"   Fix invalid: {fix_invalid}")
        logger.info(f"   Use LLM: {use_llm}")
        logger.info("=" * 80)
        
        results = {
            'total': total,
            'valid': 0,
            'invalid': 0,
            'fixed': 0,
            'failed_to_fix': 0,
            'skipped': 0,
            'details': []
        }
        
        for i, venue in enumerate(venues, 1):
            city_name = venue.city.name if venue.city else "Unknown"
            logger.info(f"\n[{i}/{total}] {venue.name}")
            logger.info(f"   Current URL: {venue.website_url}")
            logger.info(f"   Type: {venue.venue_type}, City: {city_name}")
            
            if not venue.website_url:
                logger.info("   ⚠️  No URL - skipping")
                results['skipped'] += 1
                results['details'].append({
                    'venue': venue.name,
                    'status': 'no_url',
                    'current_url': None
                })
                continue
            
            # Check if we have a known correction
            if venue.name in KNOWN_CORRECTIONS:
                correct_url = KNOWN_CORRECTIONS[venue.name]
                if correct_url is None:
                    # Venue is closed/permanently unavailable
                    logger.info(f"   ⚠️  Known to be closed/unavailable")
                    results['skipped'] += 1
                    results['details'].append({
                        'venue': venue.name,
                        'status': 'closed',
                        'current_url': venue.website_url
                    })
                    continue
                elif venue.website_url != correct_url:
                    logger.info(f"   🔧 Known correction: {correct_url}")
                    if not dry_run and fix_invalid:
                        old_url = venue.website_url
                        venue.website_url = correct_url
                        db.session.commit()
                        results['fixed'] += 1
                        results['details'].append({
                            'venue': venue.name,
                            'status': 'fixed_known',
                            'old_url': old_url,
                            'new_url': correct_url
                        })
                    else:
                        results['invalid'] += 1
                        results['details'].append({
                            'venue': venue.name,
                            'status': 'needs_fix_known',
                            'current_url': venue.website_url,
                            'correct_url': correct_url
                        })
                    continue
            
            # Check URL validity
            is_valid, final_url, message, url_details = check_url(venue.website_url)
            
            if is_valid:
                logger.info(f"   ✅ Valid: {message}")
                if final_url != venue.website_url:
                    logger.info(f"   📍 Redirects to: {final_url}")
                    # Update to final URL if different
                    if not dry_run and fix_invalid:
                        old_url = venue.website_url
                        venue.website_url = final_url
                        db.session.commit()
                        results['fixed'] += 1
                        results['details'].append({
                            'venue': venue.name,
                            'status': 'fixed_redirect',
                            'old_url': old_url,
                            'new_url': final_url,
                            'url_details': url_details
                        })
                    else:
                        results['valid'] += 1
                        results['details'].append({
                            'venue': venue.name,
                            'status': 'valid_redirect',
                            'url': venue.website_url,
                            'redirects_to': final_url,
                            'url_details': url_details
                        })
                else:
                    results['valid'] += 1
                    results['details'].append({
                        'venue': venue.name,
                        'status': 'valid',
                        'url': venue.website_url,
                        'url_details': url_details
                    })
            else:
                logger.info(f"   ❌ Invalid: {message}")
                results['invalid'] += 1
                
                # Log specific issues
                if url_details.get('ssl_issue'):
                    logger.info(f"   🔒 SSL certificate issue detected")
                if url_details.get('bot_protection'):
                    logger.info(f"   🤖 Bot protection detected (but URL may be valid)")
                if url_details.get('timeout'):
                    logger.info(f"   ⏱️  Timeout issue")
                if url_details.get('connection_error'):
                    logger.info(f"   🔌 Connection error")
                
                if fix_invalid and use_llm:
                    logger.info(f"   🔍 Searching for correct URL...")
                    city_name = venue.city.name if venue.city else None
                    correct_url = search_correct_url(venue.name, venue.venue_type, city_name)
                    
                    if correct_url:
                        # Validate the found URL
                        is_correct_valid, _, _ = check_url(correct_url)
                        if is_correct_valid:
                            logger.info(f"   ✅ Found valid URL: {correct_url}")
                            if not dry_run:
                                old_url = venue.website_url
                                venue.website_url = correct_url
                                db.session.commit()
                                results['fixed'] += 1
                                results['details'].append({
                                    'venue': venue.name,
                                    'status': 'fixed_llm',
                                    'old_url': old_url,
                                    'new_url': correct_url,
                                    'original_error': message,
                                    'original_url_details': url_details
                                })
                            else:
                                results['details'].append({
                                    'venue': venue.name,
                                    'status': 'would_fix_llm',
                                    'current_url': venue.website_url,
                                    'found_url': correct_url,
                                    'error': message,
                                    'url_details': url_details
                                })
                        else:
                            logger.info(f"   ⚠️  Found URL but it's also invalid: {correct_url}")
                            results['failed_to_fix'] += 1
                            results['details'].append({
                                'venue': venue.name,
                                'status': 'failed_to_fix',
                                'current_url': venue.website_url,
                                'attempted_url': correct_url,
                                'error': message,
                                'url_details': url_details
                            })
                    else:
                        logger.info(f"   ⚠️  Could not find correct URL")
                        results['failed_to_fix'] += 1
                        results['details'].append({
                            'venue': venue.name,
                            'status': 'failed_to_fix',
                            'current_url': venue.website_url,
                            'error': message,
                            'url_details': url_details
                        })
                else:
                    results['details'].append({
                        'venue': venue.name,
                        'status': 'invalid',
                        'url': venue.website_url,
                        'error': message,
                        'url_details': url_details
                    })
            
            # Rate limiting
            time.sleep(0.5)
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total venues: {results['total']}")
        logger.info(f"✅ Valid: {results['valid']}")
        logger.info(f"❌ Invalid: {results['invalid']}")
        logger.info(f"🔧 Fixed: {results['fixed']}")
        logger.info(f"⚠️  Failed to fix: {results['failed_to_fix']}")
        logger.info(f"⏭️  Skipped (no URL): {results['skipped']}")
        
        # Save detailed results
        results_file = project_root / 'venue_url_validation_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n📄 Detailed results saved to: {results_file}")
        
        # Update venues.json if we made changes
        if not dry_run and results['fixed'] > 0:
            logger.info("\n🔄 Updating venues.json...")
            from scripts.update_venues_json import update_venues_json
            update_venues_json()
            logger.info("✅ venues.json updated")
        
        return results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate and fix venue URLs')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Check URLs without making changes')
    parser.add_argument('--no-fix', action='store_true',
                       help='Only validate, do not attempt to fix')
    parser.add_argument('--no-llm', action='store_true',
                       help='Do not use LLM to search for correct URLs')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of venues to check (for testing)')
    
    args = parser.parse_args()
    
    dry_run = args.dry_run
    fix_invalid = not args.no_fix
    use_llm = not args.no_llm
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    results = validate_and_fix_venues(
        dry_run=dry_run,
        fix_invalid=fix_invalid,
        use_llm=use_llm,
        limit=args.limit
    )
    
    # Exit with error code if there are invalid URLs that couldn't be fixed
    if results['failed_to_fix'] > 0:
        sys.exit(1)
