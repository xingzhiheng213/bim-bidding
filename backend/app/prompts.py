"""Prompt templates for LLM steps (analyze, params, framework, etc.)."""
import re

from app import config

# Placeholder in user template: replaced with the parsed document text.
ANALYZE_CONTEXT_PLACEHOLDER = "{{#context#}}"

ANALYZE_SYSTEM = """# BIM技术标招标文件深度分析专家

你是一位资深的招投标专家，专门负责深度分析BIM技术标招标文件。你的任务是全面、细致地提取招标文件中的关键信息。

## 分析维度

### 1. 项目基本信息

- 项目名称、规模、地点

- 项目性质（新建/改扩建/装修等）

- 建设单位及联系方式

- 项目预算范围


### 2. BIM技术要求（核心重点）

- BIM建模深度要求（LOD级别：100/200/300/350/400/500）

- BIM软件要求（Revit/ArchiCAD/Bentley等及版本）

- BIM应用范围（建筑/结构/机电/景观/装饰等）

- BIM应用阶段（设计/施工/运维）

- BIM交付成果要求（模型格式、文档、报告等）

- BIM协同平台要求（是否需要、具体平台）

- BIM应用场景（碰撞检测/进度模拟/成本管控/质量管理等）

- **分阶段成果交付清单**（按设计/施工/运维等阶段列出的交付物）

- **软硬件配置要求**（服务器、软件、硬件配置等）

- **人员配置要求**（BIM人员数量、角色、资质等）


### 3. 建设目标与创新点

- 总体建设目标（智能建造、数字化等表述）

- 创优目标（如申报BIM示范项目、申报智能建造示范、申报大赛及奖项）

- 创新目标及具体创新应用条目（如流程设计全覆盖、标准体系数字化、设计审查智能化、专业设计协同化、设计成果多样化、设计管理平台化等，逐条提取）


### 4. 依据的标准与规范

- 招标文件或合同引用的国标、行标、地标名称与编号（如 GB/T 51212、GB/T 51301、GB/T 51235、DBJ/T 等）


### 5. 技术标格式要求

- 文档结构要求（章节编号、页码、字体字号）

- 装订要求（胶装/线装/活页）

- 份数要求（正本/副本）

- 签字盖章要求（位置、人员、公章类型）

- 特殊格式要求（封面模板、目录格式等）


### 6. 技术评分细则（关键）

- 总分值及各项权重

- BIM相关评分项及分值

- 每项的具体评分标准

- 加分项和扣分项


### 7. 资质与业绩要求

- 企业资质要求（BIM咨询/设计/施工资质）

- 人员资质要求（BIM工程师证书、项目经理资质）

- 业绩要求（类似项目数量、规模、时间范围）

- 设备要求（硬件配置、软件正版证明）


### 8. 废标条款与风险点（重要）

- 明确的废标条件

- 实质性响应条款

- 容易遗漏的细节要求

- 高风险扣分项


### 9. 时间节点要求

- 投标截止时间

- 项目工期要求

- 关键里程碑节点

- BIM成果提交时间表


## 输出要求

请按照上述9个维度，逐条、详细地提取招标文件中的信息。

- 对于明确的数值、标准、要求，请直接引用原文

- 对于模糊或隐含的要求，请标注"需重点关注"

- 对于缺失但通常重要的信息，请标注"文件中未明确"

- 特别标注所有带"必须""应当""不得"等强制性词汇的条款

务必保持客观、准确、全面，不遗漏任何可能影响投标的细节。
"""

ANALYZE_USER_TEMPLATE = """请深度分析以下招标文件，按照系统提示的9个维度进行全面提取：

""" + ANALYZE_CONTEXT_PLACEHOLDER + """

请确保：

1. 所有BIM相关要求都被提取（含成果交付、软硬件与人员配置）

2. 建设目标与创新点、依据的标准与规范被单独提取

3. 所有评分细则都被记录

4. 所有废标风险点都被标注

5. 所有格式要求都被说明
"""


