"""基于 Jinja2/HTMX 的管理后台（侧边栏 + 面板切换）。"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.api.deps import get_db_session
from app.models.enums import TrackerStatus, LLMProviderType
from app.models.tracker_run_log import TrackerRunLog
from app.schemas.llm_provider import LLMProviderCreate
from app.schemas.rss_source import RSSSourceCreate
from app.schemas.tracker import TrackerCreate, TrackerUpdate
from app.services.llm_provider_service import LLMProviderService
from app.services.rss_source_service import RSSSourceService
from app.services.tracker_service import TrackerService
from app.workers.tasks import run_tracker_once

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["admin"])


# ── 工具函数 ──────────────────────────────────────────────


def _to_list(value: str) -> list[str]:
    """把逗号或换行分隔字符串转换为字符串数组。"""

    if not value:
        return []
    values = []
    for raw in value.replace(",", "\n").splitlines():
        clean = raw.strip()
        if clean:
            values.append(clean)
    return values


def _is_htmx(request: Request) -> bool:
    """检查请求是否来自 HTMX。"""
    return request.headers.get("HX-Request") == "true"


def _panel_response(request: Request, session: Session, template_name: str, context: dict):
    """如果是 HTMX 请求，返回面板片段；否则返回完整壳页面包裹面板。"""
    if _is_htmx(request):
        return templates.TemplateResponse(
            request=request,
            name=template_name,
            context=context,
        )

    # 非 HTMX 请求（直接 URL 访问），返回完整壳页面 + 内联面板
    return templates.TemplateResponse(
        request=request,
        name="admin_shell.html",
        context={**context, "inline_panel": template_name},
    )


# ── 主入口 ──────────────────────────────────────────────


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, session: Session = Depends(get_db_session)):
    """后台首页，加载壳页面，默认显示 Tracker 列表面板。"""

    trackers = TrackerService.list(session)
    all_providers = LLMProviderService.list(session)

    # 为每个 tracker 附加额外展示信息
    for t in trackers:
        t._rss_sources = RSSSourceService.get_sources_for_tracker(session, t.id) if t.id else []
        t._provider_name = ""
        if t.llm_provider_id:
            for p in all_providers:
                if p.id == t.llm_provider_id:
                    t._provider_name = p.name
                    break

    return templates.TemplateResponse(
        request=request,
        name="admin_shell.html",
        context={
            "trackers": trackers,
            "inline_panel": "panels/tracker_list.html",
        },
    )


# ── Tracker 面板 ────────────────────────────────────────


@router.get("/admin/panels/trackers", response_class=HTMLResponse)
def panel_tracker_list(request: Request, session: Session = Depends(get_db_session)):
    """Tracker 列表面板。"""

    trackers = TrackerService.list(session)
    all_providers = LLMProviderService.list(session)

    for t in trackers:
        t._rss_sources = RSSSourceService.get_sources_for_tracker(session, t.id) if t.id else []
        t._provider_name = ""
        if t.llm_provider_id:
            for p in all_providers:
                if p.id == t.llm_provider_id:
                    t._provider_name = p.name
                    break

    return _panel_response(request, session, "panels/tracker_list.html", {
        "trackers": trackers,
    })


@router.get("/admin/panels/tracker-form", response_class=HTMLResponse)
def panel_tracker_form_new(request: Request, session: Session = Depends(get_db_session)):
    """新建 Tracker 表单面板。"""

    providers = LLMProviderService.list(session)
    rss_sources = RSSSourceService.list(session)
    return _panel_response(request, session, "panels/tracker_form.html", {
        "tracker": None,
        "providers": providers,
        "rss_sources": rss_sources,
        "tracker_rss_ids": [],
    })


@router.get("/admin/panels/tracker-form/{tracker_id}", response_class=HTMLResponse)
def panel_tracker_form_edit(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """编辑 Tracker 表单面板。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    providers = LLMProviderService.list(session)
    rss_sources = RSSSourceService.list(session)
    tracker_rss = RSSSourceService.get_sources_for_tracker(session, tracker_id)
    tracker_rss_ids = [s.id for s in tracker_rss]
    return _panel_response(request, session, "panels/tracker_form.html", {
        "tracker": tracker,
        "providers": providers,
        "rss_sources": rss_sources,
        "tracker_rss_ids": tracker_rss_ids,
    })


