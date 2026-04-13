import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.schemas import SearchResult
from app.services import ask_service
from tests.eval_case_loader import load_eval_cases

ASK_CASES = {case["id"]: case for case in load_eval_cases()["ask_cases"]}


def make_result(score: float, chunk_id: int) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=1,
        chunk_index=chunk_id - 1,
        content=f"chunk-{chunk_id}",
        source="test.pdf",
        score=score,
        rerank_position=chunk_id,
        version="v1",
        updated_at=datetime.now(timezone.utc),
        document_group="test_group",
    )


def build_results_for_eval_case(case_id: str) -> list[SearchResult]:
    if case_id == "QA-002":
        return [make_result(0.70, 1), make_result(0.60, 2), make_result(0.40, 3)]

    if case_id == "QA-015":
        return [make_result(0.49, 1), make_result(0.48, 2), make_result(0.20, 3)]

    if case_id == "QA-016":
        return [make_result(0.58, 1), make_result(0.40, 2), make_result(0.30, 3)]

    if case_id == "META-006":
        shared_updated_at = datetime(2026, 4, 11, tzinfo=timezone.utc)
        return [
            SearchResult(
                chunk_id=17,
                document_id=1,
                chunk_index=1,
                content="育児休業の延長申請は人事ポータルから行います。",
                source="childcare_policy_v2.pdf",
                score=0.67,
                rerank_position=1,
                version="v2",
                updated_at=shared_updated_at,
                document_group="childcare_policy",
            ),
            SearchResult(
                chunk_id=18,
                document_id=1,
                chunk_index=2,
                content="延長申請には本人確認書類の添付が必要です。",
                source="childcare_policy_v2.pdf",
                score=0.63,
                rerank_position=2,
                version="v2",
                updated_at=shared_updated_at,
                document_group="childcare_policy",
            ),
            SearchResult(
                chunk_id=19,
                document_id=1,
                chunk_index=3,
                content="申請期限までに上長確認を完了してください。",
                source="childcare_policy_v2.pdf",
                score=0.58,
                rerank_position=3,
                version="v2",
                updated_at=shared_updated_at,
                document_group="childcare_policy",
            ),
        ]

    raise ValueError(f"Unknown eval case id: {case_id}")


def test_answer_question_sets_answer_level_and_used_sources(monkeypatch) -> None:
    cases = [
        (
            [make_result(0.70, 1), make_result(0.60, 2), make_result(0.40, 3)],
            "green",
            True,
            False,
            2,
        ),
        (
            [make_result(0.58, 1), make_result(0.40, 2), make_result(0.30, 3)],
            "yellow",
            True,
            True,
            2,
        ),
        (
            [make_result(0.49, 1), make_result(0.48, 2), make_result(0.20, 3)],
            "red",
            False,
            False,
            0,
        ),
    ]

    for (
        results,
        expected_level,
        expected_enough,
        expect_yellow_prefix,
        expected_used_count,
    ) in cases:
        monkeypatch.setattr(
            ask_service,
            "retrieve_chunks",
            lambda db, query, top_k, user_role="employee", _results=results: _results,
        )
        monkeypatch.setattr(
            ask_service, "generate_answer", lambda query, context: "base answer"
        )

        response = ask_service.answer_question(
            db=Mock(spec=Session), query="test query", top_k=3
        )

        assert response.answer_level == expected_level
        assert response.enough_information is expected_enough
        assert len(response.used_sources) == expected_used_count

        if expect_yellow_prefix:
            assert response.answer.startswith("提示された情報だけでは断定できませんが")
        elif expected_level == "green":
            assert response.answer == "base answer"
        else:
            assert (
                response.answer
                == "十分な情報が見つからなかったため、現時点では回答できません。"
            )


def test_answer_question_deduplicates_used_source_summaries(monkeypatch) -> None:
    shared_updated_at = datetime(2026, 4, 11, tzinfo=timezone.utc)
    results = [
        SearchResult(
            chunk_id=17,
            document_id=1,
            chunk_index=1,
            content="育児休業の延長申請は人事ポータルから行います。",
            source="childcare_policy_v2.pdf",
            score=0.67,
            rerank_position=1,
            version="v2",
            updated_at=shared_updated_at,
            document_group="childcare_policy",
        ),
        SearchResult(
            chunk_id=18,
            document_id=1,
            chunk_index=2,
            content="延長申請には本人確認書類の添付が必要です。",
            source="childcare_policy_v2.pdf",
            score=0.63,
            rerank_position=2,
            version="v2",
            updated_at=shared_updated_at,
            document_group="childcare_policy",
        ),
    ]

    monkeypatch.setattr(
        ask_service,
        "retrieve_chunks",
        lambda db, query, top_k, user_role="employee": results,
    )
    monkeypatch.setattr(
        ask_service, "generate_answer", lambda query, context: "base answer"
    )

    response = ask_service.answer_question(
        db=Mock(spec=Session), query="育児休業の延長申請はどこから行いますか？", top_k=3
    )

    assert len(response.used_sources) == 2
    assert response.used_source_summaries == [
        "childcare_policy_v2.pdf (v2, 2026-04-11更新)"
    ]


@pytest.mark.parametrize(
    ("case_id", "expect_yellow_prefix"),
    [
        ("QA-002", False),
        ("QA-015", False),
        ("QA-016", True),
        ("META-006", False),
    ],
)
def test_answer_question_matches_eval_cases(
    monkeypatch, case_id: str, expect_yellow_prefix: bool
) -> None:
    case = ASK_CASES[case_id]
    results = build_results_for_eval_case(case_id)

    monkeypatch.setattr(
        ask_service,
        "retrieve_chunks",
        lambda db, query, top_k, user_role="employee", _results=results: _results,
    )
    monkeypatch.setattr(
        ask_service, "generate_answer", lambda query, context: "base answer"
    )

    response = ask_service.answer_question(
        db=Mock(spec=Session),
        query=case["query"],
        top_k=3,
        user_role=case.get("user_role", "employee"),
    )

    assert response.answer_level == case["expected_answer_level"]
    assert response.enough_information is case["expected_enough_information"]
    assert len(response.used_sources) == case["expected_used_source_count"]

    if expect_yellow_prefix:
        assert response.answer.startswith("提示された情報だけでは断定できませんが")
    elif case["expected_answer_level"] == "green":
        assert response.answer == "base answer"
    else:
        assert (
            response.answer
            == "十分な情報が見つからなかったため、現時点では回答できません。"
        )

    if "expected_used_source_summaries" in case:
        assert response.used_source_summaries == case["expected_used_source_summaries"]


def test_answer_question_passes_user_role_and_returns_red_when_acl_filters_results(
    monkeypatch,
) -> None:
    captured_user_roles: list[str] = []

    def fake_retrieve_chunks(db, query: str, top_k: int, user_role: str = "employee"):
        captured_user_roles.append(user_role)
        return []

    monkeypatch.setattr(ask_service, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(
        ask_service, "generate_answer", lambda query, context: "base answer"
    )

    response = ask_service.answer_question(
        db=Mock(spec=Session),
        query=ASK_CASES["ACL-003"]["query"],
        top_k=3,
        user_role=ASK_CASES["ACL-003"]["user_role"],
    )

    assert captured_user_roles == ["employee"]
    assert response.answer_level == ASK_CASES["ACL-003"]["expected_answer_level"]
    assert (
        response.enough_information
        is ASK_CASES["ACL-003"]["expected_enough_information"]
    )
    assert len(response.used_sources) == ASK_CASES["ACL-003"]["expected_used_source_count"]