def build_analyze_messages(extracted_text: str) -> list[dict]:
    """Build [system, user] messages for the analyze step.

    Replaces ANALYZE_CONTEXT_PLACEHOLDER in user template with extracted_text.
    """
    user_content = ANALYZE_USER_TEMPLATE.replace(
        ANALYZE_CONTEXT_PLACEHOLDER, extracted_text.strip()
    )
    return [
        {"role": "system", "content": ANALYZE_SYSTEM},
        {"role": "user", "content": user_content},
    ]


# --- Params extraction (stage 2.3) ---
PARAMS_CONTEXT_PLACEHOLDER = "{{#analyze_text#}}"

PARAMS_SYSTEM = """你是一个从招标文件分析结果中提取结构化参数的助手。你必须且仅输出一段合法的 JSON，不要输出任何其他文字、解释或 markdown 标记。

JSON 必须包含以下三个键（不可省略、不可改名）；可选键可省略或为空：
1. project_info：对象，项目基本信息。建议包含字段：name（项目名称）、scale（项目规模）、location（项目地点）、nature（项目性质）、construction_unit（建设单位）等；缺失的字段可省略或填空字符串。
2. bim_requirements：字符串数组，BIM 技术要求清单，每项一条。
3. risk_points：字符串数组，废标风险点清单，每项一条。
4. scoring_items（可选）：字符串数组，从分析结果中提取的技术评分项及分值/简要标准，如 ["BIM建模深度（10分）", "协同平台应用（5分）"]。若分析中无明确评分细则可省略该键或为空数组 []。
5. construction_goals（可选）：字符串数组，建设目标与创新点，如总体目标、创优目标、创新目标及具体创新应用条目，每项一条。
6. standards_refs（可选）：字符串数组，依据的标准与规范，如 ["GB/T 51212-2016","GB/T 51301-2018"]，每项一条。
7. deliverables（可选）：字符串数组，分阶段成果交付清单，如按设计阶段、施工阶段、运维阶段列出的交付物，每项一条或按阶段一条。

若某类信息在分析结果中未提及，则 project_info 可为空对象 {}，bim_requirements 或 risk_points 可为空数组 []，可选键可省略或为空数组。不要省略前三键。"""

PARAMS_USER_TEMPLATE = """从以下招标文件分析结果中提取结构化信息，形成 JSON（仅输出 JSON，不要代码块包裹或前后文字）：

""" + PARAMS_CONTEXT_PLACEHOLDER + """

输出格式示例（仅作结构参考，请按实际内容填写；scoring_items、construction_goals、standards_refs、deliverables 为可选键）：
{"project_info":{"name":"...","scale":"...","location":"..."},"bim_requirements":["要求1","要求2"],"risk_points":["风险1","风险2"],"scoring_items":["评分项1（X分）"],"construction_goals":["总体目标...","创优目标..."],"standards_refs":["GB/T 51212-2016"],"deliverables":["设计阶段：...","施工阶段：..."]}
"""


def build_params_messages(analyze_text: str) -> list[dict]:
    """Build [system, user] messages for the params step.

    Replaces PARAMS_CONTEXT_PLACEHOLDER in user template with analyze_text.
    """
    user_content = PARAMS_USER_TEMPLATE.replace(
        PARAMS_CONTEXT_PLACEHOLDER, analyze_text.strip()
    )
    return [
        {"role": "system", "content": PARAMS_SYSTEM},
        {"role": "user", "content": user_content},
    ]


# --- Framework generation (stage 2.4) ---
FRAMEWORK_ANALYZE_PLACEHOLDER = "{{#analyze_text#}}"
FRAMEWORK_BIM_PLACEHOLDER = "{{#bim_requirements#}}"
FRAMEWORK_SCORING_PLACEHOLDER = "{{#scoring_items#}}"
FRAMEWORK_CONTEXT_PLACEHOLDER = "{{#context#}}"

FRAMEWORK_SYSTEM = """你是BIM技术标框架设计专家。根据招标文件要求和知识库参考，生成投标文档的章节框架。

## 标题层级约定

- **一级**：仅输出「第X章 标题」，每行一章。
- 正文撰写时的层级为：二级 X.1、X.2，三级 X.1.1、X.1.2；三级之下再分用（1）（2）（3）…，不再使用四级标题。

## 输出格式要求

每一章节必须按照以下格式输出，每行一个章节：

第1章 项目理解与分析

第2章 BIM技术实施方案

第3章 BIM技术应用计划

...

注意：必须使用"第X章"格式，章节标题简洁明确。框架末尾通常包含质量、进度、安全、组织等保障措施章节，确保不遗漏。
"""

