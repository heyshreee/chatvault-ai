
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from app.generators.markdown_blocks import (
    parse_blocks,
    strip_inline_html,
)
from app.generators.utils import get_output_path


# --------------------------------------------------
# Design system
# --------------------------------------------------

NAVY = colors.HexColor("#111827")
NAVY_LIGHT = colors.HexColor("#1F2937")
GREEN = colors.HexColor("#059669")
BLUE = colors.HexColor("#2563EB")

TEXT = colors.HexColor("#263244")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")
SURFACE = colors.HexColor("#F8FAFC")
CODE_BG = colors.HexColor("#F1F5F9")

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def register_fonts():
    fonts = {
        "CVSans": f"{FONT_DIR}/DejaVuSans.ttf",
        "CVSans-Bold": f"{FONT_DIR}/DejaVuSans-Bold.ttf",
        "CVMono": f"{FONT_DIR}/DejaVuSansMono.ttf",
    }

    registered = set(pdfmetrics.getRegisteredFontNames())

    for name, path in fonts.items():
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, path))


# --------------------------------------------------
# Markdown formatting
# --------------------------------------------------

SYMBOL_REPLACEMENTS = {
    "─": "-",
    "━": "=",
    "│": "|",
    "┃": "|",
    "┌": "+",
    "┐": "+",
    "└": "+",
    "┘": "+",
    "├": "+",
    "┤": "+",
    "┬": "+",
    "┴": "+",
    "┼": "+",
    "→": "->",
    "←": "<-",
    "㉿": "@",
    "✅": "✓",
    "✔": "✓",
    "☑": "✓",
    "❌": "x",
    "❎": "x",
    "⭐": "★",
    "✨": "★",
    "🌟": "★",
}

# Emoji are not present in the bundled DejaVu fonts. Drop the remaining
# pictographs and variation selectors instead of rendering empty boxes.
EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "\uFE0F\u200D"
    "]"
)


def clean_terminal_characters(text):
    """
    Replace terminal and emoji characters that may render
    inconsistently with the selected PDF font.
    """

    text = "".join(
        SYMBOL_REPLACEMENTS.get(char, char)
        for char in text
    )

    return EMOJI_RE.sub("", text)


def inline_markdown(text):
    """Convert basic Markdown inline syntax to ReportLab markup."""

    text = escape(clean_terminal_characters(strip_inline_html(text)))

    # Inline code
    text = re.sub(
        r"`([^`]+)`",
        r'<font name="CVMono" color="#047857">\1</font>',
        text,
    )

    # Bold
    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text,
    )

    # Italic
    text = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        r"<i>\1</i>",
        text,
    )

    return text


# --------------------------------------------------
# PDF page design
# --------------------------------------------------

