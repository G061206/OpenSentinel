"""基于 Jinja2/HTMX 的轻量管理后台。"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.api.deps import get_db_session
from app.models.enums import TrackerStatus
from app.models.tracker_run_log import TrackerRunLog
from app.services.system_config_service import SystemConfigService
from app.schemas.tracker import TrackerCreate
from app.services.tracker_service import TrackerService
from app.workers.tasks import run_tracker_once

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["admin"])


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


def _render_table(request: Request, session: Session):
    """渲染 tracker 表格局部模板。"""

    trackers = TrackerService.list(session)
    return templates.TemplateResponse(
        request=request,
        name="partials/tracker_table.html",
        context={"trackers": trackers},
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, session: Session = Depends(get_db_session)):
    """后台首页。"""

    trackers = TrackerService.list(session)
    return templates.TemplateResponse(
        request=request,
        name="admin_index.html",
        context={"trackers": trackers},
    )


@router.get("/admin/config", response_class=HTMLResponse)
def admin_config_page(request: Request, session: Session = Depends(get_db_session)):
    """系统配置页（LLM Provider 与全局 RSS 源）。"""

    config = SystemConfigService.get_or_create(session)
    return templates.TemplateResponse(
        request=request,
        name="admin_config.html",
        context={"config": config, "message": ""},
    )


@router.post("/admin/config", response_class=HTMLResponse)
def admin_config_save(
    request: Request,
    llm_provider: str = Form("mock"),
    llm_api_key: str = Form(""),
    llm_model: str = Form(""),
    global_rss_urls: str = Form(""),
    session: Session = Depends(get_db_session),
):
    """保存系统配置并返回结果。"""

    config = SystemConfigService.update(
        session,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        global_rss_urls=_to_list(global_rss_urls),
    )
    return templates.TemplateResponse(
        request=request,
        name="admin_config.html",
        context={"config": config, "message": "配置已保存"},
    )


@router.get("/admin/trackers/table", response_class=HTMLResponse)
def admin_tracker_table(request: Request, session: Session = Depends(get_db_session)):
    """仅返回表格局部内容，用于 HTMX 刷新。"""

    return _render_table(request, session)


@router.post("/admin/trackers", response_class=HTMLResponse)
def admin_create_tracker(
    request: Request,
    title: str = Form(...),
    question: str = Form(...),
    description: str = Form(""),
    queries: str = Form(""),
    rss_urls: str = Form(""),
    web_urls: str = Form(""),
    schedule: str = Form("*/15 * * * *"),
    wecom_webhook_url: str = Form(""),
    session: Session = Depends(get_db_session),
):
    """通过表单创建任务，并返回刷新后的表格。"""

    payload = TrackerCreate(
        title=title,
        question=question,
        description=description,
        queries=_to_list(queries),
        source_profile={
            "rss_urls": _to_list(rss_urls),
            "web_urls": _to_list(web_urls),
        },
        schedule=schedule,
        alert_rules={
            "elevated_threshold": 2,
            "crisis_threshold": 4,
            "confirmed_threshold": 6,
        },
        delivery_channels={"wecom_webhook_url": wecom_webhook_url},
        priority=50,
    )
    TrackerService.create(session, payload)
    return _render_table(request, session)


@router.post("/admin/trackers/{tracker_id}/pause", response_class=HTMLResponse)
def admin_pause_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """暂停指定任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.set_status(session, tracker, TrackerStatus.paused)
    return _render_table(request, session)


@router.post("/admin/trackers/{tracker_id}/resume", response_class=HTMLResponse)
def admin_resume_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """恢复指定任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.set_status(session, tracker, TrackerStatus.active)
    return _render_table(request, session)


@router.post("/admin/trackers/{tracker_id}/run", response_class=HTMLResponse)
def admin_run_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """手动触发指定任务执行。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    if tracker.id is None:
        raise HTTPException(status_code=400, detail="tracker id invalid")
    run_tracker_once.delay(tracker.id, force=True)
    return _render_table(request, session)


@router.post("/admin/trackers/{tracker_id}/delete", response_class=HTMLResponse)
def admin_delete_tracker(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """删除指定任务。"""

    tracker = TrackerService.get(session, tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="tracker not found")
    TrackerService.delete(session, tracker)
    return _render_table(request, session)


@router.get("/admin/trackers/{tracker_id}/logs", response_class=HTMLResponse)
def admin_tracker_logs(tracker_id: int, request: Request, session: Session = Depends(get_db_session)):
    """查看单个任务的执行日志页面。"""

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
    return templates.TemplateResponse(
        request=request,
        name="admin_tracker_logs.html",
        context={"tracker": tracker, "logs": logs},
    )