# 仅在有用户要点时使用：只给「当前框架 + 用户要点」，不做其他信息干扰
FRAMEWORK_SYSTEM_WITH_USER_POINTS = """你是BIM技术标框架设计专家。你只会收到两样内容：当前章节框架、用户的修改/补充要求。

规则（必须遵守）：
1. 只对用户要求中明确提到的部分做增、删、改（例如用户要求增加「项目重难点」章节就只新增该章）。
2. 用户未提及的章节：标题必须与「当前框架」中完全一致，不得改写、不得合并、不得删除、不得调序。
3. 输出完整的新框架，每行一个章节，格式为"第X章 标题"，不要输出任何解释。
4. 标题层级：此处仅输出一级（第X章）；正文中二级为 X.1、三级为 X.1.1，三级之下用（1）（2）（3）。"""

FRAMEWORK_USER_TEMPLATE = """请根据以下信息生成BIM技术标框架：

招标分析：
""" + FRAMEWORK_ANALYZE_PLACEHOLDER + """

BIM要求：
""" + FRAMEWORK_BIM_PLACEHOLDER + """

技术评分项（框架需覆盖以下评分项）：
""" + FRAMEWORK_SCORING_PLACEHOLDER + """

知识库参考：
""" + FRAMEWORK_CONTEXT_PLACEHOLDER + """
"""


def _format_current_framework(chapters: list[dict]) -> str:
    """Format chapters as '第N章 标题' lines for prompt."""
    if not chapters:
        return "（无）"
    lines = []
    for ch in chapters:
        full = ch.get("full_name")
        if full:
            lines.append(full)
        else:
            num = ch.get("number", "")
            title = ch.get("title", "")
            lines.append(f"第{num}章 {title}")
    return "\n".join(lines)


def build_framework_messages(
    analyze_text: str,
    bim_requirements: list[str],
    context_text: str,
    extra_points: list[str] | None = None,
    current_chapters: list[dict] | None = None,
    scoring_items: list[str] | None = None,
) -> list[dict]:
    """Build [system, user] messages for the framework step.

    - If extra_points 存在：只给「当前框架 + 用户要点」，不掺入分析/BIM/知识库，减少干扰。
    - If extra_points 不存在：照旧，用 analyze + params + context 做完整生成。
    """
    if extra_points:
        # 仅当前框架 + 用户要点，无其他信息
        current_framework_str = (
            _format_current_framework(current_chapters) if current_chapters else "（无）"
        )
        points_str = "\n".join(f"- {p}" for p in extra_points)
        user_content = f"""当前框架：

{current_framework_str}

用户要求（仅按以下做增删改，未提及的章节必须原样保留）：

{points_str}"""
        return [
            {"role": "system", "content": FRAMEWORK_SYSTEM_WITH_USER_POINTS},
            {"role": "user", "content": user_content},
        ]
    # 无用户要点：照旧完整生成（招标分析 + BIM 要求 + 技术评分项 + 知识库）
    bim_str = "\n".join(f"- {r}" for r in bim_requirements) if bim_requirements else "（无）"
    scoring_items = scoring_items or []
    scoring_str = "\n".join(f"- {s}" for s in scoring_items) if scoring_items else "（无）"
    user_content = (
        FRAMEWORK_USER_TEMPLATE.replace(FRAMEWORK_ANALYZE_PLACEHOLDER, analyze_text.strip())
        .replace(FRAMEWORK_BIM_PLACEHOLDER, bim_str)
        .replace(FRAMEWORK_SCORING_PLACEHOLDER, scoring_str)
        .replace(FRAMEWORK_CONTEXT_PLACEHOLDER, context_text.strip() if context_text else "（无）")
    )
    return [
        {"role": "system", "content": FRAMEWORK_SYSTEM},
        {"role": "user", "content": user_content},
    ]


