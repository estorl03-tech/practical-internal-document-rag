from pathlib import Path
from typing import Any

import yaml


def load_eval_cases() -> dict[str, list[dict[str, Any]]]:
    eval_cases_path = Path(__file__).resolve().parents[1] / "docs" / "eval-cases.yaml"
    with eval_cases_path.open(encoding="utf-8") as file:
        loaded = yaml.safe_load(file)

    if not isinstance(loaded, dict):
        raise ValueError("eval-cases.yaml must contain a top-level mapping")

    return loaded


def load_management_cases_by_id() -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in load_eval_cases()["management_cases"]}


def load_retrieval_cases_by_id() -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in load_eval_cases()["retrieval_cases"]}
