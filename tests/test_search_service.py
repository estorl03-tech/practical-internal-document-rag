import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services import search_service
from tests.eval_case_loader import load_retrieval_cases_by_id

RETRIEVAL_CASES = load_retrieval_cases_by_id()


class FakeDistance:
    def label(self, name: str):
        return self


class FakeEmbeddingColumn:
    def cosine_distance(self, query_embedding):
        return FakeDistance()


class FakeBoolColumn:
    def is_(self, value: bool):
        return value


class FakeDocumentModel:
    id = object()
    is_active = FakeBoolColumn()


class FakeChunkModel:
    embedding = FakeEmbeddingColumn()
    document_id = object()


class FakeStatement:
    def join(self, *args, **kwargs):
        return self

    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, statement):
        return FakeResult(self._rows)


def make_chunk(
    *,
    chunk_id: int,
    document_id: int,
    chunk_index: int,
    content: str,
    source: str,
    title: str,
    version: str,
    document_group: str = "default_group",
    access_level: str = "public",
    updated_at: datetime | None = None,
) -> SimpleNamespace:
    if updated_at is None:
        updated_at = datetime(2026, 4, 11, tzinfo=timezone.utc)

    document = SimpleNamespace(
        title=title,
        version=version,
        updated_at=updated_at,
        document_group=document_group,
        access_level=access_level,
    )
    return SimpleNamespace(
        id=chunk_id,
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        source=source,
        document=document,
    )


def build_rows_for_case(case_id: str):
    if case_id == "QA-002":
        return [
            (
                make_chunk(
                    chunk_id=1,
                    chunk_index=0,
                    content="有給休暇は社内システムから申請します。",
                    source="hr_policy_v1.pdf",
                    title="有給休暇の申請ルール",
                    version="v1",
                    document_id=1,
                ),
                0.20,
            ),
            (
                make_chunk(
                    chunk_id=2,
                    chunk_index=1,
                    content="上長承認後に申請が確定します。",
                    source="hr_policy_v1.pdf",
                    title="有給休暇の申請ルール",
                    version="v1",
                    document_id=1,
                ),
                0.30,
            ),
            (
                make_chunk(
                    chunk_id=3,
                    chunk_index=2,
                    content="繁忙期は申請期限に注意してください。",
                    source="hr_policy_v1.pdf",
                    title="有給休暇の申請ルール",
                    version="v1",
                    document_id=1,
                ),
                0.40,
            ),
        ]

    if case_id == "QA-003":
        return [
            (
                make_chunk(
                    chunk_id=1,
                    chunk_index=0,
                    content="有給休暇は社内システムから申請します。",
                    source="hr_policy_v1.pdf",
                    title="有給休暇の申請ルール",
                    version="v1",
                    document_id=1,
                ),
                0.20,
            ),
            (
                make_chunk(
                    chunk_id=2,
                    chunk_index=1,
                    content="上長承認後に申請が確定します。",
                    source="hr_policy_v1.pdf",
                    title="有給休暇の申請ルール",
                    version="v1",
                    document_id=1,
                ),
                0.25,
            ),
            (
                make_chunk(
                    chunk_id=3,
                    chunk_index=2,
                    content="繁忙期は申請期限に注意してください。",
                    source="hr_policy_v1.pdf",
                    title="有給休暇の申請ルール",
                    version="v1",
                    document_id=1,
                ),
                0.35,
            ),
        ]

    if case_id == "META-006":
        return [
            (
                make_chunk(
                    chunk_id=17,
                    chunk_index=1,
                    content="育児休業の延長申請は人事ポータルから行います。",
                    source="childcare_policy_v2.pdf",
                    title="育児休業の申請ルール",
                    version="v2",
                    document_id=1,
                ),
                0.22,
            ),
            (
                make_chunk(
                    chunk_id=18,
                    chunk_index=2,
                    content="延長申請には本人確認書類の添付が必要です。",
                    source="childcare_policy_v2.pdf",
                    title="育児休業の申請ルール",
                    version="v2",
                    document_id=1,
                ),
                0.28,
            ),
            (
                make_chunk(
                    chunk_id=19,
                    chunk_index=3,
                    content="申請期限までに上長確認を完了してください。",
                    source="childcare_policy_v2.pdf",
                    title="育児休業の申請ルール",
                    version="v2",
                    document_id=1,
                ),
                0.38,
            ),
        ]

    if case_id == "META-012":
        return [
            (
                make_chunk(
                    chunk_id=11,
                    chunk_index=1,
                    content="育児休業の延長申請は所定フォームで行います。",
                    source="childcare_policy_v1.pdf",
                    title="育児休業の申請ルール",
                    version="v1",
                    document_group="childcare_policy",
                    updated_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
                    document_id=10,
                ),
                0.18,
            ),
            (
                make_chunk(
                    chunk_id=17,
                    chunk_index=1,
                    content="育児休業の延長申請は人事ポータルから行います。",
                    source="childcare_policy_v2.pdf",
                    title="育児休業の申請ルール",
                    version="v2",
                    document_group="childcare_policy",
                    updated_at=datetime(2026, 4, 11, tzinfo=timezone.utc),
                    document_id=11,
                ),
                0.22,
            ),
        ]

    if case_id == "META-013":
        shared_updated_at = datetime(2026, 4, 11, tzinfo=timezone.utc)
        return [
            (
                make_chunk(
                    chunk_id=21,
                    chunk_index=1,
                    content="育児休業の延長申請は所定フォームで行います。",
                    source="childcare_policy_v1.pdf",
                    title="育児休業の申請ルール",
                    version="v1",
                    document_group="childcare_policy",
                    updated_at=shared_updated_at,
                    document_id=20,
                ),
                0.18,
            ),
            (
                make_chunk(
                    chunk_id=22,
                    chunk_index=1,
                    content="育児休業の延長申請は人事ポータルから行います。",
                    source="childcare_policy_v2.pdf",
                    title="育児休業の申請ルール",
                    version="v2",
                    document_group="childcare_policy",
                    updated_at=shared_updated_at,
                    document_id=21,
                ),
                0.22,
            ),
        ]

    if case_id == "ACL-001":
        return [
            (
                make_chunk(
                    chunk_id=31,
                    document_id=30,
                    chunk_index=0,
                    content="人事評価資料は人事ポータルで確認します。",
                    source="hr_review_policy_v1.pdf",
                    title="人事評価資料の確認ルール",
                    version="v1",
                    document_group="hr_review_policy",
                    access_level="hr",
                ),
                0.15,
            ),
            (
                make_chunk(
                    chunk_id=32,
                    document_id=31,
                    chunk_index=1,
                    content="社員ハンドブックは社内ポータルで確認します。",
                    source="public_handbook_v1.pdf",
                    title="社員ハンドブック",
                    version="v1",
                    document_group="public_handbook",
                    access_level="public",
                ),
                0.22,
            ),
        ]

    if case_id == "ACL-002":
        return [
            (
                make_chunk(
                    chunk_id=31,
                    document_id=30,
                    chunk_index=0,
                    content="人事評価資料は人事ポータルで確認します。",
                    source="hr_review_policy_v1.pdf",
                    title="人事評価資料の確認ルール",
                    version="v1",
                    document_group="hr_review_policy",
                    access_level="hr",
                ),
                0.15,
            ),
            (
                make_chunk(
                    chunk_id=32,
                    document_id=31,
                    chunk_index=1,
                    content="社員ハンドブックは社内ポータルで確認します。",
                    source="public_handbook_v1.pdf",
                    title="社員ハンドブック",
                    version="v1",
                    document_group="public_handbook",
                    access_level="public",
                ),
                0.22,
            ),
        ]

    raise ValueError(f"Unknown retrieval case id: {case_id}")


