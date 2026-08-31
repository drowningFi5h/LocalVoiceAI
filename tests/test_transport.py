import asyncio
from types import SimpleNamespace

from localvoiceai.transport import Conversation


class Socket:
    def __init__(self):
        self.events = []

    async def send_json(self, event):
        self.events.append(event)


class SlowPipeline:
    async def run(self, state, emit):
        await emit({"type": "answer_delta", "text": "A partial answer. "})
        await asyncio.sleep(60)


async def test_cancel_persists_partial_and_drops_late_events(db):
    socket = Socket()
    session_id = db.session()
    services = SimpleNamespace(db=db, pipeline=SlowPipeline())
    connection = Conversation(socket, session_id, services)
    await connection.start(question="Battery?")
    await asyncio.sleep(0.02)
    old = connection.turn_id
    await connection.cancel()
    await connection.send({"type": "audio", "wav": "stale"}, old)
    assert db.history(session_id)[0]["answer"] == "A partial answer. "
    assert db.history(session_id)[0]["played"] == ""
    assert db.history(session_id)[0]["status"] == "interrupted"
    assert not any(e["type"] == "audio" for e in socket.events)
    assert connection.task.done()


async def test_new_question_has_new_turn_id(db):
    connection = Conversation(Socket(), db.session(), SimpleNamespace(db=db, pipeline=SlowPipeline()))
    await connection.start(question="First?")
    first = connection.turn_id
    await asyncio.sleep(0.02)
    await connection.start(question="Second?")
    assert first != connection.turn_id
    await asyncio.sleep(0.02)
    await connection.cancel()
    assert len(db.history(connection.session_id)) == 2


async def test_provider_failure_is_visible_and_persisted(db):
    class Failing:
        async def run(self, state, emit):
            raise ConnectionError("Model unavailable")

    socket = Socket()
    connection = Conversation(socket, db.session(), SimpleNamespace(db=db, pipeline=Failing()))
    await connection.start(question="Question")
    await connection.task
    assert db.history(connection.session_id)[0]["status"] == "error"
    assert any(e["type"] == "error" and "Model unavailable" in e["message"] for e in socket.events)


async def test_provider_errors_redact_keys(db):
    class Failing:
        async def run(self, state, emit):
            raise ConnectionError("Provider rejected test-secret-key")

    socket = Socket()
    services = SimpleNamespace(
        db=db,
        pipeline=Failing(),
        models=SimpleNamespace(settings=SimpleNamespace(cloud_api_key="test-secret-key")),
    )
    connection = Conversation(socket, db.session(), services)
    await connection.start(question="Generic test")
    await connection.task
    message = next(e["message"] for e in socket.events if e["type"] == "error")
    assert "test-secret-key" not in message
    assert "[redacted]" in message


async def test_interrupt_after_generation_marks_unplayed_audio(db):
    from localvoiceai.db import now

    session_id = db.session()
    db.execute(
        "INSERT INTO turns(id,session_id,question,answer,status,mode,provider,created) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("turn-a", session_id, "Q", "Completed text", "complete", "baseline", "local", now()),
    )
    connection = Conversation(Socket(), session_id, SimpleNamespace(db=db))
    connection.turn_id = "turn-a"
    connection.audio_chunks["audio-a"] = ("turn-a", "Unplayed sentence")
    await connection.cancel()
    turn = db.history(session_id)[0]
    assert turn["answer"] == "Completed text"
    assert turn["played"] == ""
    assert turn["status"] == "interrupted"
