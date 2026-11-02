from types import SimpleNamespace

import pytest

from app.processing.chunker import chunk_conversation, estimate_tokens


def make_conversation(messages):
    return SimpleNamespace(
        id=1,
        conversation_id="chunk-test",
        title="Chunking test",
        messages=[
            SimpleNamespace(
                id=index + 1,
                position=index,
                role=role,
                content=content,
            )
            for index, (role, content) in enumerate(messages)
        ],
    )


def test_short_messages_are_retained():
    conversation = make_conversation([
        ("user", "What is Nmap?"),
        ("assistant", "Nmap is a network scanning tool."),
    ])

    chunks = chunk_conversation(
        conversation,
        size_tokens=500,
        overlap_tokens=75,
        min_tokens=30,
    )

    assert len(chunks) == 2
    assert chunks[0].content == "What is Nmap?"
    assert chunks[1].content == "Nmap is a network scanning tool."
    assert chunks[0].role == "user"
    assert chunks[1].role == "assistant"


def test_long_message_splits_with_overlap():
    content = " ".join(f"word{i}" for i in range(1000))
    conversation = make_conversation([("assistant", content)])

    chunks = chunk_conversation(
        conversation,
        size_tokens=100,
        overlap_tokens=20,
        min_tokens=10,
    )

    assert len(chunks) > 1
    assert all(chunk.estimated_tokens <= 100 for chunk in chunks)

    first_words = chunks[0].content.split()
    second_words = chunks[1].content.split()

    # The second chunk starts with a word-aligned tail of the first chunk.
    assert " ".join(first_words[-5:]) in chunks[1].content
    assert second_words[:5] != first_words[:5]


def test_chunks_respect_hard_token_budget():
    # Regression: packed pieces plus the overlap separator must still fit.
    content = (
        ("X" * 300)
        + "\n\n"
        + ("A" * 100)
        + " "
        + ("B" * 18)
    )
    conversation = make_conversation([("assistant", content)])

    chunks = chunk_conversation(
        conversation,
        size_tokens=50,
        overlap_tokens=20,
        min_tokens=0,
    )

    assert len(chunks) > 1
    assert all(chunk.estimated_tokens <= 50 for chunk in chunks)


def test_large_overlap_still_respects_hard_token_budget():
    code = "```python\n" + "\n".join(
        f"print({index})" for index in range(50)
    ) + "\n```"
    conversation = make_conversation([("assistant", code)])

    chunks = chunk_conversation(
        conversation,
        size_tokens=50,
        overlap_tokens=49,
        min_tokens=0,
    )

    assert chunks
    assert all(chunk.estimated_tokens <= 50 for chunk in chunks)


def test_chunks_do_not_cross_message_boundaries():
    conversation = make_conversation([
        ("user", "ALPHA " * 200),
        ("assistant", "BETA " * 200),
    ])

    chunks = chunk_conversation(
        conversation,
        size_tokens=50,
        overlap_tokens=10,
        min_tokens=5,
    )

    for chunk in chunks:
        if chunk.message_position == 0:
            assert "BETA" not in chunk.content
        else:
            assert "ALPHA" not in chunk.content


def test_small_code_block_is_preserved():
    content = (
        "Run this command:\n\n"
        "```bash\npipx install shell-gpt\n```"
    )
    conversation = make_conversation([("assistant", content)])

    chunks = chunk_conversation(
        conversation,
        size_tokens=200,
        overlap_tokens=20,
        min_tokens=10,
    )

    assert len(chunks) == 1
    assert chunks[0].content == content


def test_oversized_code_block_is_re_fenced():
    code = "\n".join(f"print({index})" for index in range(200))
    content = f"```python\n{code}\n```"
    conversation = make_conversation([("assistant", content)])

    chunks = chunk_conversation(
        conversation,
        size_tokens=100,
        overlap_tokens=0,
        min_tokens=10,
    )

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk.content.startswith("```python")
        assert chunk.content.rstrip().endswith("```")


def test_empty_messages_are_skipped():
    conversation = make_conversation([
        ("user", "   "),
        ("assistant", "Useful answer"),
    ])

    chunks = chunk_conversation(conversation)

    assert len(chunks) == 1
    assert chunks[0].message_position == 1


def test_chunk_ids_are_stable_and_message_aware():
    conversation = make_conversation([
        ("user", "hello"),
        ("assistant", "world"),
    ])

    chunks = chunk_conversation(conversation)

    assert [chunk.chunk_id for chunk in chunks] == [
        "chunk-test:0:0",
        "chunk-test:1:0",
    ]


def test_unicode_content_is_retained():
    content = "Kali Linux 指纹认证配置 — 使用 PAM。"
    conversation = make_conversation([("user", content)])

    chunks = chunk_conversation(conversation)

    assert chunks[0].content == content
    assert estimate_tokens(content) >= 1


def test_empty_conversation_returns_no_chunks():
    conversation = make_conversation([])

    assert chunk_conversation(conversation) == []


@pytest.mark.parametrize(
    "options",
    [
        {"size_tokens": 0},
        {"size_tokens": -1},
        {"overlap_tokens": -1},
        {"size_tokens": 100, "overlap_tokens": 100},
        {"size_tokens": 100, "overlap_tokens": 101},
        {"size_tokens": 100, "min_tokens": 101},
        {"chunking_version": "   "},
    ],
)
def test_invalid_chunking_options_are_rejected(options):
    conversation = make_conversation([("user", "hello")])

    with pytest.raises(ValueError):
        chunk_conversation(conversation, **options)
