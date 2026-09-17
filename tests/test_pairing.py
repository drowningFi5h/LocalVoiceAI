import json

import pytest
from fastapi.testclient import TestClient
from localvoiceai.app import create_app
from localvoiceai.pairing import validate_origin
from starlette.websockets import WebSocketDisconnect


def test_hosted_pairing_http_and_websocket(settings):
    origin = "https://my-studio.vercel.app"
    token = "a" * 43
    (settings.data_dir / "workspace-pairing.json").write_text(json.dumps({"origin": origin, "token": token}))
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        assert client.get("/api/health").status_code == 200
        denied = client.get("/api/health", headers={"Origin": origin})
        assert denied.status_code == 401
        assert denied.headers["access-control-allow-origin"] == origin
        headers = {"Origin": origin, "Authorization": "Bearer " + token}
        health = client.get("/api/health", headers=headers)
        assert health.json()["workspace_protocol"] == 1
        assert token not in health.text
        assert client.get("/api/sources", headers={**headers, "Origin": "https://other.example"}).status_code == 403
        assert client.get("/api/sources", headers={**headers, "Authorization": "Bearer wrong"}).status_code == 401
        preflight = client.options("/api/sessions", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
        assert preflight.status_code == 200
        session = client.post("/api/sessions", headers=headers).json()["id"]
        for protocols in ([], ["lva-pair.wrong"]):
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(f"ws://127.0.0.1/api/ws/{session}", headers={"Origin": origin}, subprotocols=protocols):
                    pass
        with client.websocket_connect(f"ws://127.0.0.1/api/ws/{session}", headers={"Origin": origin}, subprotocols=["lva-pair." + token]) as ws:
            assert ws.receive_json()["type"] == "ready"


@pytest.mark.parametrize("origin", ["http://site.example", "https://user:pass@site.example", "https://site.example/path", "https://site.example?q=1"])
def test_pairing_requires_exact_https_origin(origin):
    with pytest.raises(ValueError):
        validate_origin(origin)
