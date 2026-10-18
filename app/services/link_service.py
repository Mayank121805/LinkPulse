import re
import string
import secrets
from urllib.parse import urlparse
from datetime import datetime
from app.extensions import db
from app.models.link import Link
from app.models.blocked_domain import BlockedDomain
from app.models.tag import Tag

RESERVED_ALIASES = {
    'auth', 'login', 'register', 'logout', 'dashboard', 'links', 'campaigns',
    'analytics', 'qr-codes', 'import', 'settings', 'admin', 'api', 'static',
    'r', 'health', 'home', 'privacy', 'terms', 'help', 'app', 'user', 'me'
}

ALIAS_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')

def is_valid_url(url: str) -> tuple[bool, str]:
    """Validates destination URL: must be http/https, well-formed, and not blocked."""
    if not url or not isinstance(url, str):
        return False, "Destination URL is required."
    
    url = url.strip()
    if len(url) > 2048:
        return False, "URL exceeds maximum length of 2048 characters."
        
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False, "URL must start with http:// or https://"
        
    if not parsed.netloc:
        return False, "URL must have a valid domain name."
        
    domain = extract_domain(url).lower()
    
    # Check against blocked domains in database
    blocked = BlockedDomain.query.filter_by(domain=domain, is_active=True).first()
    if blocked:
        return False, f"Domain '{domain}' is blocked due to security or abuse policies: {blocked.reason}"
        
    return True, ""

def extract_domain(url: str) -> str:
    """Extracts base domain from a URL without port or www."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.split(':')[0].lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

def generate_short_code(length: int = 7) -> str:
    """Generates a secure, collision-resistant alphanumeric short code."""
    # Exclude easily confused characters: 0, O, I, l
    chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    max_attempts = 15
    for _ in range(max_attempts):
        code = ''.join(secrets.choice(chars) for _ in range(length))
        # Ensure code doesn't collide with existing short_code or custom_alias
        exists = Link.query.filter(
            (Link.short_code == code) | (Link.custom_alias == code)
        ).first()
        if not exists and code not in RESERVED_ALIASES:
            return code
            
    # Fallback to slightly longer code if collisions occur
    return ''.join(secrets.choice(chars) for _ in range(length + 2))

def validate_custom_alias(alias: str, exclude_link_id: int = None) -> tuple[bool, str]:
    """Validates custom alias format and uniqueness."""
    if not alias:
        return True, "" # Optional
        
    alias = alias.strip()
    if not ALIAS_REGEX.match(alias):
        return False, "Alias must be 3-50 characters long and contain only letters, numbers, hyphens, or underscores."
        
    if alias.lower() in RESERVED_ALIASES:
        return False, f"'{alias}' is a reserved platform keyword and cannot be used as an alias."
        
    query = Link.query.filter(
        (Link.custom_alias == alias) | (Link.short_code == alias)
    )
    if exclude_link_id:
        query = query.filter(Link.id != exclude_link_id)
        
    if query.first():
        return False, f"Alias '{alias}' is already in use. Please pick another one."
        
    return True, ""

def get_or_create_tags(user_id: int, tag_names: list[str]) -> list[Tag]:
    """Retrieves existing tags for user or creates new ones."""
    tags = []
    seen = set()
    for name in tag_names:
        clean_name = name.strip()
        if not clean_name or clean_name.lower() in seen:
            continue
        seen.add(clean_name.lower())
        
        tag = Tag.query.filter_by(user_id=user_id, name=clean_name).first()
        if not tag:
            # Pick a pleasant color from a palette
            palette = ['#2563EB', '#0EA5E9', '#10B981', '#8B5CF6', '#F59E0B', '#EC4899', '#6366F1']
            color = palette[len(clean_name) % len(palette)]
            tag = Tag(user_id=user_id, name=clean_name, color_code=color)
            db.session.add(tag)
        tags.append(tag)
    return tags
