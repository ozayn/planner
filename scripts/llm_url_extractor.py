#!/usr/bin/env python3
"""
LLM-Based URL Event Extractor
Fallback for extracting event data when web scraping is blocked by bot protection
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.enhanced_llm_fallback import EnhancedLLMFallback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_event_with_llm(url: str, html_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract event data using LLM when web scraping fails.
    
    Args:
        url: The event page URL
        html_content: Optional HTML content if available (from user paste or other source)
    
    Returns:
        dict with extracted event data
    """
    try:
        llm = EnhancedLLMFallback(silent=True)
        
        # Build prompt based on what we have
        if html_content:
            prompt = f"""Extract event information from this HTML content for the URL: {url}

HTML Content:
{html_content[:10000]}  # Limit to 10k chars

Please extract and return ONLY a valid JSON object with these fields:
{{
    "title": "event title",
    "description": "event description",
    "start_time": "HH:MM format (24-hour) or null",
    "end_time": "HH:MM format (24-hour) or null",
    "location": "meeting point/location or null",
    "schedule_info": "recurring schedule like 'Fridays 6:30pm - 7:30pm' or null",
    "days_of_week": ["monday", "friday"] or [],
    "image_url": "image URL or null"
}}

Important:
- Return ONLY valid JSON, no other text
- Use 24-hour time format (e.g., "18:30" not "6:30pm")
- Extract actual schedule text if present (e.g., "Fridays 6:30pm - 7:30pm")
- Extract days as lowercase (monday, tuesday, etc.)
- Use null for missing fields, not empty strings"""
        else:
            # Check if this is an Instagram URL
            is_instagram = 'instagram.com' in url.lower() or 'instagr.am' in url.lower()
            
            if is_instagram:
                # Special prompt for Instagram posts
                prompt = f"""Extract event information from this Instagram post URL: {url}

Please visit or analyze this Instagram post and extract:
- The post caption/text content
- Any images (use the image URL if visible)
- Event details like dates, times, locations mentioned in the caption
- The username/handle of the account posting

Return ONLY a valid JSON object with these fields:
{{
    "title": "event title extracted from caption (first line or main heading)",
    "description": "full caption text or event description",
    "start_date": "YYYY-MM-DD format if date is mentioned, or null",
    "end_date": "YYYY-MM-DD format if end date is mentioned, or null",
    "start_time": "HH:MM format (24-hour) if time is mentioned, or null",
    "end_time": "HH:MM format (24-hour) if end time is mentioned, or null",
    "location": "location/venue mentioned in caption, or null",
    "image_url": "URL of the main image from the post, or null",
    "event_type": "exhibition/tour/workshop/performance/talk/event based on content",
    "social_media_platform": "instagram",
    "social_media_url": "{url}",
    "social_media_handle": "@username if visible, or null"
}}

Important:
- Return ONLY valid JSON, no other text
- Extract the actual caption text from the post
- Look for dates in formats like "January 15", "1/15/2025", "Jan 15-20", etc.
- Extract times like "6pm", "6:00 PM", "18:00"
- If the post is about an event, include all relevant details
- Use null for missing fields, not empty strings"""
            else:
                # Try with just the URL (LLM might know about common venues/events)
                prompt = f"""I need to extract event information from this URL, but the website is blocking web scrapers: {url}

Based on the URL structure and your knowledge, can you infer what this event might be? This appears to be from a museum or cultural institution.

Please provide your best estimate and return ONLY a valid JSON object with these fields:
{{
    "title": "estimated event title based on URL",
    "description": "brief description based on what you can infer",
    "start_time": null,
    "end_time": null,
    "location": null,
    "schedule_info": null,
    "days_of_week": [],
    "image_url": null,
    "llm_inferred": true,
    "confidence": "low/medium/high"
}}

Important:
- Return ONLY valid JSON, no other text
- Be honest about uncertainty - use low confidence if unsure
- Include llm_inferred: true to indicate this is an estimate
- Use null for fields you cannot infer"""

        # Get LLM response
        logger.info(f"Using LLM to extract event data from: {url}")
        llm_result = llm.query_with_fallback(prompt)
        
        if not llm_result or not llm_result.get('success'):
            logger.error(f"LLM query failed: {llm_result.get('error', 'Unknown error')}")
            return _empty_result()
        
        response = llm_result.get('content', '')
        
        logger.debug(f"LLM raw response: {response[:500]}")
        
        if not response:
            logger.error("LLM returned empty response")
            return _empty_result()
        
        # Parse JSON from response
        try:
            # Try to extract JSON from response (in case LLM adds extra text)
            response_text = response.strip()
            logger.debug(f"Response text (first 200 chars): {response_text[:200]}")
            
            # Find JSON object in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Validate and normalize the data
                result = {
                    'title': data.get('title'),
                    'description': data.get('description'),
                    'start_time': data.get('start_time'),
                    'end_time': data.get('end_time'),
                    'location': data.get('location'),
                    'schedule_info': data.get('schedule_info'),
                    'days_of_week': data.get('days_of_week', []),
                    'image_url': data.get('image_url'),
                    'llm_extracted': True,
                    'llm_inferred': data.get('llm_inferred', False),
                    'confidence': data.get('confidence', 'medium' if html_content else 'low')
                }
                
                logger.info(f"LLM successfully extracted: {result.get('title')}")
                return result
            else:
                logger.error(f"No JSON found in LLM response: {response_text[:200]}")
                return _empty_result()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response[:500]}")
            return _empty_result()
            
    except Exception as e:
        logger.error(f"Error in LLM extraction: {e}")
        import traceback
        traceback.print_exc()
        return _empty_result()


def extract_event_with_html_paste(url: str, pasted_html: str) -> Dict[str, Any]:
    """
    Extract event data from user-pasted HTML content.
    
    Args:
        url: The event page URL
        pasted_html: HTML content pasted by user
    
    Returns:
        dict with extracted event data
    """
    return extract_event_with_llm(url, pasted_html)


def _empty_result() -> Dict[str, Any]:
    """Return empty result structure"""
    return {
        'title': None,
        'description': None,
        'start_time': None,
        'end_time': None,
        'location': None,
        'schedule_info': None,
        'days_of_week': [],
        'image_url': None,
        'llm_extracted': False
    }


if __name__ == '__main__':
    # Test the LLM extractor
    test_url = "https://engage.metmuseum.org/events/public-guided-tours/collection-tour-islamic-art/"
    
    print(f"Testing LLM extraction for: {test_url}")
    result = extract_event_with_llm(test_url)
    
    print("\nExtracted Data:")
    print(json.dumps(result, indent=2))