def draw_page(canvas, document):
    canvas.saveState()

    width, height = A4

    # Running header on subsequent pages
    if document.page > 1:
        canvas.setFillColor(NAVY)
        canvas.rect(
            0,
            height - 14 * mm,
            width,
            14 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(colors.white)
        canvas.setFont("CVSans-Bold", 8)

        canvas.drawString(
            18 * mm,
            height - 9 * mm,
            "CHATVAULT AI",
        )

        canvas.setFont("CVSans", 8)
        canvas.drawRightString(
            width - 18 * mm,
            height - 9 * mm,
            "CONVERSATION ARCHIVE",
        )

    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(
        18 * mm,
        17 * mm,
        width - 18 * mm,
        17 * mm,
    )

    canvas.setFillColor(MUTED)
    canvas.setFont("CVSans", 7.5)

    canvas.drawString(
        18 * mm,
        11 * mm,
        "Generated with ChatVault AI",
    )

    canvas.drawRightString(
        width - 18 * mm,
        11 * mm,
        f"{document.page}",
    )

    canvas.restoreState()


# --------------------------------------------------
# Styles
# --------------------------------------------------

def create_styles():
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "CVTitle",
            parent=base["Title"],
            fontName="CVSans-Bold",
            fontSize=23,
            leading=30,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),

        "metadata": ParagraphStyle(
            "CVMetadata",
            fontName="CVSans",
            fontSize=8,
            leading=13,
            textColor=colors.HexColor("#CBD5E1"),
        ),

        "role": ParagraphStyle(
            "CVRole",
            fontName="CVSans-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.white,
        ),

        "body": ParagraphStyle(
            "CVBody",
            fontName="CVSans",
            fontSize=9,
            leading=15,
            textColor=TEXT,
            spaceAfter=3,
            wordWrap="CJK",
        ),

        "heading1": ParagraphStyle(
            "CVHeading1",
            fontName="CVSans-Bold",
            fontSize=14,
            leading=19,
            textColor=NAVY,
            spaceBefore=5,
            spaceAfter=5,
            keepWithNext=1,
        ),

        "heading2": ParagraphStyle(
            "CVHeading2",
            fontName="CVSans-Bold",
            fontSize=11,
            leading=16,
            textColor=NAVY,
            spaceBefore=4,
            spaceAfter=4,
            keepWithNext=1,
        ),

        "heading3": ParagraphStyle(
            "CVHeading3",
            fontName="CVSans-Bold",
            fontSize=9.5,
            leading=14,
            textColor=BLUE,
            spaceBefore=3,
            spaceAfter=3,
            keepWithNext=1,
        ),

        "quote": ParagraphStyle(
            "CVQuote",
            fontName="CVSans",
            fontSize=9,
            leading=14,
            textColor=MUTED,
        ),

        "table": ParagraphStyle(
            "CVTable",
            fontName="CVSans",
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT,
            wordWrap="CJK",
        ),

        "tableHeader": ParagraphStyle(
            "CVTableHeader",
            fontName="CVSans-Bold",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.white,
            wordWrap="CJK",
        ),

        "bullet": ParagraphStyle(
            "CVBullet",
            fontName="CVSans",
            fontSize=9,
            leading=14,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=TEXT,
            spaceAfter=3,
        ),

        "code": ParagraphStyle(
            "CVCode",
            fontName="CVMono",
            fontSize=7.5,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
            wordWrap="CJK",
        ),
    }


# --------------------------------------------------
# Message rendering
# --------------------------------------------------

def format_code_line(line):
    """Preserve code indentation in ReportLab paragraphs."""

    line = escape(EMOJI_RE.sub("", line))

    return (
        line
        .replace("\t", "&nbsp;" * 4)
        .replace(" ", "&nbsp;")
        or "&nbsp;"
    )


def add_code_block(story, code, styles, available_width):
    lines = code.splitlines() or [""]

    rows = [
        [Paragraph(format_code_line(line), styles["code"])]
        for line in lines
    ]

    table = Table(
        rows,
        colWidths=[available_width],
        repeatRows=0,
        splitByRow=1,
        hAlign="LEFT",
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 4),
    ]))

    story.append(table)
    story.append(Spacer(1, 3 * mm))


def add_table(story, rows, styles, available_width):
    if not rows:
        return

    columns = len(rows[0])

    weights = []
    for column in range(columns):
        longest = max(
            (len(row[column]) for row in rows),
            default=1,
        )
        longest_word = max(
            (
                len(word)
                for row in rows
                for word in row[column].split()
            ),
            default=1,
        )
        weights.append(
            max(longest_word * 1.8, min(longest, 48), 5)
        )

    total_weight = sum(weights) or 1
    col_widths = [
        available_width * weight / total_weight
        for weight in weights
    ]

    data = []

    for row_index, row in enumerate(rows):
        style = (
            styles["tableHeader"]
            if row_index == 0
            else styles["table"]
        )
        data.append([
            Paragraph(inline_markdown(cell) or " ", style)
            for cell in row
        ])

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(Spacer(1, 2 * mm))
    story.append(table)
    story.append(Spacer(1, 3 * mm))


def add_quote(story, text, styles, available_width):
    formatted = inline_markdown(text).replace("\n", "<br/>")

    quote = Table(
        [[Paragraph(formatted or " ", styles["quote"])]],
        colWidths=[available_width],
        hAlign="LEFT",
    )

    quote.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(Spacer(1, 2 * mm))
    story.append(quote)
    story.append(Spacer(1, 3 * mm))