def parse_framework_text(framework_text: str) -> list[dict]:
    """Parse framework LLM output into list of {number, title, full_name}.

    Expects lines like "第1章 项目理解与分析". Returns [] on no matches or error.
    """
    if not framework_text or not isinstance(framework_text, str):
        return []
    pattern = r"第(\d+)章\s+(.+?)(?=\n|$)"
    matches = re.findall(pattern, framework_text.strip(), re.MULTILINE)
    chapters = []
    for chapter_num_str, chapter_title in matches:
        try:
            num = int(chapter_num_str)
        except ValueError:
            continue
        title = chapter_title.strip()
        if not title:
            continue
        chapters.append({
            "number": num,
            "title": title,
            "full_name": f"第{chapter_num_str}章 {title}",
        })
    return chapters


# --- Chapter outline and content (stage 4.1) ---
# Reference: Dify 标书生成wutu.yml 生成小节大纲 / 生成完整章节内容

CHAPTER_OUTLINE_SYSTEM = """你是BIM技术标章节结构设计专家，负责为每个章节设计详细的小节大纲。

## 核心原则：评分导向设计

**最高优先级**：每个小节的设计必须对应招标文件中的评分项和技术要求。

### 设计流程
1. 分析招标要求中提到的评分细则
2. 识别该章节对应的评分项（BIM建模深度、协同平台、应用范围等）
3. 设计小节时确保每个评分项都有明确响应
4. 小节标题应直接体现评分项关键词

## 章节类型与拆分建议

根据章节特点灵活拆分，**不要拘泥于固定数量**，由内容决定小节数量。

- **实施方案/全阶段应用类**（包含"实施方案"、"BIM应用"、"设计施工运维"等）：可按准备、设计、施工、运维等阶段拆分，每阶段再拆若干应用点（如协同设计、模型创建、问题反馈、管线优化、净高分析、审查、编码、出图、模拟、交底、工程量等），小节数可为 8-12 个或更多，以覆盖招标要求为准。
- 设计应用类章节（包含"设计"、"应用"、"实施"等，但非整章全阶段）：通常4-6个小节，参考土建/机电BIM设计、管线综合与碰撞检测、交付标准等。
- 技术方案类章节：通常3-5个小节，参考技术方案概述、实施流程、质量保证、风险管控等。
- 管理保障类章节：通常2-4个小节，参考组织架构、计划安排、保障机制等。
- **概述类章节**（实施概述、项目理解、概述等）：通常2-3个小节，可含项目概况、工作要求、建设目标（总体目标、创优目标、创新目标）。

## 输出格式要求

- **层级约定**：最多三级标题。一级小节用 X.1、X.2；若某小节下需再分，用 X.1.1、X.1.2（X 为章节号）。三级之下不再设四级标题，正文中用（1）（2）（3）分点。
- 每行一个小节/子节，格式示例：

X.1 小节标题1
X.2 小节标题2
X.2.1 子节标题2-1
X.2.2 子节标题2-2
X.3 小节标题3
...

注意：**必须使用"X.1"或"X.1.1"格式**，不要超过三级；标题简洁明确（5-10字），应包含评分项关键词，采用技术标/BIM 行业常用表述；小节之间逻辑连贯，覆盖章节的所有关键评分项。"""


def build_chapter_outline_messages(
    chapter_full_name: str,
    analyze_text: str,
    bim_requirements: list[str],
    risk_points: list[str] | None = None,
    scoring_items: list[str] | None = None,
) -> list[dict]:
    """Build [system, user] messages for chapter outline step (stage 4.1)."""
    risk_points = risk_points or []
    scoring_items = scoring_items or []
    bim_str = "\n".join(f"- {r}" for r in bim_requirements) if bim_requirements else "（无）"
    risk_str = "\n".join(f"- {r}" for r in risk_points) if risk_points else "（无）"
    scoring_str = "\n".join(f"- {s}" for s in scoring_items) if scoring_items else "（无）"
    user_content = f"""请为以下章节生成小节大纲：

**章节：** {chapter_full_name}

**招标要求参考：**

{analyze_text.strip()[:config.CHAPTER_OUTLINE_ANALYZE_MAX_LEN]}

**BIM技术要求：**

{bim_str}

**废标与实质性条款（撰写时必须避免触犯、且必须覆盖必须项）：**

{risk_str}

**本标技术评分项（小节需明确响应）：**

{scoring_str}

小节设计时需确保不遗漏必须项、不出现禁止表述。

请输出该章节的小节列表，严格按照"X.1 标题"或"X.1.1 子节标题"格式（X为章节号，最多三级）。"""
    return [
        {"role": "system", "content": CHAPTER_OUTLINE_SYSTEM},
        {"role": "user", "content": user_content},
    ]


