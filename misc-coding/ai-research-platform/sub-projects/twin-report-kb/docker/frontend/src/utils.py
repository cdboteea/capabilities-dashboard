"""Utility functions for Twin-Report KB Frontend."""

import os
import uuid
import hashlib
import mimetypes
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return str(uuid.uuid4())


def generate_document_id() -> str:
    """Generate a unique document ID."""
    return str(uuid.uuid4())


def get_file_hash(file_data: bytes) -> str:
    """Generate SHA-256 hash of file data."""
    return hashlib.sha256(file_data).hexdigest()


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def is_allowed_file(filename: str, allowed_extensions: List[str]) -> bool:
    """Check if file extension is allowed."""
    if not filename:
        return False
    
    _, ext = os.path.splitext(filename.lower())
    return ext in [ext.lower() for ext in allowed_extensions]


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def format_processing_time(seconds: float) -> str:
    """Format processing time in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display."""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days < 7:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    else:
        return timestamp.strftime("%Y-%m-%d %H:%M")


def calculate_progress_percentage(current_step: str, total_steps: List[str]) -> float:
    """Calculate progress percentage based on current step."""
    try:
        current_index = total_steps.index(current_step)
        return (current_index + 1) / len(total_steps) * 100
    except ValueError:
        return 0.0


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL."""
    import re
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def extract_google_doc_id(url_or_id: str) -> Optional[str]:
    """Extract Google Doc ID from URL or return ID if already extracted."""
    import re
    
    # If it's already just an ID
    if len(url_or_id) == 44 and url_or_id.replace('-', '').replace('_', '').isalnum():
        return url_or_id
    
    # Extract from various Google Docs URL formats
    patterns = [
        r'/document/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
        r'/presentation/d/([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Ensure it's not empty and not too long
    if not filename:
        filename = "document"
    
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename


def create_error_response(error: str, details: Optional[str] = None) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "success": False,
        "error": error,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }


def create_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def get_file_type_icon(filename: str) -> str:
    """Get appropriate icon class for file type."""
    _, ext = os.path.splitext(filename.lower())
    
    icon_map = {
        '.pdf': 'fas fa-file-pdf',
        '.doc': 'fas fa-file-word',
        '.docx': 'fas fa-file-word',
        '.xls': 'fas fa-file-excel',
        '.xlsx': 'fas fa-file-excel',
        '.ppt': 'fas fa-file-powerpoint',
        '.pptx': 'fas fa-file-powerpoint',
        '.txt': 'fas fa-file-alt',
        '.html': 'fas fa-file-code',
        '.htm': 'fas fa-file-code',
        '.md': 'fas fa-file-alt',
    }
    
    return icon_map.get(ext, 'fas fa-file')


def get_status_color(status: str) -> str:
    """Get appropriate color class for status."""
    color_map = {
        'pending': 'text-warning',
        'parsing': 'text-info',
        'categorizing': 'text-info',
        'quality_check': 'text-info',
        'analyzing': 'text-info',
        'completed': 'text-success',
        'failed': 'text-danger',
        'healthy': 'text-success',
        'unhealthy': 'text-danger',
        'unknown': 'text-muted'
    }
    
    return color_map.get(status.lower(), 'text-muted')


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def parse_processing_steps() -> List[str]:
    """Get the standard processing steps in order."""
    return [
        "pending",
        "parsing", 
        "categorizing",
        "quality_check",
        "analyzing",
        "completed"
    ]


def calculate_success_rate(completed: int, failed: int) -> float:
    """Calculate success rate percentage."""
    total = completed + failed
    if total == 0:
        return 100.0
    
    return (completed / total) * 100


def group_by_date(items: List[Dict[str, Any]], date_field: str = "timestamp") -> Dict[str, List[Dict[str, Any]]]:
    """Group items by date."""
    groups = {}
    
    for item in items:
        if date_field in item:
            date_str = item[date_field]
            if isinstance(date_str, str):
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_key = date_obj.strftime("%Y-%m-%d")
                except:
                    date_key = "Unknown"
            elif isinstance(date_str, datetime):
                date_key = date_str.strftime("%Y-%m-%d")
            else:
                date_key = "Unknown"
        else:
            date_key = "Unknown"
        
        if date_key not in groups:
            groups[date_key] = []
        groups[date_key].append(item)
    
    return groups


def filter_recent_items(items: List[Dict[str, Any]], days: int = 7, date_field: str = "timestamp") -> List[Dict[str, Any]]:
    """Filter items to only include recent ones."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    recent_items = []
    
    for item in items:
        if date_field in item:
            date_str = item[date_field]
            try:
                if isinstance(date_str, str):
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                elif isinstance(date_str, datetime):
                    date_obj = date_str
                else:
                    continue
                
                if date_obj >= cutoff_date:
                    recent_items.append(item)
            except:
                continue
    
    return recent_items 