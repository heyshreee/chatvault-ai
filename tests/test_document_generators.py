from types import SimpleNamespace

from docx import Document

from app.generators.docx_generator import generate_docx
from app.generators.markdown_blocks import parse_blocks
from app.generators.pdf_generator import generate_pdf
from app.processing.text_cleaner import clean_chatgpt_text


def test_clean_chatgpt_text_removes_ui_annotations():
    text = (
        "Read the "
        "\ue200url\ue202OAuth 2.0 Security Best Current Practice"
        "\ue202https://www.rfc-editor.org/rfc/rfc9700\ue201. "
        "Try \ue200entity\ue202[\"software\",\"PortSwigger Academy\","
        "\"training\"]\ue201.\n"
        "\ue200genui\ue202{\"suggest_automation\":{}}\ue201"
        "\ue200image_group\ue202{\"layout\":\"carousel\"}\ue201"
        "Keep **Markdown** and `code`."
    )

    cleaned = clean_chatgpt_text(text)

    assert "OAuth 2.0 Security Best Current Practice" in cleaned
    assert "PortSwigger Academy" in cleaned
    assert "suggest_automation" not in cleaned
    assert "image_group" not in cleaned
    assert "\ue200" not in cleaned
    assert "**Markdown**" in cleaned


def test_parse_blocks_handles_export_markdown():
    content = """## Heading

| Host | Port |
|---|---|
| example.com | 443 |

> Quoted text

- Bullet item
1. Numbered item
- [x] Completed task
- [ ] Pending task

---

```python
print("hello")
```
"""

    blocks = parse_blocks(content)

    assert [block[0] for block in blocks] == [
        "heading",
        "table",
        "quote",
        "bullet",
        "numbered",
        "task",
        "task",
        "rule",
        "code",
    ]
    assert blocks[0] == ("heading", 2, "Heading")
    assert blocks[1][1] == [
        ["Host", "Port"],
        ["example.com", "443"],
    ]
    assert blocks[5][1] is True
    assert blocks[6][1] is False


def make_conversation():
    return SimpleNamespace(
        conversation_id="test-conversation",
        title="Test Conversation",
        messages=[
            SimpleNamespace(
                role="user",
                content="Show me a **table** and `code`.",
            ),
            SimpleNamespace(
                role="assistant",
                content=(
                    "## Results\n\n"
                    "| Host | Status |\n"
                    "|---|---|\n"
                    "| example.com | ok |\n\n"
                    "> Keep this in mind.\n\n"
                    "- One\n"
                    "- Two\n\n"
                    "```python\nprint('hello')\n```\n\n"
                    "Ready to go! \u2728 \U0001f31f\n\n"
                    "<badge color=\"success\">Done</badge>"
                ),
            ),
        ],
    )


def test_generate_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.generators.utils.GENERATED_DIR",
        tmp_path,
    )

    path = generate_pdf(make_conversation())
    data = (tmp_path / "test-conversation.pdf").read_bytes()

    assert path.endswith("test-conversation.pdf")
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_generate_docx_formats_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.generators.utils.GENERATED_DIR",
        tmp_path,
    )

    generate_docx(make_conversation())
    document = Document(tmp_path / "test-conversation.docx")

    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Test Conversation" in text
    assert "**" not in text
    assert "<badge" not in text

    assert len(document.tables) == 1
    assert document.tables[0].cell(0, 0).text == "Host"
    assert document.tables[0].cell(1, 0).text == "example.com"

    assert any(
        run.font.name == "DejaVu Sans Mono"
        for paragraph in document.paragraphs
        for run in paragraph.runs
    )
