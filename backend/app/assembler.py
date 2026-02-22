"""Document assembly: project_info + chapters + risk_points -> full Markdown (stage 4.2).

Reference: Dify 标书生成wutu.yml 文档聚合 template.
"""
import json

from sqlalchemy.orm import Session

from app.models import TaskStep

PROJECT_INFO_KEY_MAP = {
    "name": "项目名称",
    "scale": "项目规模",
    "location": "项目地点",
    "nature": "项目性质",
    "construction_unit": "建设单位",
    "contact": "联系方式",
    "budget_range": "预算范围",
}


def project_info_to_markdown(project_info: dict | None) -> str:
    """Convert project_info dict to readable Markdown list.

    Maps known keys to Chinese labels; unknown keys are kept as-is.
    Returns empty string if project_info is None or empty.
    """
    if not project_info or not isinstance(project_info, dict):
        return ""
    lines = []
    for key, value in project_info.items():
        display_key = PROJECT_INFO_KEY_MAP.get(key, key)
        if value is None:
            val_str = ""
        elif isinstance(value, (dict, list)):
            val_str = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            val_str = str(value).strip()
        lines.append(f"- {display_key}: {val_str}")
    return "\n".join(lines) if lines else ""


def assemble_full_markdown(task_id: int, db: Session) -> str:
    """Assemble full Markdown from params + framework + chapters steps.

    Structure: chapters -> --- -> ## 附录 -> ### 风险点提醒.
    Cover and project info are no longer in body (handled separately in export).

    Args:
        task_id: Task ID.
        db: SQLAlchemy session.
    Returns:
        Full Markdown string.
    Raises:
        ValueError: If any required step is missing or data is invalid.
    """
    params_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "params")
        .first()
    )
    if not params_step or params_step.status != "completed" or not params_step.output_snapshot:
        raise ValueError("请先完成参数提取")

    try:
        params_out = json.loads(params_step.output_snapshot)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("参数步骤输出格式异常")

    project_info = params_out.get("project_info")
    if not isinstance(project_info, dict):
        project_info = {}
    risk_points = params_out.get("risk_points")
    if not isinstance(risk_points, list):
        risk_points = []
    risk_points = [str(r).strip() for r in risk_points if r]

    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step or framework_step.status != "completed" or not framework_step.output_snapshot:
        raise ValueError("请先完成框架并接受框架")

    try:
        fw_out = json.loads(framework_step.output_snapshot)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("框架步骤输出格式异常")

    chapters_list = fw_out.get("chapters")
    if not isinstance(chapters_list, list):
        chapters_list = []
    chapters_list = sorted(chapters_list, key=lambda ch: ch.get("number", 0))

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step or chapters_step.status != "completed" or not chapters_step.output_snapshot:
        raise ValueError("请先完成按章生成")

    try:
        ch_out = json.loads(chapters_step.output_snapshot)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("按章生成步骤输出格式异常")

    chapters_dict = ch_out.get("chapters")
    if not isinstance(chapters_dict, dict):
        chapters_dict = {}

    parts = []

    for ch in chapters_list:
        num = ch.get("number")
        key = str(num) if num is not None else ""
        content = chapters_dict.get(key) if key else None
        if content and isinstance(content, str):
            parts.append(content.strip())
        else:
            title = ch.get("title", "")
            parts.append(f"（第 {num} 章{f' {title}' if title else ''} 内容待生成）")
        parts.append("")
        parts.append("---")
        parts.append("")

    parts.append("## 附录")
    parts.append("")
    parts.append("### 风险点提醒")
    parts.append("")

    if risk_points:
        for r in risk_points:
            parts.append(f"- {r}")
        parts.append("")
    else:
        parts.append("（暂无）")
        parts.append("")

    return "\n".join(parts).rstrip("\n")
