"""本地快速测：代码块里的表格 → Word 真实表格。

在 backend/ 目录下：

  python scripts/run_table_export_demo.py

输出：backend/test_table_output.docx
"""
import os
import sys

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_ROOT)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.export_docx import markdown_to_docx


def main() -> None:
    md = """## 2.2 全过程 BIM 应用规划

表2-1 各阶段BIM主要交付成果清单

```
| 阶段 | 交付成果名称 | 内容描述 | 格式 |
| :--- | :--- | :--- | :--- |
| 策划与标准 | 项目 BIM实施标准(BEP) | 涵盖建模、协同、交付、管理的全套标准 | PDF/DOCX |
| | BIM 协同平台部署报告 | 平台架构、权限设置、访问方式说明 | PDF |
| 方案设计 | 概念体量模型 | 场地、建筑群整体体量模型 | RVT/NWC |
```

以上为示例表格。
"""

    doc = markdown_to_docx(md)
    out_path = os.path.join(_BACKEND_ROOT, "test_table_output.docx")
    doc.save(out_path)
    print(f"已保存: {out_path}，请用 Word 打开查看：表标题应单独成段，下面为工整表格。")
    print(f"文档中表格数量: {len(doc.tables)}")


if __name__ == "__main__":
    main()
