"""API client for posting entries to Nox Dashboard."""
import os
import requests
from datetime import datetime

API_BASE_URL = os.getenv('NOX_API_URL', 'http://localhost:3000/api')
API_KEY = os.getenv('NOX_API_KEY', '')

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
    
    try:
        headers = {'Authorization': f'Bearer {API_KEY}'} if API_KEY else {}
        response = requests.post(
            f'{API_BASE_URL}/entries',
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        return None

def log_script_build(script_name, description, metadata=None):
    """Log a script build activity."""
    return create_entry(
        category='youtube',
        type='script_build',
        title=f'Script: {script_name}',
        content=description,
        metadata=metadata or {}
    )

def log_research(topic, findings, metadata=None):
    """Log research activity."""
    return create_entry(
        category='youtube',
        type='research_note',
        title=f'Research: {topic}',
        content=findings,
        metadata=metadata or {}
    )

def log_analysis(subject, analysis, metadata=None):
    """Log analysis activity."""
    return create_entry(
        category='business',
        type='analysis',
        title=f'Analysis: {subject}',
        content=analysis,
        metadata=metadata or {}
    )

def log_activity(activity_type, title, description, category='youtube'):
    """Generic activity logger."""
    return create_entry(
        category=category,
        type=activity_type,
        title=title,
        content=description
    )