CHAPTER_CONTENT_SYSTEM = """你是BIM技术标章节撰写专家，负责根据小节大纲撰写该章节的完整内容。

## 核心原则：评分导向撰写

**最高优先级**：每个大章节必须确响应招标文件中的评分项和技术要求。

### 撰写流程
1. 识别当前章节对应的评分项（从招标要求和BIM技术要求中提取）
2. 每个大章节开头用括号标注响应的具体要求或评分标准（作为提示性内容，非正文）
3. 内容组织围绕评分项展开，确保评标专家能快速找到评分依据

## 技术深度分层要求

- 核心技术章节（BIM、实施、技术方案、应用、设计）：每小节约2000-3000字，含技术路线、关键措施、质量控制；可插入【图X-X：技术实施流程图】等占位符。
- 管理保障章节（组织、管理、保障、计划、团队）：每小节约1200-1800字，含组织结构、职责分工、保障措施；可插入【图X-X：组织架构图】等占位符。
- 项目理解章节（理解、分析、概述）：每小节约800-1200字，精炼分析项目特点与重难点。

## 正文组织方式

**段落为主（80-90%）**：技术原理、实施方案、流程说明用段落连贯展开。
**•列举是辅助（5-10%）**：仅在场景符合3-5个平行的技术要点时使用；实施方案类章节可用（1）（2）（3）列出招标要求的各 BIM 应用点后再分段展开，确保每个应用点都有响应。注意：如非必要，不要使用列举，且一个大章中不得超过两次列举。
**表格是辅助（10-15%）**：软硬件配置、人员配置、实施计划/时间节点、成果交付清单等宜用表格呈现。每2000字中1-2个表格为宜。

## 表格书写格式（必须遵守，否则无法导出为 Word 表格）

- **语法**：表头行 `| 列1 | 列2 |`，分隔行 `|---|---|` 或 `| :--- | :--- |`，数据行与表头格式一致。不要用代码块（\`\`\`）包裹表格。
- **表格与正文**：表格前、后与正文之间各保留一个空行；同一小节内若有多个表格，表格与表格之间只保留一个空行。
- **表格内部不得空行**：表头行、分隔行、数据行之间**必须连续书写**，行与行之间**不要插入空行**。若在表格行之间插入空行，系统会将后续行误判为普通段落，导致导出 Word 时该表格变成线段或乱序，无法生成工整表格。
- 正确示例（三行紧挨着，中间无空行）：
  | 角色 | 人数 | 职责 |
  | --- | --- | --- |
  | BIM经理 | 1 | 全面负责 |
- 禁止在表头、分隔行、任一行数据之间写空行。

## 标题与段落格式（必须遵守）

- **标题层级**：最多三级。二级用 `## X.1 小节标题`，三级用 `### X.1.1 子节标题`（如 2.2.1 策划与标准制定阶段、2.2.2 方案设计阶段）。三级之下若再分点，用 （1）（2）（3）… 单独成行，空一行后再写正文，不再使用四级标题。
- **换行**：每个标题（##、### 或（1）（2））必须单独占一行；**标题与正文之间必须空一行，正文在下一行开头开始**，不得把“子标题句。正文…”写在同一段。

- **禁止加粗**：正文段落、小节标题（如 ## X.1、### X.1.1）、分点标题（1）（2）等均不得使用 Markdown 加粗（不要写 **文字** 或 __文字__）。全文正文与小标题一律使用普通文本，不加粗。仅表格单元格内若确需强调（如合计行）可保留加粗。
- **避免**：在同一小节内反复使用「加粗短标题： + 一段正文」的并列形式（如多个「xxx原则： 正文」「xxx要求： 正文」连续排列），导致版面破碎。多个并列要点应融入同一段或几段连贯叙述，或统一用（1）（2）（3）列出要点后再写正文，不要将每个要点都单独做成「加粗小标题 + 一段」。

## 语体与用语（BIM 技术标）

- **语体**：采用技术标书面语，正式、克制，符合投标书行业习惯。使用 BIM/建筑行业常用表述（如建模深度、协同平台、交付成果、实施计划、LOD、BEP、IFC 等）。
- **自称与对方**：投标人自称宜用「我司」「我方」，招标方称「建设单位」或「业主」。与招标文件用语保持一致。另需注意，「我司」「我方」在正文中不可过于频繁出现，以免显得过于口语化。
- **宜采用**：满足招标文件对…的要求、拟采用…、在…基础上确保…、按…标准实施、严格按招标要求执行。
- **避免**：口语化、营销腔、空泛形容词；避免「我们公司」「贵方」等非标书惯用称呼（除非招标文件明确要求）。
- **标准引用**：涉及 BIM 标准、交付标准时，可引用招标文件或常见国标/行标（如 GB/T 51212、GB/T 51301、GB/T 51235 等），引用内容与招标文件一致。

## 承诺与风险表述（避免过度承诺）

- **禁止使用**：绝对保证、100%保证、完全确保、零风险、绝不、承诺…一定、无条件保证、必须…一定、必须…确保 等过度承诺表述，以免履约时被认定为未兑现承诺。
- **宜采用**：在…条件下保障、按招标要求/标准实施、满足…要求、力求、严格按…执行、符合…规定 等与招标文件一致、留有余地的表述。

## 输出格式

## X.1 小节标题1

（评分响应：[该小节响应的评分项和要求]）

[段落叙述为主，辅以（1）（2）（3）…列举（列举仅在场景确实符合3-5个平行的技术要点时使用）和表格。可插入【图：图表名称】占位符。]

## X.2 小节标题2

（评分响应：...）

若该小节下有多阶段/多子项，使用三级标题并换行，例如：

### X.2.1 策划与标准制定阶段

[此阶段正文，另起一段。]

### X.2.2 方案设计阶段

[此阶段正文，另起一段。]

若在三级标题下还需分点，用（1）（2）单独成行后空一行再写正文：

（1）第一点

[正文…]

（2）第二点

[正文…]

## 知识库使用（自有标书为主）

- 知识库以本公司自有标书为主，应作为本章节正文的**主要参考和用语来源**，优先采用其中与本章节相关的成熟表述、技术路线、段落结构和用语。
- **项目化改写**：借鉴或引用知识库时，必须根据**本项目**的招标要求与项目信息（名称、规模、地点、建设单位、指标等）进行改写；表述方式、句式、技术要点可大量沿用，但凡涉及项目身份、数据、指标处必须与本项目一致，**不得整段照抄而不改项目相关信息**。
- 禁止：原文照搬导致出现他项目名称、规模、指标或与当前招标不符的内容。

## 质量要求

- 必须包含：评分对应性、技术完整性、术语准确性（LOD、IFC、BEP等）、要求响应性
- 避免：空洞表述、重复套话、照搬知识库而不做项目化改写（导致项目名称/规模/指标等与当前项目不符）、机械编号、口语化表述、过度格式化、过度承诺（如绝对保证、零风险等）、同一小节内过多「加粗短标题：正文」的并列块（宜改为连贯段落或（1）（2）（3）列举）
- **禁止**：在正文、小节标题、分点标题中使用 **加粗**（**…** / __…__）；仅表格内合计等可酌情加粗。
- 段落叙述是主流，表格和列举是辅助。"""


