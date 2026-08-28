import json

from localvoiceai.evaluation import ROOT, summarize


def test_benchmark_has_40_cases_and_real_source_references():
    cases = json.loads((ROOT / "sample_data" / "benchmark.json").read_text())
    assert len(cases) == len({c["id"] for c in cases}) == 40
    assert len([c for c in cases if not c["expected_sources"]]) == 10
    for case in cases:
        for title in case["expected_sources"]:
            assert (ROOT / "sample_data" / "documents" / title).exists()


def test_human_metrics_are_absent_until_reviewed():
    row = {
        "mode": "baseline",
        "expected_sources": ["a"],
        "recall_at_5": 1,
        "abstained": False,
        "latency_ms": 123,
        "citations": [{"id": "one"}],
        "review": None,
    }
    result = summarize([row])["baseline"]
    assert result["recall_at_5"] == 1
    assert result["answer_correctness"] is None
    row["review"] = {"answer_correct": True, "citations_supported": False}
    result = summarize([row])["baseline"]
    assert result["answer_correctness"] == 1
    assert result["citation_correctness"] == 0
