import ipaddress
import socket
from urllib.parse import urlparse
from app.core.config import settings

def validate_target_url(url: str) -> str:
    print("--- DEBUG SSRF ---")
    print("ALLOW_INTERNAL_TARGETS VALUE:", settings.ALLOW_INTERNAL_TARGETS)
    print("------------------")
    
    parsed = urlparse(url)
    # Schema and hostname validation
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only 'http' and 'https' schemes are allowed.")
    if not parsed.hostname:
        raise ValueError("Invalid URL format")

    try:
        # DNS resolution
        resolved_ip_str = socket.gethostbyname(parsed.hostname)
        ip = ipaddress.ip_address(resolved_ip_str)

        # Blocked Internal, Loopback and Cloud Metadata IPs
        if ip.is_loopback or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise ValueError("Target resolves to a restricted IP")
        # Conditionally allow Private Network IPs (192.168.x.x, 10.x.x.x)
        if ip.is_private and not settings.ALLOW_INTERNAL_TARGETS:
            raise ValueError("Internal network testing is disabled. Turn on ALLOW_INTERNAL_TARGETS in .env")
        


    except socket.gaierror:
        raise ValueError("Cannot resolve target host")
    return url