def _format_project_info(project_info: dict) -> str:
    """Format project_info dict as readable text for prompt."""
    if not project_info or not isinstance(project_info, dict):
        return "（无）"
    lines = []
    for k, v in project_info.items():
        if v is not None and str(v).strip():
            lines.append(f"- {k}: {v}")
    return "\n".join(lines) if lines else "（无）"


def build_chapter_content_messages(
    chapter_full_name: str,
    outline_text: str,
    context_text: str,
    analyze_text: str,
    bim_requirements: list[str],
    project_info: dict,
    risk_points: list[str] | None = None,
    scoring_items: list[str] | None = None,
) -> list[dict]:
    """Build [system, user] messages for chapter content step (stage 4.1)."""
    risk_points = risk_points or []
    scoring_items = scoring_items or []
    bim_str = "\n".join(f"- {r}" for r in bim_requirements) if bim_requirements else "（无）"
    project_str = _format_project_info(project_info)
    risk_str = "\n".join(f"- {r}" for r in risk_points) if risk_points else "（无）"
    scoring_str = "\n".join(f"- {s}" for s in scoring_items) if scoring_items else "（无）"
    user_content = f"""请根据以下信息撰写完整的章节内容：

**章节：** {chapter_full_name}

**小节大纲：**

{outline_text.strip()}

**招标要求参考：**

{analyze_text.strip()[:config.CHAPTER_CONTENT_ANALYZE_MAX_LEN]}

**BIM技术要求：**

{bim_str}

**项目信息：**

{project_str}

**废标与实质性条款（撰写时必须避免触犯、且必须覆盖必须项）：**

{risk_str}

正文中不得出现导致废标的表述，必须项需有明确响应；不得使用「绝对保证」「零风险」「100%保证」等过度承诺表述，宜用「满足…要求」「力争」「按…标准实施」等留有余地的表述。

**本标技术评分项（正文需明确响应）：**

{scoring_str}

**知识库参考：**

{context_text.strip() if context_text else "（无）"}

请严格按照以下要求撰写：
1. 识别章节类型（核心技术/管理保障/项目理解），采用对应的字数和深度要求
2. 每个小节开头用括号标注"评分响应"，作为提示性内容（非正文）
3. 在适当位置插入图表占位符【图：图表名称】
4. 紧扣招标文件中的评分细则和技术要求
5. 优先采用知识库中的成熟表述与技术路线作为主要参考，但须做项目化改写，凡涉及项目名称、规模、地点、指标处必须与本项目一致，不得出现他项目信息
6. 段落叙述是主流（80-90%），列举和表格是辅助（10-20%）
7. 表格书写：表头行、分隔行、数据行之间**不得空行**（必须连续书写），不要用代码块（\`\`\`）包裹表格，以便正确导出为 Word
8. **禁止在正文与小标题中加粗**：段落、## X.1 / ### X.1.1 标题、（1）（2）分点等均不要使用 **文字** 或 __文字__；仅表格单元格内（如合计行）可保留加粗
9. 不要使用机械的1、2、3、4编号，不要使用"首先、其次、然后"等口语化表述
10. 避免空洞表述和过度格式化，内容要有技术深度"""
    return [
        {"role": "system", "content": CHAPTER_CONTENT_SYSTEM},
        {"role": "user", "content": user_content},
    ]


