import pytest
from conftest import FakeModels, FakeRetrieval
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from localvoiceai.graph import ABSTENTION, Pipeline, initial_state, valid_citations


@pytest.mark.parametrize(
    "mode,expected",
    [("baseline", ["retrieve", "answer"]), ("graph", ["resolve", "retrieve", "assess", "answer"])],
)
async def test_modes_emit_trace_and_grounded_citations(mode, expected):
    events = []

    async def emit(event):
        events.append(event)

    retrieval = FakeRetrieval()
    pipeline = Pipeline(retrieval, FakeModels(), InMemorySaver())
    result = await pipeline.run(initial_state("session-a", "Battery capacity?", mode, "local"), emit)
    assert [e["node"] for e in events if e["type"] == "node" and e["status"] == "complete"] == expected
    assert result["citations"][0]["id"] == "chunk-1"
    assert retrieval.calls[0][1] == (mode == "graph")
    assert result["trace"]["usage"]["output_tokens"] == 10


async def test_retry_is_bounded_and_abstains():
    retrieval = FakeRetrieval()
    pipeline = Pipeline(retrieval, FakeModels(False), InMemorySaver())

    async def emit(event):
        pass

    result = await pipeline.run(initial_state("a", "Unknown?", "graph", "local"), emit)
    assert len(retrieval.calls) == 2
    assert result["retry_count"] == 1
    assert result["answer"] == ABSTENTION
    assert result["citations"] == []


async def test_empty_baseline_does_not_invent_answer():
    async def emit(event):
        pass

    result = await Pipeline(FakeRetrieval([]), FakeModels(), InMemorySaver()).run(
        initial_state("empty", "Anything?", "baseline", "local"), emit
    )
    assert result["abstained"]


async def test_empty_graph_abstains_without_model_calls():
    async def emit(event):
        pass

    model = FakeModels()
    result = await Pipeline(FakeRetrieval([]), model, InMemorySaver()).run(
        initial_state("empty-graph", "Anything?", "graph", "local"), emit
    )
    assert result["abstained"]
    assert model.calls == []


@pytest.mark.parametrize(
    "decision,expected", [("CHAT", "chat"), ("SOURCES", "sources"), ("unclear", "sources")]
)
async def test_conversation_routes_without_weakening_source_grounding(decision, expected):
    class RoutedModels(FakeModels):
        async def complete(self, provider, system, text):
            return decision

        async def stream(self, provider, system, text):
            assert "LocalVoice" in system
            yield {"text": "Hey! What are you curious about today?"}

    retrieval = FakeRetrieval([])
    events = []

    async def emit(event):
        events.append(event)

    result = await Pipeline(retrieval, RoutedModels(), InMemorySaver()).run(
        initial_state("chat-test", "Hello", "graph", "local", conversational=True), emit
    )
    assert result["trace"]["intent"] == expected
    assert result["citations"] == []
    if expected == "chat":
        assert not retrieval.calls
        assert result["answer"].startswith("Hey!")
        assert not result["abstained"]
    else:
        assert result["answer"] == ABSTENTION


async def test_checkpoint_survives_restart_and_isolates_sessions(tmp_path):
    path = str(tmp_path / "checkpoints.sqlite")

    async def emit(event):
        pass

    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        await saver.setup()
        await Pipeline(FakeRetrieval(), FakeModels(), saver).run(
            initial_state("private-session", "Battery?", "graph", "local"), emit
        )
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        saved = await saver.aget_tuple({"configurable": {"thread_id": "private-session"}})
        assert saved.checkpoint["channel_values"]["question"] == "Battery?"
        assert await saver.aget_tuple({"configurable": {"thread_id": "another-session"}}) is None


def test_citation_ids_must_exist_in_retrieved_passages():
    refs = valid_citations("Claim [1], invented [999] and repeated [1].", FakeRetrieval().passages)
    assert len(refs) == 1 and refs[0]["number"] == 1
