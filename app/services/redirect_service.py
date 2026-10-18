import hashlib
from datetime import datetime
from urllib.parse import urlparse
from user_agents import parse as parse_user_agent
from flask import Request, session
from app.extensions import db
from app.models.link import Link
from app.models.click_event import ClickEvent

def resolve_and_evaluate_link(code: str, request: Request, password: str = None) -> tuple[str, any]:
    """
    Evaluates short link redirection rules in strict order:
    1. Check existence -> 'not_found'
    2. Check active -> 'disabled'
    3. Check expiry -> 'expired'
    4. Check click limits -> 'limit_reached'
    5. Check password protection -> 'password_required' or unlock
    6. Record click event & atomically increment click count
    7. Return ('redirect', destination_url)
    """
    code = code.strip()
    link = Link.query.filter(
        (Link.custom_alias == code) | (Link.short_code == code)
    ).first()

    if not link:
        return 'not_found', None

    if not link.is_active:
        return 'disabled', link

    if link.is_expired:
        return 'expired', link

    if link.is_limit_reached:
        return 'limit_reached', link

    # Check password protection
    if link.is_password_protected:
        session_key = f'unlocked_link_{link.id}'
        is_session_unlocked = session.get(session_key) is True
        
        if password:
            if link.check_password(password):
                session[session_key] = True
            else:
                return 'invalid_password', link
        elif not is_session_unlocked:
            return 'password_required', link

    # Record click event
    try:
        record_click(link, request)
    except Exception as e:
        # Avoid blocking user redirect if click logging hits an edge error
        db.session.rollback()

    return 'redirect', link.destination_url

def record_click(link: Link, request: Request):
    """Parses visitor metadata and records click event with atomic counter increment."""
    ua_string = request.headers.get('User-Agent', '') or ''
    parsed_ua = parse_user_agent(ua_string)
    
    # Identify Bots
    is_bot = parsed_ua.is_bot or any(b in ua_string.lower() for b in ['bot', 'crawler', 'spider', 'curl', 'wget'])
    
    # Device category
    if is_bot:
        device_category = 'bot'
    elif parsed_ua.is_mobile:
        device_category = 'mobile'
    elif parsed_ua.is_tablet:
        device_category = 'tablet'
    else:
        device_category = 'desktop'
        
    browser = parsed_ua.browser.family if parsed_ua.browser.family else 'Unknown'
    os_name = parsed_ua.os.family if parsed_ua.os.family else 'Unknown'
    
    # Referrer parsing
    raw_referrer = request.referrer or request.headers.get('Referer', '') or 'Direct'
    referrer_domain = 'Direct'
    if raw_referrer and raw_referrer != 'Direct':
        try:
            ref_parsed = urlparse(raw_referrer)
            referrer_domain = ref_parsed.netloc.split(':')[0]
            if referrer_domain.startswith('www.'):
                referrer_domain = referrer_domain[4:]
            if not referrer_domain:
                referrer_domain = 'Direct'
        except Exception:
            referrer_domain = 'Direct'

    # IP & Geo determination
    # Support reverse-proxy headers (Cloudflare, nginx X-Forwarded-For)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip = forwarded_for.split(',')[0].strip()
    else:
        ip = request.remote_addr or '127.0.0.1'

    country = request.headers.get('CF-IPCountry', '')
    if not country:
        if ip in ('127.0.0.1', '::1', 'localhost'):
            country = 'Local Dev'
            city = 'Localhost'
        else:
            country = 'United States'
            city = 'New York'
    else:
        city = request.headers.get('CF-IPCity', 'Unknown')

    # Visitor Hash for privacy-preserving unique-visitor estimation
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    visitor_hash = hashlib.sha256(f"{ip}:{ua_string}:{today_str}".encode('utf-8')).hexdigest()[:32]

    # Create click record
    click_event = ClickEvent(
        link_id=link.id,
        timestamp=datetime.utcnow(),
        ip_address=ip,
        country=country,
        city=city,
        referrer=raw_referrer[:500],
        referrer_domain=referrer_domain[:120],
        user_agent=ua_string[:500],
        browser=browser[:60],
        os=os_name[:60],
        device_category=device_category,
        is_bot=is_bot,
        visitor_hash=visitor_hash
    )
    
    db.session.add(click_event)
    
    # Atomic increment to prevent race conditions during concurrent redirects
    db.session.query(Link).filter(Link.id == link.id).update(
        {Link.clicks_count: Link.clicks_count + 1},
        synchronize_session=False
    )
    
    db.session.commit()