def add_rule(story):
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=BORDER,
            spaceBefore=2,
            spaceAfter=5,
        )
    )


def add_message(story, message, styles, available_width):
    is_user = message.role == "user"

    role_color = BLUE if is_user else GREEN
    role_label = "YOU" if is_user else "CHATGPT"

    # Speaker label
    label = Table(
        [[Paragraph(role_label, styles["role"])]],
        colWidths=[25 * mm],
    )

    label.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), role_color),
        ("BOX", (0, 0), (-1, -1), 0, role_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(Spacer(1, 4 * mm))
    story.append(label)
    story.append(Spacer(1, 2 * mm))

    # Message body
    for block in parse_blocks(message.content):
        kind = block[0]

        if kind == "code":
            add_code_block(
                story,
                block[1],
                styles,
                available_width,
            )

        elif kind == "paragraph":
            formatted = inline_markdown(block[1]).replace(
                "\n",
                "<br/>",
            )

            story.append(
                Paragraph(formatted, styles["body"])
            )

        elif kind == "heading":
            level = min(block[1], 3)

            story.append(
                Paragraph(
                    inline_markdown(block[2]),
                    styles[f"heading{level}"],
                )
            )

        elif kind == "bullet":
            story.append(
                Paragraph(
                    "&#8226; " + inline_markdown(block[1]),
                    styles["bullet"],
                )
            )

        elif kind == "numbered":
            story.append(
                Paragraph(
                    inline_markdown(block[1]),
                    styles["bullet"],
                )
            )

        elif kind == "task":
            marker = "&#9632;" if block[1] else "&#9633;"

            story.append(
                Paragraph(
                    marker + " " + inline_markdown(block[2]),
                    styles["bullet"],
                )
            )

        elif kind == "quote":
            add_quote(
                story,
                block[1],
                styles,
                available_width,
            )

        elif kind == "table":
            add_table(
                story,
                block[1],
                styles,
                available_width,
            )

        elif kind == "rule":
            add_rule(story)


# --------------------------------------------------
# Main generator
# --------------------------------------------------

def generate_pdf(conversation) -> str:
    """Generate a premium formatted conversation PDF."""

    register_fonts()
    styles = create_styles()

    output_path = get_output_path(
        conversation.conversation_id,
        "pdf",
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=19 * mm,
        leftMargin=19 * mm,
        topMargin=23 * mm,
        bottomMargin=23 * mm,
        title=conversation.title,
        author="ChatVault AI",
        subject="Exported ChatGPT conversation",
    )

    available_width = A4[0] - 38 * mm

    story = []

    # Premium title panel
    title_content = [
        Paragraph(
            "CHATVAULT AI",
            ParagraphStyle(
                "Brand",
                fontName="CVSans-Bold",
                fontSize=9,
                textColor=colors.HexColor("#34D399"),
                alignment=TA_CENTER,
                spaceAfter=9,
            ),
        ),
        Paragraph(
            escape(conversation.title),
            styles["title"],
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            f"CONVERSATION ID  |  "
            f"{escape(conversation.conversation_id)}",
            styles["metadata"],
        ),
    ]

    title_panel = Table(
        [[title_content]],
        colWidths=[available_width],
    )

    title_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("BOX", (0, 0), (-1, -1), 0, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 13 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 13 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 10 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10 * mm),
    ]))

    story.append(title_panel)
    story.append(Spacer(1, 7 * mm))

    # Conversation section
    story.append(
        Paragraph(
            "CONVERSATION",
            ParagraphStyle(
                "SectionTitle",
                fontName="CVSans-Bold",
                fontSize=9,
                textColor=MUTED,
                spaceAfter=2 * mm,
            ),
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.7,
            color=BORDER,
            spaceAfter=2 * mm,
        )
    )

    for message in conversation.messages:
        add_message(
            story,
            message,
            styles,
            available_width,
        )

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    return str(output_path)
