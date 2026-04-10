"""Magic-byte checks for uploaded files (SEC-04), no external libmagic dependency."""


def bytes_match_upload_extension(suffix: str, head: bytes) -> bool:
    """Return True if leading bytes match the declared extension (.pdf / .docx)."""
    if suffix == ".pdf":
        return head.startswith(b"%PDF")
    if suffix == ".docx":
        return len(head) >= 4 and head[:4] == b"PK\x03\x04"
    return False
