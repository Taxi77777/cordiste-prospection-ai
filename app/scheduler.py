"""Planificateur interne (APScheduler) : lance la recherche chaque jour.

Alternative sans intervention humaine au cron système. Activé par ENABLE_SCHEDULER.
En production sur VPS on peut aussi utiliser cron/systemd (voir deploy/).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .jobs import run_daily_job

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.enable_scheduler:
        logger.info("Scheduler désactivé (ENABLE_SCHEDULER=false).")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Europe/Paris")
    _scheduler.add_job(
        run_daily_job,
        trigger=CronTrigger(hour=settings.daily_hour, minute=settings.daily_minute),
        id="prospection_quotidienne",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "Scheduler démarré : prospection quotidienne à %02d:%02d (Europe/Paris)",
        settings.daily_hour, settings.daily_minute,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
