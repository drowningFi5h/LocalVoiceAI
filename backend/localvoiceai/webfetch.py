"""Bounded public-page fetch with DNS pinning and per-redirect address validation."""

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx


async def public_target(url: str):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a public HTTP/HTTPS URL without credentials.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("Only standard web ports are supported.")
    records = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, port, type=socket.SOCK_STREAM)
    ips = list(dict.fromkeys(r[4][0] for r in records))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("Private, loopback, reserved, and link-local addresses are blocked.")
    return parsed, ips[0]


async def fetch_page(url: str, max_bytes: int):
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
        for _ in range(6):
            parsed, ip = await public_target(url)
            # Connect to the validated IP, preserving Host and TLS certificate/SNI identity.
            target = httpx.URL(url).copy_with(host=ip)
            async with client.stream(
                "GET",
                target,
                headers={"Host": parsed.netloc, "User-Agent": "LocalVoiceAI/0.1 (single-page import)"},
                extensions={"sni_hostname": parsed.hostname},
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirect has no destination.")
                    url = urljoin(url, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not any(kind in content_type for kind in ("text/html", "text/plain", "application/xhtml")):
                    raise ValueError("This URL is not a readable HTML or text page.")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > max_bytes:
                        raise ValueError("Page exceeds the 5 MB import limit.")
                return bytes(data), url, content_type
        raise ValueError("Too many redirects.")
