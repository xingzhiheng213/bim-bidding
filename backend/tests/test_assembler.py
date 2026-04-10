"""Test document assembler (stage 4.2).

自动化测试见 test_project_info_to_markdown；可选在 backend/ 下运行联调：

  python tests/test_assembler.py [task_id]
"""
import os
import sys

# tests/ 的父目录即 backend/，保证与仓库内其它模块一致
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_ROOT)

from app.assembler import assemble_full_markdown, project_info_to_markdown
from app.database import SessionLocal


def test_project_info_to_markdown():
    """Test project_info_to_markdown with sample data."""
    # Normal case
    info = {"name": "测试项目", "scale": "中型", "location": "北京"}
    md = project_info_to_markdown(info)
    assert "- 项目名称: 测试项目" in md
    assert "- 项目规模: 中型" in md
    assert "- 项目地点: 北京" in md

    # Empty
    assert project_info_to_markdown({}) == ""
    assert project_info_to_markdown(None) == ""

    # Unknown key kept as-is
    md2 = project_info_to_markdown({"custom_key": "value"})
    assert "- custom_key: value" in md2

    print("project_info_to_markdown: OK")


def main():
    test_project_info_to_markdown()

    task_id_str = sys.argv[1] if len(sys.argv) > 1 else None
    if task_id_str:
        try:
            task_id = int(task_id_str)
            db = SessionLocal()
            try:
                full_md = assemble_full_markdown(task_id, db)
                print(f"assemble_full_markdown(task_id={task_id}): OK, length={len(full_md)}")
                if full_md:
                    print("Preview (first 300 chars):")
                    print(full_md[:300] + ("..." if len(full_md) > 300 else ""))
            finally:
                db.close()
        except ValueError as e:
            print(f"assemble_full_markdown: {e}")
            print("Ensure task has completed params, framework, and chapters steps.")
    else:
        print("To verify assemble_full_markdown, run: python tests/test_assembler.py <task_id>")


if __name__ == "__main__":
    main()
