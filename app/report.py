"""Construction du contenu du rapport quotidien (HTML + texte)."""
from __future__ import annotations

from datetime import date

from . import ai
from .prospecting import RunResult

COMPANY = "Cordiste Île-de-France"


def build_subject(result: RunResult) -> str:
    return f"[Prospection] {result.nouveaux} nouveaux prospects — {date.today():%d/%m/%Y}"


def _row(p: dict) -> str:
    def cell(v):
        return v if v not in (None, "") else "—"

    site = p.get("site_internet")
    site_html = f'<a href="{site}">{site}</a>' if site else "—"
    justif = p.get("score_justification")
    justif_html = (
        f'<br><span style="color:#64748b;font-size:12px">💡 {justif}</span>' if justif else ""
    )
    return f"""
      <tr>
        <td>{cell(p.get('score_label'))}</td>
        <td><strong>{cell(p.get('nom'))}</strong>{justif_html}</td>
        <td>{cell(p.get('activite'))}</td>
        <td>{cell(p.get('ville'))} ({cell(p.get('departement'))})</td>
        <td>{cell(p.get('telephone'))}</td>
        <td>{cell(p.get('email'))}</td>
        <td>{site_html}</td>
        <td>{cell(p.get('contact_nom'))}</td>
      </tr>"""


def build_html(result: RunResult) -> str:
    # Résumé IA optionnel (vide si l'IA est désactivée ou injoignable).
    summary = ai.summarize_prospects(result.nouveaux_prospects) if ai.is_available() else None
    summary_block = (
        f"""<div style="background:#eef2ff;border-left:4px solid #6366f1;border-radius:8px;
             padding:14px 16px;margin-bottom:20px">
          <div style="font-weight:700;margin-bottom:6px">🤖 Analyse IA du jour</div>
          <div style="color:#334155">{summary}</div>
        </div>"""
        if summary else ""
    )

    if not result.nouveaux_prospects:
        body = "<p>Aucun nouveau prospect découvert aujourd'hui.</p>"
    else:
        rows = "".join(_row(p) for p in result.nouveaux_prospects)
        body = f"""
        <table cellpadding="8" cellspacing="0" border="0"
               style="border-collapse:collapse;width:100%;font-size:13px">
          <thead>
            <tr style="background:#0f172a;color:#fff;text-align:left">
              <th>Score</th><th>Entreprise</th><th>Activité</th><th>Ville</th>
              <th>Téléphone</th><th>Email</th><th>Site</th><th>Contact</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"></head>
<body style="font-family:Arial,Helvetica,sans-serif;color:#0f172a;margin:0;padding:24px;background:#f1f5f9">
  <div style="max-width:900px;margin:auto;background:#fff;border-radius:12px;padding:24px">
    <h2 style="margin:0 0 4px">{COMPANY} — Rapport de prospection</h2>
    <p style="color:#64748b;margin:0 0 20px">{date.today():%A %d %B %Y}</p>
    {summary_block}
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
      <div style="flex:1;min-width:120px;background:#ecfdf5;border-radius:10px;padding:14px">
        <div style="font-size:26px;font-weight:700">{result.nouveaux}</div>
        <div style="color:#475569">Nouveaux prospects</div>
      </div>
      <div style="flex:1;min-width:120px;background:#eff6ff;border-radius:10px;padding:14px">
        <div style="font-size:26px;font-weight:700">{result.mis_a_jour}</div>
        <div style="color:#475569">Fiches mises à jour</div>
      </div>
      <div style="flex:1;min-width:120px;background:#f8fafc;border-radius:10px;padding:14px">
        <div style="font-size:26px;font-weight:700">{result.doublons}</div>
        <div style="color:#475569">Doublons évités</div>
      </div>
    </div>
    {body}
    <p style="color:#94a3b8;font-size:12px;margin-top:24px">
      Rapport généré automatiquement par Cordiste Prospection AI. Données publiques
      (base SIRENE). Prospection B2B — entreprises privées uniquement.
    </p>
  </div>
</body></html>"""


def build_text(result: RunResult) -> str:
    lines = [
        f"{COMPANY} — Rapport de prospection du {date.today():%d/%m/%Y}",
        "",
        f"Nouveaux prospects : {result.nouveaux}",
        f"Fiches mises à jour : {result.mis_a_jour}",
        f"Doublons évités : {result.doublons}",
        "",
    ]
    for p in result.nouveaux_prospects:
        lines.append(
            f"- {p.get('score_label','')} {p.get('nom','')} | {p.get('activite','')} | "
            f"{p.get('ville','')} ({p.get('departement','')}) | "
            f"tel: {p.get('telephone') or '—'} | email: {p.get('email') or '—'} | "
            f"site: {p.get('site_internet') or '—'} | contact: {p.get('contact_nom') or '—'}"
        )
    return "\n".join(lines)