def reranked_results_for_case(case_id: str, results):
    if case_id == "QA-003":
        return [results[1], results[0], results[2]]

    return results


@pytest.mark.parametrize(
    "case_id",
    ["QA-002", "QA-003", "META-006", "META-012", "META-013", "ACL-001", "ACL-002"],
)
def test_retrieve_chunks_matches_eval_cases(monkeypatch, case_id: str) -> None:
    case = RETRIEVAL_CASES[case_id]
    rows = build_rows_for_case(case_id)

    monkeypatch.setattr(search_service, "DocumentChunk", FakeChunkModel)
    monkeypatch.setattr(search_service, "Document", FakeDocumentModel)
    monkeypatch.setattr(
        search_service, "select", lambda *args, **kwargs: FakeStatement()
    )
    monkeypatch.setattr(search_service, "rewrite_query", lambda query: query)
    monkeypatch.setattr(search_service, "embed_text", lambda query: [0.1, 0.2])
    monkeypatch.setattr(
        search_service,
        "rerank_chunks",
        lambda query, results, _case_id=case_id: reranked_results_for_case(
            _case_id, results
        ),
    )

    response = search_service.retrieve_chunks(
        db=cast(Session, FakeSession(rows)),
        query=case["query"],
        top_k=case["top_k"],
        user_role=case.get("user_role", "employee"),
    )

    assert [result.chunk_index for result in response] == case["expected_chunk_indexes"]
    assert response[0].chunk_index == case["expected_top1_chunk_index"]
    assert response[0].source == case["expected_top1_source"]

    if case_id in {"META-012", "META-013", "ACL-001"}:
        assert len(response) == 1
    else:
        assert len(response) == len(case["expected_chunk_indexes"])

    assert [result.rerank_position for result in response] == list(
        range(1, len(response) + 1)
    )


def test_title_match_bonus_applies_to_related_titles() -> None:
    bonus = search_service.title_match_bonus(
        query="テレワークの申請はどこから行いますか？",
        title="テレワーク勤務規定",
    )

    assert bonus == search_service.TITLE_MATCH_BONUS


def test_title_match_bonus_skips_unrelated_titles() -> None:
    bonus = search_service.title_match_bonus(
        query="テレワークの申請はどこから行いますか？",
        title="交通費精算ルール",
    )

    assert bonus == 0.0
