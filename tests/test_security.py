import socket

import httpx
import pytest
from localvoiceai.webfetch import fetch_page, public_target


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com",
        "https://a:b@example.com",
        "http://example.com:8080",
        "http://127.0.0.1",
        "http://[::1]",
        "http://169.254.169.254",
        "http://10.0.0.1",
        "http://100.64.0.1",
    ],
)
async def test_unsafe_urls_rejected(url, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", (a[0], 80))])
    with pytest.raises(ValueError):
        await public_target(url)


async def test_mixed_dns_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [(2, 1, 6, "", (ip, 80)) for ip in ["93.184.216.34", "127.0.0.1"]],
    )
    with pytest.raises(ValueError, match="blocked"):
        await public_target("https://example.com")


async def test_redirect_cannot_reach_private_address(monkeypatch):
    import localvoiceai.webfetch as webfetch

    def dns(host, *a, **kw):
        return [(2, 1, 6, "", ("93.184.216.34" if host == "example.com" else "127.0.0.1", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.host == "93.184.216.34"
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(302, headers={"location": "http://localhost/secret"})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        webfetch.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    with pytest.raises(ValueError, match="blocked"):
        await fetch_page("https://example.com", 1000)
    assert len(requests) == 1
