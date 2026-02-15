"""API client for posting entries to Nox Dashboard."""
import os
import requests
from datetime import datetime


def _get_api_config():
    """Lazy evaluation of API configuration to avoid import-time side effects."""
    return {
        'base_url': os.getenv('NOX_API_URL', 'http://localhost:3000/api'),
        'api_key': os.getenv('NOX_API_KEY', '')
    }


def create_entry(category, type, title, content, source='auto-logger', 
                 confidence=80, metadata=None):
    """
    Create a new entry in the dashboard.
    
    Args:
        category: 'youtube', 'business', or 'investments'
        type: entry type (e.g., 'script_build', 'research', 'analysis')
        title: entry title
        content: full content/description
        source: where this came from
        confidence: confidence score (0-100)
        metadata: optional dict of additional data
        
    Returns:
        tuple: (success: bool, response_data: dict or None)
    """
    if metadata is None:
        metadata = {}
    
    payload = {
        'category': category,
        'type': type,
        'title': title,
        'content': content,
        'source': source,
        'confidence': confidence,
        'metadata': metadata,
        'verified': True
    }
    
    config = _get_api_config()
    
    try:
        headers = {'Content-Type': 'application/json'}
        if config['api_key']:
            headers['Authorization'] = f'Bearer {config["api_key"]}'
        
        response = requests.post(
            f'{config["base_url"]}/entries',
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        # DEFECT-002 FIX: Check status code explicitly instead of truthy check
        if response.status_code == 201:
            return True, response.json()
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        return False, None


def log_script_build(script_name, description, metadata=None):
    """Log a script build activity."""
    success, data = create_entry(
        category='youtube',
        type='script_build',
        title=f'Script: {script_name}',
        content=description,
        metadata=metadata or {}
    )
    return data if success else None


def log_research(topic, findings, metadata=None):
    """Log research activity."""
    success, data = create_entry(
        category='youtube',
        type='research_note',
        title=f'Research: {topic}',
        content=findings,
        metadata=metadata or {}
    )
    return data if success else None


def log_analysis(subject, analysis, metadata=None):
    """Log analysis activity."""
    success, data = create_entry(
        category='business',
        type='analysis',
        title=f'Analysis: {subject}',
        content=analysis,
        metadata=metadata or {}
    )
    return data if success else None


def log_activity(activity_type, title, description, category='youtube'):
    """Generic activity logger."""
    success, data = create_entry(
        category=category,
        type=activity_type,
        title=title,
        content=description
    )
    return data if success else None
