import argparse
import json
import pathlib
import re
import sys
import time
from typing import Any
from pyoxigraph import QuerySolutions, Store
from tabulate import tabulate


HEADER_KEY = re.compile(r"^#\s*(\w+):\s*(.*)$")


def read_cq(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    meta: dict[str, str] = {}
    key = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            if line.strip():
                break
            continue
        match = HEADER_KEY.match(line)
        if match:
            key = match.group(1).lower()
            meta[key] = match.group(2).strip()
        elif key:
            meta[key] = (meta[key] + " " + line.lstrip("#").strip()).strip()
    return {
        "id": meta.get("id", path.stem),
        "question": meta.get("question", ""),
        "file": path.relative_to(root).as_posix(),
        "query": path.read_text(encoding="utf-8"),
    }


def term_value(term: Any) -> str | None:
    if term is None:
        return None
    return term.value if hasattr(term, "value") else str(term)


def run_cq(store: Store, cq: dict[str, Any]) -> dict[str, Any]:
    result = {k: cq[k] for k in ("id", "question", "file")}
    start = time.perf_counter()
    try:
        answer = store.query(cq["query"])
        if isinstance(answer, bool):  # ASK
            variables, rows = ["result"], [{"result": answer}] if answer else []
        elif isinstance(answer, QuerySolutions):  # SELECT
            variables = [v.value for v in answer.variables]
            rows = [{v: term_value(s[v]) for v in variables} for s in answer]
        else:  # CONSTRUCT / DESCRIBE
            variables = ["subject", "predicate", "object"]
            rows = [dict(zip(variables, (term_value(t.subject), term_value(t.predicate), term_value(t.object))))
                    for t in answer]
    except Exception as e:  # a malformed query must not stop the other CQs
        result.update(status="error", error=str(e), seconds=round(time.perf_counter() - start, 3))
        return result
    result.update(
        status="answered" if rows else "empty",
        seconds=round(time.perf_counter() - start, 3),
        count=len(rows),
        variables=variables,
        rows=rows,
    )
    return result


def print_result(result: dict[str, Any], max_rows: int) -> None:
    print(f"\n{result['id']} [{result['status']}] {result['question']}")
    if result["status"] == "error":
        print(f"  error: {result['error']}")
        return
    rows = result["rows"]
    if rows:
        shown = [[r[v] for v in result["variables"]] for r in rows[:max_rows]]
        print(tabulate(shown, headers=result["variables"], tablefmt="psql", disable_numparse=True))
    more = f", {len(rows) - max_rows} more in the report" if len(rows) > max_rows else ""
    print(f"  {len(rows)} results in {result['seconds']}s{more}")


def main():

    parser = argparse.ArgumentParser(description="Run the competency questions (SPARQL queries) against the knowledge graph.")
    parser.add_argument("--data", default="data.ttl", help="Turtle file to query (default: data.ttl)")
    parser.add_argument("--cqs", default="cqs", help="directory with one .rq file per competency question (default: cqs)")
    parser.add_argument("--output", default="cq_results.json", help="JSON report with all the results (default: cq_results.json)")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these competency questions (e.g. CQ_001 CQ_014)")
    parser.add_argument("--max-rows", type=int, default=20, help="rows shown per competency question in the terminal (default: 20)")
    parser.add_argument("--strict", action="store_true", help="also exit with an error when a competency question has no results")
    args = parser.parse_args()

    root = pathlib.Path(__file__).parent
    cqs = [read_cq(p, root) for p in sorted((root / args.cqs).glob("*.rq"))]
    if args.only:
        cqs = [cq for cq in cqs if cq["id"] in args.only]
    if not cqs:
        sys.exit(f"No competency questions found in {args.cqs}/")

    store = Store()
    store.bulk_load(str(root / args.data), "text/turtle")

    results = []
    for cq in cqs:
        result = run_cq(store, cq)
        print_result(result, args.max_rows)
        results.append(result)

    summary = {s: sum(r["status"] == s for r in results) for s in ("answered", "empty", "error")}
    print(f"\n{len(results)} competency questions: " + ", ".join(f"{n} {s}" for s, n in summary.items()))

    report = {"data": args.data, "summary": summary, "results": results}
    with open(root / args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report written to {args.output}")

    if summary["error"] or (args.strict and summary["empty"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