@router.post("/admin/trackers", response_class=HTMLResponse)
def admin_create_tracker(
    request: Request,
    title: str = Form(...),
    question: str = Form(...),
    description: str = Form(""),
    queries: str = Form(""),
    web_urls: str = Form(""),
    schedule: str = Form("*/15 * * * *"),
    wecom_webhook_url: str = Form(""),
    llm_provider_id: int | None = Form(None),
    rss_source_ids: str = Form(""),
    elevated_threshold: int = Form(2),
    crisis_threshold: int = Form(4),
    confirmed_threshold: int = Form(6),
    session: Session = Depends(get_db_session),
):
    """通过表单创建任务，返回 Tracker 列表面板。"""

    rss_ids = [int(x) for x in rss_source_ids.split(",") if x.strip().isdigit()]

    payload = TrackerCreate(
        title=title,
        question=question,
        description=description,
        queries=_to_list(queries),
        source_profile={
            "web_urls": _to_list(web_urls),
        },
        schedule=schedule,
        alert_rules={
            "elevated_threshold": elevated_threshold,
            "crisis_threshold": crisis_threshold,
            "confirmed_threshold": confirmed_threshold,
        },
        delivery_channels={"wecom_webhook_url": wecom_webhook_url},
        priority=50,
        llm_provider_id=llm_provider_id if llm_provider_id and llm_provider_id > 0 else None,
        rss_source_ids=rss_ids,
    )
    TrackerService.create(session, payload)
    return panel_tracker_list(request, session)


@router.post("/admin/trackers/{tracker_id}/update", response_class=HTMLResponse)
def admin_update_tracker(
    tracker_id: int,
    request: Request,
    title: str = Form(...),
    question: str = Form(...),
    description: str = Form(""),
    queries: str = Form(""),
    web_urls: str = Form(""),
    schedule: str = Form("*/15 * * * *"),
    wecom_webhook_url: str = Form(""),
    llm_provider_id: int | None = Form(None),
    rss_source_ids: str = Form(""),
    elevated_threshold: int = Form(2),
    crisis_threshold: int = Form(4),
    confirmed_threshold: int = Form(6),
    session: Session = Depends(get_db_session),
):
    """通过表单更新任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")

    rss_ids = [int(x) for x in rss_source_ids.split(",") if x.strip().isdigit()]

    data = TrackerUpdate(
        title=title,
        question=question,
        description=description,
        queries=_to_list(queries),
        source_profile={
            "web_urls": _to_list(web_urls),
        },
        schedule=schedule,
        alert_rules={
            "elevated_threshold": elevated_threshold,
            "crisis_threshold": crisis_threshold,
            "confirmed_threshold": confirmed_threshold,
        },
        delivery_channels={"wecom_webhook_url": wecom_webhook_url},
        llm_provider_id=llm_provider_id if llm_provider_id and llm_provider_id > 0 else None,
        rss_source_ids=rss_ids,
    )
    TrackerService.update(session, tracker, data)
    return panel_tracker_list(request, session)


@router.post("/admin/trackers/{tracker_id}/pause", response_class=HTMLResponse)
def admin_pause_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """暂停指定任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.set_status(session, tracker, TrackerStatus.paused)
    return panel_tracker_list(request, session)


@router.post("/admin/trackers/{tracker_id}/resume", response_class=HTMLResponse)
def admin_resume_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """恢复指定任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.set_status(session, tracker, TrackerStatus.active)
    return panel_tracker_list(request, session)


@router.post("/admin/trackers/{tracker_id}/run", response_class=HTMLResponse)
def admin_run_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """手动触发指定任务执行。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    if tracker.id is None:
        raise HTTPException(status_code=400, detail="tracker id invalid")
    run_tracker_once.delay(tracker.id, force=True)
    return panel_tracker_list(request, session)


