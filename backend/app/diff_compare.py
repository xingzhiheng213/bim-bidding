"""Character-level diff: produce structured list of add/del segments for compare API."""
import difflib

from app.schemas.compare import DiffItem


def compute_diff(original: str, modified: str) -> list[DiffItem]:
    """Compute character-level diff with full segment stream (equal/del/add).

    Returns a list of DiffItem in document order including "equal" (unchanged)
    segments, so the frontend can render one coherent text with only changed
    parts highlighted (e.g. only "我们" in red, not a pile of red "我们").
    """
    matcher = difflib.SequenceMatcher(None, original, modified)
    result: list[DiffItem] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            text = original[i1:i2]
            if text:
                result.append(DiffItem(type="equal", text=text))
        elif tag == "delete":
            text = original[i1:i2]
            if text:
                result.append(DiffItem(type="del", text=text))
        elif tag == "insert":
            text = modified[j1:j2]
            if text:
                result.append(DiffItem(type="add", text=text))
        elif tag == "replace":
            del_text = original[i1:i2]
            add_text = modified[j1:j2]
            if del_text:
                result.append(DiffItem(type="del", text=del_text))
            if add_text:
                result.append(DiffItem(type="add", text=add_text))
    return result
