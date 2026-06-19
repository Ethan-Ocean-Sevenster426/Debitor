"""Render the lawyer progress report as a detailed, KPI-focused PDF.

Severity (how long a matter has been idle) is colour-coded, every company name
links back to its matter page on the site, and the headline KPIs sit up top.
Uses reportlab (pure-Python, no system dependencies). ASCII-only punctuation so
the standard Helvetica font renders everything cleanly.
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BRAND = colors.HexColor("#0E7C7B")
NAVY = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
GRIDC = colors.HexColor("#e5e7eb")

# Severity bands by days since the matter was last worked.
SEV = {
    "ok":       {"bg": colors.HexColor("#ecfdf5"), "hex": "#15803d", "label": "On track"},
    "warning":  {"bg": colors.HexColor("#fef3c7"), "hex": "#b45309", "label": "Warning"},
    "critical": {"bg": colors.HexColor("#fde8e8"), "hex": "#b91c1c", "label": "Critical"},
}


def _money(v):
    try:
        return "R {:,.2f}".format(float(v))
    except (TypeError, ValueError):
        return "R 0.00"


def build_report_pdf(ctx):
    """Return PDF bytes for the report context produced by reports.build_lawyer_report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title="Lawyer Progress Report",
        topMargin=15 * mm, bottomMargin=13 * mm, leftMargin=14 * mm, rightMargin=14 * mm)

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], textColor=BRAND, fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=base["Normal"], textColor=MUTED, fontSize=9, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=NAVY, fontSize=12, spaceBefore=12, spaceAfter=4)
    cell = ParagraphStyle("cell", parent=base["Normal"], fontSize=8.5, leading=11)
    cellh = ParagraphStyle("cellh", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    small = ParagraphStyle("small", parent=base["Normal"], fontSize=8, textColor=MUTED, leading=11)
    kpi_num = ParagraphStyle("kpinum", parent=base["Normal"], fontSize=16, leading=18,
                             alignment=TA_CENTER, textColor=BRAND, fontName="Helvetica-Bold")
    kpi_lbl = ParagraphStyle("kpilbl", parent=base["Normal"], fontSize=7, leading=9,
                             alignment=TA_CENTER, textColor=MUTED)

    k = ctx["kpis"]
    gen, ps = ctx["generated_at"], ctx["period_start"]
    story = []

    story.append(Paragraph("Lawyer Progress Report", h1))
    story.append(Paragraph("Reporting period: %s to %s" % (
        ps.strftime("%d %b %Y"), gen.strftime("%d %b %Y")), sub))

    # ---- KPI tiles (two rows of four) ----
    tiles = [
        (k["active"], "Active matters"),
        (k["new"], "New this period"),
        ("%s%%" % k["avg_completion"], "Avg completion"),
        (k["in_litigation"], "In litigation"),
        (k["idle_7"], "Idle 7+ days"),
        (k["idle_14"], "Idle 14+ days"),
        (_money(k["recovered_period"]), "Recovered (period)"),
        (_money(k["recovered_total"]), "Recovered (all time)"),
    ]
    tile_rows = []
    for i in range(0, len(tiles), 4):
        tile_rows.append([[Paragraph(str(n), kpi_num), Paragraph(lbl, kpi_lbl)]
                          for n, lbl in tiles[i:i + 4]])
    kt = Table(tile_rows, colWidths=[doc.width / 4.0] * 4)
    kt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5fbfb")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6efee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(kt)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "%s in litigation, %s still in collections. Average %s day(s) since last worked. "
        "%s matter(s) closed this period." % (
            k["in_litigation"], k["in_collections"], k["avg_days_idle"], k["closed_period"]), small))

    # ---- Severity legend ----
    story.append(Spacer(1, 8))
    legend = Table([[
        Paragraph('<b><font color="%s">On track</font></b> &mdash; worked &lt;7 days ago' % SEV["ok"]["hex"], small),
        Paragraph('<b><font color="%s">Warning</font></b> &mdash; 7-13 days idle' % SEV["warning"]["hex"], small),
        Paragraph('<b><font color="%s">Critical</font></b> &mdash; 14+ days idle' % SEV["critical"]["hex"], small),
    ]], colWidths=[doc.width / 3.0] * 3)
    legend.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), SEV["ok"]["bg"]),
        ("BACKGROUND", (1, 0), (1, 0), SEV["warning"]["bg"]),
        ("BACKGROUND", (2, 0), (2, 0), SEV["critical"]["bg"]),
        ("BOX", (0, 0), (-1, -1), 0.4, GRIDC), ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(legend)

    header_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIDC),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    def _link(m):
        return '<a href="%s" color="#0E7C7B"><b>%s</b></a>' % (m["url"], escape(m["name"]))

    # ---- Newly handed over ----
    story.append(Paragraph("Newly handed over (%s)" % k["new"], h2))
    if ctx["new_matters"]:
        data = [[Paragraph(t, cellh) for t in ("Company", "Handed over", "By")]]
        for m in ctx["new_matters"]:
            data.append([
                Paragraph(_link(m), cell),
                Paragraph(m["sent_at"].strftime("%d %b %Y") if m["sent_at"] else "-", cell),
                Paragraph(escape(m["sent_by"] or "-"), cell),
            ])
        t = Table(data, colWidths=[doc.width * 0.5, doc.width * 0.25, doc.width * 0.25])
        t.setStyle(TableStyle(header_cmds))
        story.append(t)
    else:
        story.append(Paragraph("No companies handed over this period.", small))

    # ---- Active matters detail ----
    story.append(Paragraph("Active matters - detail (%s)" % k["active"], h2))
    if ctx["active_matters"]:
        headers = ("Company", "Progress", "Stage", "Route", "Last worked", "Severity")
        data = [[Paragraph(t, cellh) for t in headers]]
        cmds = list(header_cmds)
        for idx, m in enumerate(ctx["active_matters"], start=1):
            sev = SEV[m["severity"]]
            last = m["last_worked"]
            last_cell = ("%s<br/><font size=7 color='#9ca3af'>%s day%s ago</font>" % (
                last.strftime("%d %b %Y") if last else "-",
                m["days_idle"], "" if m["days_idle"] == 1 else "s"))
            data.append([
                Paragraph(_link(m), cell),
                Paragraph("%s/%s (%s%%)" % (m["done"], m["total"], m["pct"]), cell),
                Paragraph("Litigation" if m["in_litigation"] else "Collections", cell),
                Paragraph(escape(m["route_summary"]), cell),
                Paragraph(last_cell, cell),
                Paragraph('<font color="%s"><b>%s</b></font>' % (sev["hex"], sev["label"]), cell),
            ])
            cmds.append(("BACKGROUND", (0, idx), (-1, idx), sev["bg"]))
        t = Table(data, colWidths=[doc.width * c for c in (0.24, 0.13, 0.12, 0.22, 0.16, 0.13)],
                  repeatRows=1)
        t.setStyle(TableStyle(cmds))
        story.append(t)
    else:
        story.append(Paragraph("No active matters.", small))

    # ---- Footer ----
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        'Open the Lawyers page to investigate: <a href="%s" color="#0E7C7B">%s</a>'
        % (ctx["legal_url"], ctx["legal_url"]), small))
    story.append(Paragraph(
        "Generated automatically by the FSA Debtor System on %s."
        % gen.strftime("%d %b %Y %H:%M"), small))

    doc.build(story)
    return buf.getvalue()