@router.post("/admin/trackers/{tracker_id}/delete", response_class=HTMLResponse)
def admin_delete_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """删除指定任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.delete(session, tracker)
    return panel_tracker_list(request, session)


@router.get("/admin/panels/tracker-logs/{tracker_id}", response_class=HTMLResponse)
def panel_tracker_logs(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """Tracker 执行日志面板。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")

    logs = list(
        session.exec(
            select(TrackerRunLog)
            .where(TrackerRunLog.tracker_id == tracker_id)
            .order_by(TrackerRunLog.started_at.desc())
        ).all()
    )
    return _panel_response(request, session, "panels/tracker_logs.html", {
        "tracker": tracker,
        "logs": logs,
    })


# ── Provider 面板 ───────────────────────────────────────


@router.get("/admin/panels/providers", response_class=HTMLResponse)
def panel_provider_list(request: Request, session: Session = Depends(get_db_session)):
    """LLM Provider 列表面板。"""

    providers = LLMProviderService.list(session)
    provider_types = list(LLMProviderType)
    return _panel_response(request, session, "panels/provider_list.html", {
        "providers": providers,
        "provider_types": provider_types,
    })


@router.post("/admin/providers", response_class=HTMLResponse)
def admin_create_provider(
    request: Request,
    name: str = Form(...),
    provider_type: str = Form("mock"),
    api_key: str = Form(""),
    model: str = Form(""),
    base_url: str = Form(""),
    is_default: bool = Form(False),
    session: Session = Depends(get_db_session),
):
    """创建 LLM Provider。"""

    data = LLMProviderCreate(
        name=name,
        provider_type=LLMProviderType(provider_type),
        api_key=api_key,
        model=model,
        base_url=base_url,
        is_default=is_default,
    )
    LLMProviderService.create(session, data)
    return panel_provider_list(request, session)


@router.post("/admin/providers/{provider_id}/delete", response_class=HTMLResponse)
def admin_delete_provider(provider_id: int, request: Request, session: Session = Depends(get_db_session)):
    """删除 LLM Provider。"""

    provider = LLMProviderService.get(session, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="provider not found")
    LLMProviderService.delete(session, provider)
    return panel_provider_list(request, session)


@router.post("/admin/providers/{provider_id}/set-default", response_class=HTMLResponse)
def admin_set_default_provider(provider_id: int, request: Request, session: Session = Depends(get_db_session)):
    """将指定 Provider 设为默认。"""

    provider = LLMProviderService.get(session, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="provider not found")
    LLMProviderService.set_default(session, provider)
    return panel_provider_list(request, session)


# ── RSS 信源面板 ────────────────────────────────────────


@router.get("/admin/panels/rss-sources", response_class=HTMLResponse)
def panel_rss_list(request: Request, session: Session = Depends(get_db_session)):
    """RSS 信源列表面板。"""

    rss_sources = RSSSourceService.list(session)
    # 附加引用计数
    for s in rss_sources:
        s._ref_count = RSSSourceService.get_reference_count(session, s.id) if s.id else 0
    return _panel_response(request, session, "panels/rss_list.html", {
        "rss_sources": rss_sources,
    })


@router.post("/admin/rss-sources", response_class=HTMLResponse)
def admin_create_rss_source(
    request: Request,
    name: str = Form(""),
    url: str = Form(""),
    category: str = Form(""),
    bulk_urls: str = Form(""),
    session: Session = Depends(get_db_session),
):
    """创建 RSS 信源（单条或批量）。"""

    if bulk_urls.strip():
        RSSSourceService.bulk_create(session, bulk_urls, category=category)
    elif url.strip():
        data = RSSSourceCreate(
            name=name or url.split("/")[-1] or url,
            url=url.strip(),
            category=category,
        )
        RSSSourceService.create(session, data)
    return panel_rss_list(request, session)


@router.post("/admin/rss-sources/{source_id}/delete", response_class=HTMLResponse)
def admin_delete_rss_source(source_id: int, request: Request, session: Session = Depends(get_db_session)):
    """删除 RSS 信源。"""

    source = RSSSourceService.get(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="rss source not found")
    RSSSourceService.delete(session, source)
    return panel_rss_list(request, session)
