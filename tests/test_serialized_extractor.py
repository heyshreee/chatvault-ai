
from app.ingestion.extractor import extract_serialized_messages


def build_serialized_payload():
    """
    Build a small synthetic payload matching the observed
    ChatGPT serialized structure. No real conversation text is used.
    """

    payload = []

    def add(value):
        payload.append(value)
        return len(payload) - 1

    def add_object(fields):
        obj = {}

        for name, value_ref in fields.items():
            property_ref = add(name)
            obj[f"_{property_ref}"] = value_ref

        return add(obj)

    def add_message(node_id, role, content_type, parts=None):
        node_id_ref = add(node_id)

        role_ref = add(role)
        author_ref = add_object({
            "role": role_ref
        })

        content_type_ref = add(content_type)

        content_fields = {
            "content_type": content_type_ref
        }

        if parts is not None:
            part_refs = [add(part) for part in parts]
            parts_ref = add(part_refs)
            content_fields["parts"] = parts_ref

        content_ref = add_object(content_fields)

        message_ref = add_object({
            "author": author_ref,
            "content": content_ref
        })

        node_ref = add_object({
            "id": node_id_ref,
            "message": message_ref
        })

        return node_id, node_id_ref, node_ref

    messages = [
        ("node-1", "system", "text", ["System instructions"]),
        ("node-2", "user", "text", ["First user message"]),
        ("node-3", "assistant", "text", ["First answer"]),
        ("node-4", "tool", "text", ["Internal tool output"]),
        ("node-5", "assistant", "thoughts", None),
        ("node-6", "assistant", "text", [""]),
        ("node-7", "user", "text", ["Second user message"]),
        ("node-8", "assistant", "text", ["Final answer"]),
    ]

    mapping = {}
    linear_refs = []

    for node_id, role, content_type, parts in messages:
        actual_id, id_ref, node_ref = add_message(
            node_id,
            role,
            content_type,
            parts
        )

        mapping[f"_{actual_id}"] = node_ref

        linear_ref = add_object({
            "id": id_ref
        })

        linear_refs.append(linear_ref)

    mapping_ref = add(mapping)
    linear_ref = add(linear_refs)
    title_ref = add("Regression Test Conversation")

    add_object({
        "title": title_ref,
        "mapping": mapping_ref,
        "linear_conversation": linear_ref
    })

    return payload


def test_serialized_extractor_preserves_order_and_filters_messages():
    payload = build_serialized_payload()

    messages = extract_serialized_messages(payload)

    assert len(messages) == 4

    assert [message.role for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]

    assert [message.content for message in messages] == [
        "First user message",
        "First answer",
        "Second user message",
        "Final answer",
    ]

    assert [message.position for message in messages] == [
        0, 1, 2, 3
    ]


def test_serialized_extractor_skips_internal_and_empty_messages():
    payload = build_serialized_payload()

    messages = extract_serialized_messages(payload)

    contents = [message.content for message in messages]

    assert "System instructions" not in contents
    assert "Internal tool output" not in contents
    assert "" not in contents
