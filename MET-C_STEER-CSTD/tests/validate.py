"""Check workflow artifacts, not the correctness of specification judgements."""

import csv
import json
from pathlib import Path
from zipfile import ZipFile


def skill_was_loaded(log: Path) -> bool:
    calls: set[str] = set()
    succeeded: set[str] = set()
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.startswith("{"):
            continue
        event = json.loads(line)
        content = event.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if event.get("type") == "assistant" and block.get("type") == "tool_use":
                arguments = block.get("input", {})
                if (
                    block.get("name") == "Skill"
                    and arguments.get("skill", "").split(":")[-1]
                    == "speccheck-workflow"
                ) or (
                    block.get("name") == "Read"
                    and str(arguments.get("file_path", "")).endswith(
                        "/speccheck-workflow/SKILL.md"
                    )
                ):
                    calls.add(block["id"])
            if event.get("type") == "user" and block.get("type") == "tool_result":
                if not block.get("is_error", False):
                    succeeded.add(block["tool_use_id"])
    return bool(calls & succeeded)


def validate(root: Path, log: Path) -> dict[str, str | int | bool]:
    if not skill_was_loaded(log):
        raise ValueError("No successful speccheck-workflow skill load in agent logs")
    new_files = list(root.glob("specification_check/check_spec/*/*.xlsm"))
    old_files = list(root.glob("input/old/*.xlsm"))
    if len(new_files) != 1 or len(old_files) != 1:
        raise ValueError("Expected exactly one local old/new workbook pair")
    new, old = new_files[0], old_files[0]
    output = root / "specification_check/output"
    report = output / f"{new.stem}_report"
    required = [
        new.with_suffix(".md"),
        output / "spec_diff.csv",
        output / "spec_diff.html",
        output / "spec_diff.json",
        output / "limitations.md",
        report.with_suffix(".md"),
        report.with_suffix(".xlsx"),
    ]
    for path in required:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty workflow artifact: {path}")
    limitation = (output / "limitations.md").read_text(encoding="utf-8")
    if "text-only" not in limitation or "EMF" not in limitation:
        raise ValueError("Limitations must disclose text-only scope and omitted EMF")
    with (output / "spec_diff.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Expected nonempty differences for this old/new fixture")
    for row in rows:
        if (
            Path(row.get("file_old", "")).name != old.name
            or Path(row.get("file_new", "")).name != new.name
        ):
            raise ValueError("Difference CSV does not use the supplied local pair")
    records = json.loads((output / "spec_diff.json").read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("spec_diff.json must contain difference records")
    expected: set[tuple[int, str]] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("Invalid difference record")
        if record.get("excluded") is True:
            continue
        checks = record.get("checkno")
        if not isinstance(checks, list):
            raise ValueError("Step 2 must label each active record with a checkno list")
        for check in checks:
            if not isinstance(check, str) or not check.startswith("CHK-"):
                raise ValueError("Step 2 checkno entries must be CHK identifiers")
            expected.add((index, check))
    actual: set[tuple[int, str]] = set()
    for path in sorted((output / f"{new.stem}_check_results").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(
            payload.get("results"), list
        ):
            raise ValueError(f"Invalid Step 3 result file: {path}")
        for result in payload["results"]:
            if not isinstance(result, dict):
                raise ValueError(f"Invalid Step 3 result in {path}")
            index = result.get("index", payload.get("index"))
            check = result.get("checkno")
            if not isinstance(index, int) or not isinstance(check, str):
                raise ValueError(f"Missing result index/checkno in {path}")
            key = (index, check)
            if key in actual:
                raise ValueError(f"Duplicate check result: {key}")
            if result.get("judgement") not in {"問題あり", "問題なし", "要確認"}:
                raise ValueError(f"Invalid judgement for {key}")
            if (
                not isinstance(result.get("reason"), str)
                or not result["reason"].strip()
            ):
                raise ValueError(f"Missing judgement reason for {key}")
            actual.add(key)
    if actual != expected:
        raise ValueError(
            f"Step 3 coverage mismatch: missing={expected - actual}, extra={actual - expected}"
        )
    if new.stem not in report.with_suffix(".md").read_text(encoding="utf-8"):
        raise ValueError("Markdown report does not identify the new specification")
    with ZipFile(report.with_suffix(".xlsx")) as workbook:
        if not {"[Content_Types].xml", "xl/workbook.xml"} <= set(workbook.namelist()):
            raise ValueError("Excel report is not an XLSX workbook")
        if workbook.testzip() is not None:
            raise ValueError("Excel report is corrupt")
    return {
        "status": "passed",
        "scope": "text-only",
        "skill_load_verified": True,
        "diff_records": len(records),
        "check_results": len(actual),
        "business_accuracy_validated": False,
        "mcp_success_validated": False,
    }


if __name__ == "__main__":
    checks = validate(Path("/app"), Path("/logs/agent/claude-code.txt"))
    Path("/logs/verifier/checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(checks, ensure_ascii=False))
