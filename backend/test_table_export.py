"""本地快速测：代码块里的表格 → Word 真实表格。

运行：在 backend 目录下
  .venv\Scripts\activate
  python test_table_export.py
然后用 Word 打开生成的 test_table_output.docx，确认表标题单独成段、下面为工整表格。
"""
import sys

sys.path.insert(0, ".")

from app.export_docx import markdown_to_docx

# 模拟 LLM 把表格放在代码块里的情况
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
out_path = "test_table_output.docx"
doc.save(out_path)
print(f"已保存: {out_path}，请用 Word 打开查看：表标题应单独成段，下面为工整表格。")
print(f"文档中表格数量: {len(doc.tables)}")
