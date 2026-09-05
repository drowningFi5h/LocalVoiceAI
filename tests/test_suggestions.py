from localvoiceai.suggestions import suggest_sources


def test_typo_topic_and_unrelated_queries():
    sources = [{"id": "one", "title": "Obsidian.pdf"}, {"id": "two", "title": "Station.md"}]
    chunks = [{"source_id": "two", "text": "Solar panels charge the battery."}]
    assert suggest_sources("Tell me about obsidan", sources, chunks)[0]["id"] == "one"
    assert suggest_sources("battery", sources, chunks)[0]["match"] == "Related topic"
    assert suggest_sources("Hello!", sources, chunks) == []
    assert suggest_sources("cooking noodles", sources, chunks) == []
