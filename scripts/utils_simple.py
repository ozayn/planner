#!/usr/bin/env python3
"""
SIMPLIFIED UTILITIES
Only the essential cleaning functions needed by app.py
"""

import re

def clean_text_field(value):
    """Clean text fields by removing markdown formatting and extra whitespace"""
    if not value:
        return None
    
    # Convert to string and strip whitespace
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Remove markdown links like [text](url) and keep just the text
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    
    # Remove markdown formatting
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)        # Code
    cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Headers
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_url_field(value):
    """Clean URL fields by removing markdown formatting and extracting URLs"""
    if not value:
        return None
    
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Extract URL from markdown link format [text](url)
    url_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', cleaned)
    if url_match:
        return url_match.group(2).strip()
    
    # Remove markdown formatting but keep the URL
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_email_field(value):
    """Clean email fields by extracting email from markdown links"""
    if not value:
        return None
    
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Extract email from markdown link format [email](mailto:email@domain.com)
    email_match = re.search(r'\[([^\]]+)\]\(mailto:([^)]+)\)', cleaned)
    if email_match:
        return email_match.group(2).strip()
    
    # Extract email from regular email format
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', cleaned)
    if email_match:
        return email_match.group(1).strip()
    
    # Clean markdown formatting
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_phone_field(value):
    """Clean phone number fields"""
    if not value:
        return None
    
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Remove markdown formatting
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_numeric_field(value):
    """Clean numeric fields (latitude, longitude, price, etc.)"""
    if not value:
        return None
    
    try:
        # Convert to string and clean markdown formatting first
        cleaned = str(value).strip()
        if not cleaned:
            return None
        
        # Remove markdown formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)        # Code
        cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Headers
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()        # Normalize whitespace
        
        if not cleaned:
            return None
            
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def clean_integer_field(value):
    """Clean integer fields (max_participants, etc.)"""
    if not value:
        return None
    
    try:
        # Convert to string and clean markdown formatting first
        cleaned = str(value).strip()
        if not cleaned:
            return None
        
        # Remove markdown formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)        # Code
        cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Headers
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()        # Normalize whitespace
        
        if not cleaned:
            return None
            
        return int(float(cleaned))  # Convert to int via float to handle "25.0"
    except (ValueError, TypeError):
        return None

