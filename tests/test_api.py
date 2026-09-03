from conftest import FakeModels
from fastapi.testclient import TestClient
from localvoiceai.app import create_app


def test_api_sessions_health_origins_and_validation(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        client.app.state.s.pipeline.models = FakeModels()
        assert client.get("/api/health").json()["status"] == "ok"
        assert "cloud_api_key" not in client.get("/api/health").json()
        first = client.post("/api/sessions").json()["id"]
        second = client.post("/api/sessions").json()["id"]
        assert first != second
        assert client.get(f"/api/sessions/{first}").json() == []
        assert client.get("/api/sessions/missing").status_code == 404
        assert client.post("/api/sessions", headers={"origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/sources/upload", files={"file": ("bad.exe", b"data")}).status_code == 422
        assert client.post("/api/sources/upload", files={"file": ("empty.txt", b"")}).status_code == 413
        assert client.post("/api/evaluations", json={"provider": "local"}).status_code == 409
        with client.websocket_connect(
            f"ws://127.0.0.1/api/ws/{first}", headers={"origin": "http://127.0.0.1:5173"}
        ) as socket:
            assert socket.receive_json()["type"] == "ready"
            socket.send_json({"type": "text", "text": "No corpus question", "mode": "baseline"})
            events = []
            while True:
                event = socket.receive_json()
                events.append(event)
                if event["type"] == "turn_end":
                    break
            assert any(e["type"] == "answer_delta" and "enough evidence" in e["text"] for e in events)
        assert len(client.get(f"/api/sessions/{first}").json()) == 1
        assert client.get(f"/api/sessions/{second}").json() == []


def test_user_provider_key_is_memory_only_and_never_returned(settings):
    original = settings.cloud_api_key
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        key = "test-private-key-123456"
        for provider in ("gemini", "openai", "groq", "openrouter"):
            response = client.post(
                "/api/provider",
                json={
                    "provider": provider,
                    "model": "my-model",
                    "api_key": key,
                },
            )
            assert response.status_code == 200
            assert key not in response.text
            assert response.json()["cloud_override"] is True
            assert settings.cloud_api_key == key
            assert settings.cloud_backend == ("gemini" if provider == "gemini" else "openai")
        bad = client.post("/api/provider", json={"provider": "unknown", "api_key": key})
        assert bad.status_code == 422 and key not in bad.text
        forbidden = client.post(
            "/api/provider",
            headers={"Origin": "https://evil.example"},
            json={
                "provider": "gemini",
                "model": "my-model",
                "api_key": key,
            },
        )
        assert forbidden.status_code == 403
        assert client.delete("/api/provider").json()["cloud_override"] is False
        assert settings.cloud_api_key == original
    assert not any(key.encode() in p.read_bytes() for p in settings.data_dir.rglob("*") if p.is_file())


def test_provider_changes_blocked_during_voice(settings):
    from types import SimpleNamespace

    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        app.state.s.conversations["busy"] = SimpleNamespace(voice=True)
        assert (
            client.post(
                "/api/provider",
                json={
                    "provider": "gemini",
                    "model": "model",
                    "api_key": "test-only-key",
                },
            ).status_code
            == 409
        )
        assert client.delete("/api/provider").status_code == 409
        app.state.s.conversations.clear()


def test_connection_management_retains_keys_without_returning_them(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        a = client.post(
            "/api/provider",
            json={"provider": "groq", "name": "Fast", "model": "first", "api_key": "private-test-key"},
        ).json()["cloud_connection_id"]
        b = client.post(
            "/api/provider", json={"provider": "openrouter", "model": "second", "api_key": "another-test-key"}
        ).json()["cloud_connection_id"]
        listing = client.get("/api/provider/connections")
        assert len(listing.json()) == 2
        assert "private-test-key" not in listing.text and "another-test-key" not in listing.text
        assert client.post(f"/api/provider/connections/{a}/activate").json()["cloud_model"] == "first"
        edited = client.post(
            "/api/provider", json={"id": a, "provider": "groq", "model": "updated", "name": "Fast v2"}
        )
        assert edited.status_code == 200 and settings.cloud_api_key == "private-test-key"
        assert client.delete(f"/api/provider/connections/{a}").json()["cloud_override"] is False
        assert client.post(f"/api/provider/connections/{a}/activate").status_code == 404
        assert client.get("/api/provider/connections").json()[0]["id"] == b
