import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.generators.markdown_blocks import (
    parse_blocks,
    strip_inline_html,
)
from app.generators.utils import get_output_path


NAVY = RGBColor(17, 24, 39)
BLUE = RGBColor(37, 99, 235)
GREEN = RGBColor(22, 101, 52)
MUTED = RGBColor(100, 116, 139)

CODE_FILL = "F1F5F9"
HEADER_FILL = "111827"
RULE_COLOR = "E2E8F0"

INLINE_RE = re.compile(
    r"(`[^`]+`|\*\*.+?\*\*|\*[^*\n]+?\*)",
    re.DOTALL,
)


def add_inline_runs(
    paragraph,
    text,
    *,
    bold=False,
    size=None,
    color=None,
):
    """Add text to a paragraph, applying inline Markdown formatting."""

    text = strip_inline_html(text)

    for token in INLINE_RE.split(text):
        if not token:
            continue

        if token.startswith("`") and token.endswith("`") and len(token) > 2:
            run = paragraph.add_run(token[1:-1])
            run.font.name = "DejaVu Sans Mono"
            run.font.size = Pt((size or 10) - 1)
            run.font.color.rgb = RGBColor(4, 120, 87)
        elif token.startswith("**") and token.endswith("**") and len(token) > 4:
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(token)

        if bold:
            run.bold = True

        if size is not None:
            run.font.size = Pt(size)

        if color is not None:
            run.font.color.rgb = color


PPR_AFTER_PBDR = (
    "w:shd",
    "w:tabs",
    "w:suppressAutoHyphens",
    "w:kinsoku",
    "w:wordWrap",
    "w:overflowPunct",
    "w:topLinePunct",
    "w:autoSpaceDE",
    "w:autoSpaceDN",
    "w:bidi",
    "w:adjustRightInd",
    "w:snapToGrid",
    "w:spacing",
    "w:ind",
    "w:contextualSpacing",
    "w:mirrorIndents",
    "w:suppressOverlap",
    "w:jc",
    "w:textDirection",
    "w:textAlignment",
    "w:textboxTightWrap",
    "w:outlineLvl",
    "w:divId",
    "w:cnfStyle",
    "w:rPr",
    "w:sectPr",
    "w:pPrChange",
)

PPR_AFTER_SHD = PPR_AFTER_PBDR[1:]

TCPR_AFTER_SHD = (
    "w:noWrap",
    "w:tcMar",
    "w:textDirection",
    "w:tcFitText",
    "w:vAlign",
    "w:hideMark",
    "w:headers",
    "w:cellIns",
    "w:cellDel",
    "w:cellMerge",
    "w:tcPrChange",
)


def make_shading(fill):
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)
    return shading


def shade_paragraph(paragraph, fill):
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.insert_element_before(make_shading(fill), *PPR_AFTER_SHD)


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.insert_element_before(make_shading(fill), *TCPR_AFTER_SHD)


def add_rule(document):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(8)

    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), RULE_COLOR)
    borders.append(bottom)
    p_pr.insert_element_before(borders, *PPR_AFTER_PBDR)


def add_code_block(document, code):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.15)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    shade_paragraph(paragraph, CODE_FILL)

    run = paragraph.add_run(code or " ")
    run.font.name = "DejaVu Sans Mono"
    run.font.size = Pt(8.5)

    r_pr = run._element.get_or_add_rPr()
    fonts = r_pr.get_or_add_rFonts()
    fonts.set(qn("w:eastAsia"), "DejaVu Sans Mono")


def add_table(document, rows):
    if not rows:
        return

    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"

    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            cell = table.cell(row_index, column_index)
            cell.text = ""

            paragraph = cell.paragraphs[0]
            add_inline_runs(
                paragraph,
                value or " ",
                bold=row_index == 0,
                size=9,
                color=RGBColor(255, 255, 255) if row_index == 0 else None,
            )

            if row_index == 0:
                shade_cell(cell, HEADER_FILL)

    document.add_paragraph()


def add_heading(document, level, text):
    paragraph = document.add_heading("", level=min(level, 4))
    paragraph.paragraph_format.keep_with_next = True
    add_inline_runs(paragraph, text)

    color = NAVY if level <= 2 else BLUE

    for run in paragraph.runs:
        run.font.color.rgb = color


def add_block(document, block):
    kind = block[0]

    if kind == "code":
        add_code_block(document, block[1])
    elif kind == "paragraph":
        add_inline_runs(document.add_paragraph(), block[1])
    elif kind == "heading":
        add_heading(document, block[1], block[2])
    elif kind == "bullet":
        paragraph = document.add_paragraph(style="List Bullet")
        add_inline_runs(paragraph, block[1])
    elif kind == "numbered":
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.first_line_indent = Inches(-0.22)
        add_inline_runs(paragraph, block[1])
    elif kind == "task":
        paragraph = document.add_paragraph(style="List Bullet")
        marker = "☑" if block[1] else "☐"
        add_inline_runs(paragraph, f"{marker} {block[2]}")
    elif kind == "quote":
        paragraph = document.add_paragraph(style="Quote")
        paragraph.paragraph_format.left_indent = Inches(0.3)
        add_inline_runs(paragraph, block[1])

        for run in paragraph.runs:
            run.italic = True
            run.font.color.rgb = MUTED
    elif kind == "table":
        add_table(document, block[1])
    elif kind == "rule":
        add_rule(document)


def generate_docx(conversation) -> str:
    """Generate an editable DOCX for a stored conversation."""

    output_path = get_output_path(
        conversation.conversation_id,
        "docx",
    )

    document = Document()

    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    # Default font
    normal = document.styles["Normal"]
    normal.font.name = "DejaVu Sans"
    normal.font.size = Pt(10)

    # Document title
    title = document.add_heading(
        conversation.title,
        level=0,
    )
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    metadata = document.add_paragraph()
    metadata.add_run("Conversation ID: ").bold = True
    metadata.add_run(conversation.conversation_id)

    add_rule(document)

    for message in conversation.messages:
        role_heading = document.add_heading(
            message.role.capitalize(),
            level=2,
        )
        role_heading.paragraph_format.keep_with_next = True

        for run in role_heading.runs:
            run.font.color.rgb = (
                BLUE if message.role == "user" else GREEN
            )

        for block in parse_blocks(message.content):
            add_block(document, block)

    # Footer
    for section in document.sections:
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("Generated by ChatVault AI")

    document.save(str(output_path))

    return str(output_path)
