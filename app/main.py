"""Application FastAPI : API JSON + tableau de bord web."""
from __future__ import annotations

import csv
import io
import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import BASE_DIR, settings
from .database import get_session, init_db
from .jobs import run_daily_job
from .models import JournalRecherche, Prospect
from .scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crée la base vide au premier lancement, puis démarre le cron interne.
    init_db()
    start_scheduler()
    logger.info("Cordiste Prospection AI démarré.")
    yield
    shutdown_scheduler()


app = FastAPI(title="Cordiste Prospection AI", version="1.0.0", lifespan=lifespan)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------------
# Tableau de bord
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return (TEMPLATES_DIR / "dashboard.html").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "smtp_configured": settings.smtp.is_configured}


@app.get("/api/stats")
def stats(session: Session = Depends(get_session)) -> dict:
    total = session.scalar(select(func.count(Prospect.id))) or 0
    aujourdhui = (
        session.scalar(
            select(func.count(Prospect.id)).where(Prospect.date_decouverte == date.today())
        )
        or 0
    )
    par_score = dict(
        session.execute(
            select(Prospect.score_label, func.count(Prospect.id)).group_by(Prospect.score_label)
        ).all()
    )
    par_dept = dict(
        session.execute(
            select(Prospect.departement, func.count(Prospect.id)).group_by(Prospect.departement)
        ).all()
    )
    par_secteur = dict(
        session.execute(
            select(Prospect.secteur, func.count(Prospect.id)).group_by(Prospect.secteur)
        ).all()
    )
    return {
        "total": total,
        "aujourdhui": aujourdhui,
        "par_score": par_score,
        "par_departement": par_dept,
        "par_secteur": par_secteur,
    }


@app.get("/api/prospects")
def list_prospects(
    session: Session = Depends(get_session),
    q: str | None = None,
    departement: str | None = None,
    secteur: str | None = None,
    score_min: int = 0,
    tri: str = "score",
    ordre: str = "desc",
    limit: int = Query(100, le=1000),
    offset: int = 0,
) -> dict:
    stmt = select(Prospect)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            Prospect.nom.ilike(like)
            | Prospect.ville.ilike(like)
            | Prospect.activite.ilike(like)
        )
    if departement:
        stmt = stmt.where(Prospect.departement == departement)
    if secteur:
        stmt = stmt.where(Prospect.secteur == secteur)
    if score_min:
        stmt = stmt.where(Prospect.score >= score_min)

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    col = {
        "score": Prospect.score,
        "nom": Prospect.nom,
        "ville": Prospect.ville,
        "date": Prospect.date_decouverte,
    }.get(tri, Prospect.score)
    col = col.desc() if ordre == "desc" else col.asc()

    rows = session.scalars(stmt.order_by(col).limit(limit).offset(offset)).all()
    return {"total": total, "items": [p.as_dict() for p in rows]}


@app.get("/api/journal")
def journal(session: Session = Depends(get_session), limit: int = Query(50, le=500)) -> dict:
    rows = session.scalars(
        select(JournalRecherche).order_by(JournalRecherche.id.desc()).limit(limit)
    ).all()
    return {"items": [j.as_dict() for j in rows]}


@app.get("/api/export.csv")
def export_csv(session: Session = Depends(get_session)) -> StreamingResponse:
    rows = session.scalars(select(Prospect).order_by(Prospect.score.desc())).all()
    buf = io.StringIO()
    fields = [
        "id", "nom", "activite", "secteur", "naf", "adresse", "ville",
        "code_postal", "departement", "telephone", "email", "site_internet",
        "contact_nom", "siret", "siren", "tranche_effectif",
        "categorie_entreprise", "chiffre_affaires", "score", "score_label",
        "source", "date_decouverte",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for p in rows:
        writer.writerow(p.as_dict())
    buf.seek(0)
    filename = f"prospects_cordiste_{date.today():%Y%m%d}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/run")
def run_now(send_email: bool = False) -> dict:
    """Déclenche manuellement un cycle de prospection (bouton du dashboard)."""
    result = run_daily_job(send_email=send_email)
    return {
        "examines": result.examines,
        "nouveaux": result.nouveaux,
        "mis_a_jour": result.mis_a_jour,
        "doublons": result.doublons,
        "duree_secondes": result.duree_secondes,
        "erreur": result.erreur,
    }
