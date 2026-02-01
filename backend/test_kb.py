"""Test knowledge base retrieval (stage 2.4). Run from backend/ with venv activated.

Requires KNOWLEDGE_BASE_TYPE=thinkdoc and THINKDOC_API_KEY、THINKDOC_KB_IDS in .env.
If KNOWLEDGE_BASE_TYPE is none or unset, search() returns [] and this script reports 0 chunks.
"""
import os

# Ensure backend/ is cwd so app.config loads .env from here
_backend = os.path.dirname(os.path.abspath(__file__))
os.chdir(_backend)

from app import config
from app.knowledge_base import search


def main():
    print("Knowledge base type:", config.KNOWLEDGE_BASE_TYPE)
    if config.KNOWLEDGE_BASE_TYPE == "none":
        print("KNOWLEDGE_BASE_TYPE is none; set THINKDOC_API_KEY and THINKDOC_KB_IDS (and optionally KNOWLEDGE_BASE_TYPE=thinkdoc) to test ThinkDoc.")
        return
    print("Query: BIM应用, top_k=5")
    chunks = search("BIM应用", top_k=5)
    print("Chunks returned:", len(chunks))
    if chunks:
        for i, c in enumerate(chunks[:3]):
            preview = (c[:120] + "…") if len(c) > 120 else c
            print(f"  [{i+1}] {preview}")
        if len(chunks) > 3:
            print(f"  ... and {len(chunks) - 3} more")
        print("OK")
    else:
        print("No chunks (check THINKDOC_API_KEY, THINKDOC_KB_IDS and ThinkDoc service).")


if __name__ == "__main__":
    main()
