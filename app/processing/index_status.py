from enum import StrEnum


class IndexStatus(StrEnum):
    """Lifecycle states for a conversation's vector index."""

    NOT_INDEXED = "not_indexed"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
