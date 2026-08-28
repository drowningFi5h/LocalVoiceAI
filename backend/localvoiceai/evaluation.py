import asyncio
import json
import math
from pathlib import Path
from uuid import uuid4

from .db import now
from .graph import initial_state

ROOT = Path(__file__).resolve().parents[2]


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(p * len(values)) - 1)]


def summarize(rows):
    result = {}
    for mode in ("baseline", "graph"):
        items = [r for r in rows if r["mode"] == mode and "error" not in r]
        answerable = [r for r in items if r["expected_sources"]]
        unanswerable = [r for r in items if not r["expected_sources"]]
        reviewed = [r for r in items if r.get("review") is not None]
        citation_reviews = [r for r in reviewed if r["citations"]]
        result[mode] = {
            "completed": len(items),
            "errors": sum("error" in r for r in rows if r["mode"] == mode),
            "recall_at_5": sum(r["recall_at_5"] for r in answerable) / len(answerable)
            if answerable
            else None,
            "abstention_accuracy": sum(r["abstained"] for r in unanswerable) / len(unanswerable)
            if unanswerable
            else None,
            "answer_correctness": sum(r["review"]["answer_correct"] for r in reviewed) / len(reviewed)
            if reviewed
            else None,
            "citation_correctness": sum(r["review"]["citations_supported"] for r in citation_reviews)
            / len(citation_reviews)
            if citation_reviews
            else None,
            "reviewed": len(reviewed),
            "p50_ms": percentile([r["latency_ms"] for r in items], 0.5),
            "p95_ms": percentile([r["latency_ms"] for r in items], 0.95),
        }
    return result


class Evaluations:
    def __init__(self, db, pipeline):
        self.db, self.pipeline = db, pipeline
        self.tasks = set()

    def start(self, provider):
        run_id = str(uuid4())
        self.db.execute(
            "INSERT INTO evaluations VALUES (?,?,?,?)",
            (run_id, "running", json.dumps({"rows": [], "provider": provider}), now()),
        )
        task = asyncio.create_task(self.run(run_id, provider))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return run_id

    async def run(self, run_id, provider):
        rows = []
        try:
            cases = json.loads((ROOT / "sample_data" / "benchmark.json").read_text(encoding="utf-8"))
            for case in cases:
                for mode in ("baseline", "graph"):

                    async def discard(event):
                        pass

                    row = {**case, "mode": mode, "review": None}
                    try:
                        result = await self.pipeline.run(
                            initial_state(
                                f"eval:{run_id}:{case['id']}:{mode}",
                                case["question"],
                                mode,
                                provider,
                                case.get("history", []),
                            ),
                            discard,
                        )
                        found = {p["title"] for p in result["passages"]}
                        expected = set(case["expected_sources"])
                        row.update(
                            answer=result["answer"],
                            citations=result["citations"],
                            passages=result["passages"],
                            trace=result["trace"],
                            abstained=result["abstained"],
                            latency_ms=result["trace"]["elapsed_ms"],
                            recall_at_5=len(found & expected) / len(expected) if expected else None,
                        )
                    except Exception as exc:
                        row["error"] = str(exc)[:500]
                    rows.append(row)
                    self.db.execute(
                        "UPDATE evaluations SET result=? WHERE id=?",
                        (
                            json.dumps({"provider": provider, "rows": rows, "summary": summarize(rows)}),
                            run_id,
                        ),
                    )
            self.db.execute("UPDATE evaluations SET status='complete' WHERE id=?", (run_id,))
        except asyncio.CancelledError:
            self.db.execute("UPDATE evaluations SET status='interrupted' WHERE id=?", (run_id,))
            raise
        except Exception as exc:
            self.db.execute(
                "UPDATE evaluations SET status='error',result=? WHERE id=?",
                (json.dumps({"rows": rows, "error": str(exc)[:500]}), run_id),
            )
