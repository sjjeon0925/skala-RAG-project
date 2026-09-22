"""검증된 Markdown 보고서를 한국어 A4 PDF로 변환한다."""

import html
import os
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from config import PROJECT_ROOT

FONT_CANDIDATES = (
    PROJECT_ROOT / "assets" / "fonts" / "NotoSansKR-Regular.ttf",
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/Library/Fonts/NotoSansCJKkr-Regular.otf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
)


def _font_path() -> Path | None:
    configured = os.getenv("REPORT_PDF_FONT")
    if configured:
        font = Path(configured).expanduser()
        if not font.is_file():
            raise FileNotFoundError(f"REPORT_PDF_FONT 파일 없음: {font}")
        return font
    return next((path for path in FONT_CANDIDATES if path.is_file()), None)


def _register_font() -> str:
    font_path = _font_path()
    name = "ReportKorean" if font_path else "HYGoThic-Medium"
    if name not in pdfmetrics.getRegisteredFontNames():
        if font_path:
            pdfmetrics.registerFont(TTFont(name, str(font_path), subfontIndex=0))
        else:
            pdfmetrics.registerFont(UnicodeCIDFont(name))
    return name


def _styles(font):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=font,
            fontSize=20,
            leading=29,
            textColor=colors.HexColor("#102A43"),
            alignment=TA_CENTER,
            spaceAfter=14,
            wordWrap="CJK",
        ),
        "chapter": ParagraphStyle(
            "ReportChapter",
            parent=base["Heading1"],
            fontName=font,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#0B4F6C"),
            spaceBefore=7,
            spaceAfter=10,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "section": ParagraphStyle(
            "ReportSection",
            parent=base["Heading2"],
            fontName=font,
            fontSize=11.5,
            leading=18,
            textColor=colors.HexColor("#1F3A5F"),
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=16,
            textColor=colors.HexColor("#1F2933"),
            spaceAfter=6,
            wordWrap="CJK",
            splitLongWords=True,
        ),
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9,
            leading=15,
            leftIndent=11 * mm,
            firstLineIndent=-4 * mm,
            spaceAfter=3,
            wordWrap="CJK",
            splitLongWords=True,
        ),
        "nested_bullet": ParagraphStyle(
            "ReportNestedBullet",
            parent=base["BodyText"],
            fontName=font,
            fontSize=8.7,
            leading=14,
            leftIndent=17 * mm,
            firstLineIndent=-4 * mm,
            textColor=colors.HexColor("#52606D"),
            spaceAfter=3,
            wordWrap="CJK",
            splitLongWords=True,
        ),
        "quote": ParagraphStyle(
            "ReportQuote",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9,
            leading=15,
            leftIndent=8 * mm,
            rightIndent=8 * mm,
            borderColor=colors.HexColor("#9FB3C8"),
            borderWidth=0.7,
            borderPadding=6,
            backColor=colors.HexColor("#F0F4F8"),
            textColor=colors.HexColor("#334E68"),
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "reference": ParagraphStyle(
            "ReportReference",
            parent=base["BodyText"],
            fontName=font,
            fontSize=8.3,
            leading=13,
            leftIndent=4 * mm,
            firstLineIndent=-4 * mm,
            spaceAfter=4,
            wordWrap="CJK",
            splitLongWords=True,
        ),
    }


def _paragraph(text, style, *, bullet=None):
    return Paragraph(html.escape(text, quote=False), style, bulletText=bullet)


def _story(markdown_text, styles):
    story = []
    in_references = False
    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if not line:
            story.append(Spacer(1, 2.5 * mm))
            continue
        if line.startswith("# "):
            story.append(_paragraph(line[2:], styles["title"]))
            story.append(Spacer(1, 2 * mm))
            continue
        if line.startswith("## "):
            heading = line[3:]
            if (heading == "REFERENCE" or re.match(r"[1-6]\.\s", heading)) and story:
                story.append(PageBreak())
            in_references = heading == "REFERENCE"
            story.append(_paragraph(heading, styles["chapter"]))
            continue
        if line.startswith("### "):
            story.append(_paragraph(line[4:], styles["section"]))
            continue
        if line.startswith("> "):
            story.append(_paragraph(line[2:], styles["quote"]))
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("- "):
            style = styles["nested_bullet"] if indent else styles["bullet"]
            story.append(_paragraph(stripped[2:], style, bullet="•"))
            continue
        if in_references or re.match(r"\d+\.\s", stripped):
            story.append(_paragraph(stripped, styles["reference"]))
            continue
        story.append(_paragraph(stripped, styles["body"]))
    return story


def export_pdf(markdown_text: str, output_path: Path) -> Path:
    if not markdown_text.strip():
        raise ValueError("빈 보고서는 PDF로 변환할 수 없음")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".pdf.tmp")
    font = _register_font()
    styles = _styles(font)

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setFont(font, 7.5)
        canvas.setFillColor(colors.HexColor("#627D98"))
        canvas.drawString(20 * mm, A4[1] - 12 * mm, "KV Cache 확장 기술 다관점 비교 평가")
        canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, str(document.page))
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(temporary),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="ITME와 CXL-PIM 데이터센터 적용성 비교 평가",
        author="조기퇴근 4조",
        subject="KV Cache 확장 기술 다관점 비교 평가",
    )
    try:
        document.build(_story(markdown_text, styles), onFirstPage=decorate, onLaterPages=decorate)
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return output_path
