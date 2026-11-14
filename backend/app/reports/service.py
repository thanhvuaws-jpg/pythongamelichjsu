"""Báo_Cáo_Sai_Sót (Req 7.1–7.4).

Luồng: new ──confirm──▶ confirmed ──(bản sửa được duyệt)──▶ resolved
           └─reject──▶ rejected

- "Xác nhận sai" ẩn Câu_Hỏi liên quan (`hidden_by_report`) rồi dựng lại bundle của
  các Màn_Chơi chứa chúng (Req 7.3):
    questions → chính Câu_Hỏi; events → mọi Câu_Hỏi của Sự_Kiện;
    fragments → Câu_Hỏi có `answer_basis` trỏ tới Mảnh_Ghép.
  Câu_Hỏi ẩn đã bị chặn chấm điểm ngay (load_question), kể cả khi dựng bundle thất bại.
- Khi nội dung bị báo được phê duyệt lại, báo cáo chuyển `resolved` và Câu_Hỏi được bỏ
  ẩn nếu không còn báo cáo xác nhận khác giữ nó.
- Mỗi lần báo cáo được xử lý, người báo nhận thông báo trong Game_Client (Req 7.4).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.models import (
    AuditLog,
    Bundle,
    ContentMixin,
    ContentStatus,
    ContentVersion,
    ErrorReport,
    Event,
    Fragment,
    Notification,
    Objective,
    ObjectiveKind,
    Quest,
    Question,
    ReportStatus,
    User,
)
from app.publish.bundler import publish_level
from app.storage import get_storage

logger = logging.getLogger("app.reports")

REPORTABLE: dict[str, type[ContentMixin]] = {
    Event.__tablename__: Event,
    Fragment.__tablename__: Fragment,
    Question.__tablename__: Question,
}

STATUS_LABEL = {
    ReportStatus.confirmed: "Báo cáo của bạn đã được xác nhận, nội dung đang được sửa",
    ReportStatus.rejected: "Báo cáo của bạn đã được xem xét, nội dung được giữ nguyên",
    ReportStatus.resolved: "Nội dung bạn báo cáo đã được sửa và phê duyệt",
}


async def _published_entity(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> ContentMixin:
    model = REPORTABLE.get(entity_type)
    if model is None:
        raise AppError(
            400,
            "REPORT_TYPE_INVALID",
            "Chỉ báo sai sót cho Sự kiện, Mảnh ghép hoặc Câu hỏi",
            {"allowed": sorted(REPORTABLE)},
        )
    entity = await session.get(model, entity_id)
    # Người_Chơi chỉ thấy nội dung đã xuất bản
    if entity is None or entity.published_version_id is None:
        raise AppError(404, "CONTENT_NOT_FOUND", "Không tìm thấy nội dung")
    return entity


async def create_report(
    session: AsyncSession,
    reporter: User,
    entity_type: str,
    entity_id: uuid.UUID,
    description: str,
    counter_source: str | None,
) -> ErrorReport:
    """Lưu báo cáo ở trạng thái Mới (Req 7.1, 7.2)."""
    await _published_entity(session, entity_type, entity_id)
    report = ErrorReport(
        id=uuid.uuid4(),
        reporter_id=reporter.id,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description.strip(),
        counter_source=(counter_source or "").strip() or None,
        status=ReportStatus.new,
        hidden_question_ids=[],
    )
    session.add(report)
    await session.flush()
    await session.refresh(report)
    return report


async def related_questions(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> list[uuid.UUID]:
    if entity_type == Question.__tablename__:
        return [entity_id]
    if entity_type == Event.__tablename__:
        rows = await session.scalars(select(Question.id).where(Question.event_id == entity_id))
        return list(rows)
    rows = await session.scalars(
        select(Question.id).where(
            Question.answer_basis.contains([{"type": "fragments", "id": str(entity_id)}])
        )
    )
    return list(rows)


async def affected_levels(session: AsyncSession, question_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Màn_Chơi đã có bundle chứa các Câu_Hỏi (qua Sự_Kiện hoặc đích Mục_Tiêu)."""
    if not question_ids:
        return set()
    levels = set(
        await session.scalars(
            select(Event.level_id)
            .join(Question, Question.event_id == Event.id)
            .where(Question.id.in_(question_ids), Event.level_id.is_not(None))
        )
    )
    levels |= set(
        await session.scalars(
            select(Quest.level_id)
            .join(Objective, Objective.quest_id == Quest.id)
            .where(Objective.kind == ObjectiveKind.answer, Objective.target_id.in_(question_ids))
        )
    )
    if not levels:
        return set()
    with_bundle = await session.scalars(
        select(Bundle.level_id).where(Bundle.level_id.in_(levels)).distinct()
    )
    return set(with_bundle)


