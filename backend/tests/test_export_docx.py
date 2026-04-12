"""Test export_docx.markdown_to_docx (stage 4.3)."""
from app.export_docx import markdown_to_docx


def test_markdown_to_docx_basic():
    """Test basic markdown conversion: headings, lists, paragraphs."""
    md = """# 标书完整文档

## 项目信息

- 项目名称: 示例项目
- 项目规模: 大型

---

## 第1章 概述

普通段落内容。

### 1.1 小节

- 列表项1
- 列表项2
"""
    doc = markdown_to_docx(md)
    assert doc is not None
    # Should have multiple paragraphs/headings
    assert len(doc.paragraphs) >= 5
    print("markdown_to_docx: OK")


if __name__ == "__main__":
    test_markdown_to_docx_basic()
    print("All tests passed.")
