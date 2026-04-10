"""知识库检索联调脚本（RAGFlow / none）。

在 backend/ 目录下：

  python scripts/run_kb_search_demo.py
  python scripts/run_kb_search_demo.py "BIM施工应用"
  python scripts/run_kb_search_demo.py "BIM施工应用" 10
"""
import os
import sys

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_ROOT)

from app.knowledge_base import search
from app.settings_store import get_kb_config


def main():
    cfg = get_kb_config()
    kb_type = (cfg.get("kb_type") or "none").strip().lower()
    print("Knowledge base type (from 设置页/DB):", kb_type)

    if kb_type == "none" or not kb_type:
        print("当前未启用知识库。请在「设置」页选择 RAGFlow 并配置：")
        print("  - RAGFlow：Base URL、API Key、Dataset IDs（或对应环境变量）")
        return

    query = (sys.argv[1] if len(sys.argv) > 1 else "BIM应用").strip() or "BIM应用"
    try:
        top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    except (ValueError, IndexError):
        top_k = 5

    print(f"Query: {query!r}, top_k={top_k}")
    chunks = search(query, top_k=top_k)
    print("Chunks returned:", len(chunks))
    if chunks:
        for i, c in enumerate(chunks[:3]):
            preview = (c[:120] + "…") if len(c) > 120 else c
            print(f"  [{i+1}] {preview}")
        if len(chunks) > 3:
            print(f"  ... and {len(chunks) - 3} more")
        print("OK — 检索正常，标书生成会使用上述知识库结果。")
    else:
        print("No chunks。请检查：")
        if kb_type == "ragflow":
            print("  - 设置页 RAGFlow Base URL、API Key、Dataset IDs 是否正确")
            print("  - 设置页「检测连通性」是否通过；知识库中是否有相关文档")
        else:
            print("  - RAGFlow 配置与服务是否可用；知识库中是否有相关文档")


if __name__ == "__main__":
    main()
