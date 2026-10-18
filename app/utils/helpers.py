import os
from urllib.parse import urlparse
from flask import request, current_app

def is_local_address(host_str):
    if not host_str:
        return True
    hostname = host_str.split(':')[0].strip().lower()
    if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
        return True
    if hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('169.254.'):
        return True
    if hostname.startswith('172.'):
        try:
            second_octet = int(hostname.split('.')[1])
            if 16 <= second_octet <= 31:
                return True
        except (IndexError, ValueError):
            pass
    return False

def get_effective_base_url():
    """
    Returns the public base URL for short links and QR codes:
    1. If the request arrived through Cloudflare Tunnel or a public proxy,
       use the public domain (HTTPS).
    2. If the request arrived directly from a public hostname (e.g. *.trycloudflare.com),
       use https://{host}.
    3. If accessed locally (localhost or local Wi-Fi 192.168.x.x):
       - If a public BASE_URL (e.g. active Cloudflare tunnel) is configured in .env, use that.
       - Otherwise use request.host_url with http:// (never https:// on local IP).
    """
    configured = (os.environ.get('BASE_URL') or current_app.config.get('BASE_URL') or '').rstrip('/')
    
    try:
        req_host = request.headers.get('X-Forwarded-Host') or request.host
        
        # If accessing via public tunnel domain (like trycloudflare.com or custom domain)
        if req_host and not is_local_address(req_host):
            return f"https://{req_host}".rstrip('/')
            
        # If accessing via local IP or localhost:
        if configured and not is_local_address(urlparse(configured).hostname):
            return configured
            
        # Fallback to local request host over plain http (never https to avoid error 400)
        if req_host:
            return f"http://{req_host}".rstrip('/')
    except Exception:
        pass

    return configured or 'http://localhost:5000'