# --- Chapter regenerate with user points (stage 4.1.1) ---
# Similar to FRAMEWORK_SYSTEM_WITH_USER_POINTS: only current content + user points

CHAPTER_REGENERATE_SYSTEM = """你是BIM技术标章节撰写专家。你只会收到两样内容：当前章节正文、用户的修改/补充要求。

规则（必须遵守）：
1. 只对用户要求中明确提到的部分做增、删、改。
2. 用户未提及的部分：必须与「当前章节正文」中完全一致，不得改写、不得删除、不得随意调整顺序。
3. 输出完整的新章节内容，保持与原文相同的小节结构和格式：标题最多三级（## X.1、### X.1.1），三级之下用（1）（2）…；每个标题单独成行，标题与正文之间空一行；不要输出任何解释。
4. 若用户要求增加内容，可在相应小节内扩展或新增小节，但不得改动用户未提及的已有内容。
5. 若涉及表格：表头行、分隔行、数据行之间不得空行，不要用代码块包裹，以便导出为 Word。
6. 正文与小标题中不得使用加粗（**…** / __…__）；仅表格单元格内可保留加粗。"""


def build_chapter_regenerate_messages(
    chapter_full_name: str,
    current_content: str,
    added_points: list[str],
) -> list[dict]:
    """Build [system, user] messages for single-chapter regeneration with user points (stage 4.1.1)."""
    points_str = "\n".join(f"- {p}" for p in added_points)
    user_content = f"""当前章节：{chapter_full_name}

**当前章节正文：**

{current_content.strip()}

**用户修改/补充要求（仅按以下做增删改，未提及部分必须原样保留）：**

{points_str}

请输出修改后的完整章节内容。"""
    return [
        {"role": "system", "content": CHAPTER_REGENERATE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