async def rebuild_bundles(
    session: AsyncSession, level_ids: set[uuid.UUID], actor: User
) -> list[dict[str, Any]]:
    """Dựng lại bundle từng màn trong savepoint riêng; màn lỗi không chặn màn khác."""
    results = []
    for lid in sorted(level_ids, key=str):
        try:
            async with session.begin_nested():
                bundle = await publish_level(session, lid, actor, get_storage())
            results.append({"level_id": str(lid), "ok": True, "version": bundle.version_no})
        except AppError as exc:
            logger.warning("bundle_rebuild_failed", extra={"level_id": str(lid), "code": exc.code})
            results.append(
                {"level_id": str(lid), "ok": False, "code": exc.code, "details": exc.details}
            )
    return results


def _notify(session: AsyncSession, report: ErrorReport) -> None:
    if report.reporter_id is None:
        return
    session.add(
        Notification(
            id=uuid.uuid4(),
            user_id=report.reporter_id,
            kind="report_handled",
            payload={
                "report_id": str(report.id),
                "entity_type": report.entity_type,
                "entity_id": str(report.entity_id),
                "status": report.status.value,
                "message": STATUS_LABEL[report.status],
                "resolution": report.resolution,
            },
        )
    )


def _audit(session: AsyncSession, actor: User | None, report: ErrorReport, before: str) -> None:
    session.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=f"report_{report.status.value}",
            target_type="error_reports",
            target_id=str(report.id),
            before={"status": before},
            after={
                "status": report.status.value,
                "hidden_question_ids": [str(q) for q in report.hidden_question_ids],
            },
        )
    )


async def handle_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    actor: User,
    status: ReportStatus,
    resolution: str | None,
) -> tuple[ErrorReport, list[dict[str, Any]]]:
    """Xác nhận sai hoặc bác báo cáo đang ở trạng thái Mới."""
    report = await session.scalar(
        select(ErrorReport).where(ErrorReport.id == report_id).with_for_update()
    )
    if report is None:
        raise AppError(404, "REPORT_NOT_FOUND", "Không tìm thấy báo cáo")
    if report.status != ReportStatus.new:
        raise AppError(
            409,
            "INVALID_TRANSITION",
            "Chỉ xử lý được báo cáo ở trạng thái Mới",
            {"status": report.status.value},
        )
    before = report.status.value
    report.status = status
    report.handled_by = actor.id
    report.resolution = (resolution or "").strip() or None

    rebuilt: list[dict[str, Any]] = []
    if status == ReportStatus.confirmed:
        qids = await related_questions(session, report.entity_type, report.entity_id)
        report.hidden_question_ids = qids
        if qids:
            await session.execute(
                update(Question).where(Question.id.in_(qids)).values(hidden_by_report=True)
            )
            rebuilt = await rebuild_bundles(session, await affected_levels(session, qids), actor)
    _audit(session, actor, report, before)
    _notify(session, report)
    return report, rebuilt


async def resolve_on_approval(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID, approver: User
) -> None:
    """Gọi khi nội dung được phê duyệt: đóng báo cáo đã xác nhận và bỏ ẩn Câu_Hỏi."""
    reports = list(
        await session.scalars(
            select(ErrorReport)
            .where(
                ErrorReport.entity_type == entity_type,
                ErrorReport.entity_id == entity_id,
                ErrorReport.status == ReportStatus.confirmed,
            )
            .with_for_update()
        )
    )
    if not reports:
        return
    released = {q for r in reports for q in r.hidden_question_ids}
    for r in reports:
        r.status = ReportStatus.resolved
        _audit(session, approver, r, ReportStatus.confirmed.value)
        _notify(session, r)
    await session.flush()
    # Câu_Hỏi còn bị một báo cáo xác nhận khác giữ thì vẫn ẩn
    still_held = {
        q
        for ids in await session.scalars(
            select(ErrorReport.hidden_question_ids).where(
                ErrorReport.status == ReportStatus.confirmed
            )
        )
        for q in ids
    }
    unhide = released - still_held
    if unhide:
        await session.execute(
            update(Question).where(Question.id.in_(unhide)).values(hidden_by_report=False)
        )


async def entity_title(session: AsyncSession, report: ErrorReport) -> str | None:
    """Tiêu đề bản đang chạy để hàng đợi Admin_Portal dễ đọc."""
    model = REPORTABLE.get(report.entity_type)
    if model is None:
        return None
    snap = await session.scalar(
        select(ContentVersion.snapshot)
        .join(model, model.published_version_id == ContentVersion.id)
        .where(model.id == report.entity_id, model.status != ContentStatus.archived)
    )
    if not snap:
        return None
    return snap.get("title") or snap.get("prompt")
