"""LLM-backed semantic prompt adaptation for PromptProfile (smart generate)."""

from __future__ import annotations

from app.disciplines import DISCIPLINES, list_disciplines
from app.llm import call_llm
from app.llm_resolver import get_llm_for_step
from app.prompts import (
    ANALYZE_CONTEXT_PLACEHOLDER,
    PARAMS_CONTEXT_PLACEHOLDER,
    REVIEW_TYPE_VALUES,
)
from app.semantic_slots import SEMANTIC_SLOTS, get_default_semantic_overrides

REF_MAX_CHARS = 12000
HEAD_CHARS = 5500
TAIL_CHARS = 5500
GEN_TEMPERATURE = 0.35


def _other_disciplines(discipline: str) -> str:
    return "、".join(d for d in DISCIPLINES if d != discipline)


def _prepare_reference(reference: str) -> str:
    r = reference.strip()
    if len(r) <= REF_MAX_CHARS:
        return r
    head = r[:HEAD_CHARS]
    tail = r[-TAIL_CHARS:]
    return (
        head
        + "\n\n…（中间内容已截断，生成时须保持与参考整体结构、格式约束一致；"
        "若不确定请保守沿用参考中的版式与硬性要求。）…\n\n"
        + tail
    )


def _strip_optional_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if len(lines) >= 2 and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _validate_generated(slot_key: str, text: str) -> None:
    if not text or not text.strip():
        raise ValueError("模型返回为空")
    if slot_key == "analyze_user":
        if ANALYZE_CONTEXT_PLACEHOLDER not in text:
            raise ValueError(
                f"生成结果须保留字面占位符 {ANALYZE_CONTEXT_PLACEHOLDER!r}"
                "（解析招标文件正文时替换），请重试或手工补充"
            )
    if slot_key == "params_user":
        if PARAMS_CONTEXT_PLACEHOLDER not in text:
            raise ValueError(
                f"生成结果须保留字面占位符 {PARAMS_CONTEXT_PLACEHOLDER!r}"
                "（注入分析结果正文时替换），请重试或手工补充"
            )
    if slot_key == "review_system":
        # 运行时 build_review_messages 会追加 REVIEW_OUTPUT_FORMAT_SPEC（含 JSON 数组约定），
        # 此处不再强制生成段出现英文字样 JSON，避免模型仅用中文「数组」描述却被误杀。
        present = sum(1 for t in REVIEW_TYPE_VALUES if t in text)
        if present < 3:
            raise ValueError(
                "校审语义须体现多类审查维度（建议保留「废标项」「幻觉」「套路」「建议」等表述，至少命中其中三项），请重试"
            )


def _meta_system_base() -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    return f"""你是「技术标语义提示词」改编专家，服务于招投标文档生成流水线。

## 任务
用户会给出：配置名称、所选「专业」、槽位标识与槽位标题、以及当前系统内置的参考提示词（可能被截断）。请编写**一条完整的、可直接用作该槽位覆盖文案**的提示词正文（中文），用于替换原先偏 BIM/泛技术标的默认表述。

## 专业边界（必须遵守）
- **参与专业全量认知（与系统内置一致，共 {n} 项）**：{all_d}。其中**仅**用户所选「主专业」为当前 Profile 服务对象；上表**其余名称**均为**非主专业**（彼此**无例外**）。改编时须让模型明确：不得以「招标某段提到表中任一非主专业」为由，在主专业交付物中按该非主专业深度撰写专篇；**招标文件分析、参数提取、框架生成**相关槽位须在成稿中**完整按名列举**本表（见各槽附加要求）。
- 当前专业为用户选定的唯一主专业：内容中的角色设定、术语、章节导向、举例须**紧扣该专业**，与配置名称中的场景一致。
- **非主专业「绝对零提及」原则（交付正文，须写入成稿）**：主专业技术标链路产出（分析、参数、框架、章节、校审）中，**除**系统硬性要求的「专业清单 / 主非主边界声明」**固定块**内为履行全表列举义务而**一次性列名**外，**不得**在**任何其它位置**以**任何方式**出现、展开、点名、列举、讨论、复述**任一非主专业**（表中除主专业外**全部**名称**同等适用**，无「BIM 特殊」「独立成章可写」等例外）；**禁止**在正文条款、要点、评分项、目录、括号说明中**以非主专业名为对象**作专篇式论述、响应要点或「故提取…」**合理化**；**禁止**在**边界块之外**再写**任一**非主专业全称或简称作为**响应/分析对象**；若须表达归属，用**「非主专业」「见招标原文」「本技术标不展开」**等**统称**，**不点名**具体非主专业。
- **零越界（硬性，须写入成稿）**：主专业技术标交付物**仅**含主专业本体工程设计/施工/技术内容；**任何**表内非主专业**绝对禁止**以专篇、专章、子方案、长篇「实施/目标/范围/交付」等形式进入主专业分析、参数或框架；**禁止**以「招标独立成章」「与主专业有交叉」「评分/废标需响应」「涉及主专业应用」等理由**合理化越界**。
- **独立成章 / 专册不构成例外**：若招标文件为**任一非主专业**另设独立专章/专册（如独立「BIM」「结构」「暖通」章等），该专业**仍**为非主专业；**禁止**将该章按专篇逻辑纳入本技术标分析或响应；**禁止**输出「（某非主专业，但招标文件将其作为独立章节且涉及…故提取…）」等**括号式越界背书**；若废标/评分**必须**表态，**至多**一条**不展开**的归属说明（**不点名**具体专业名，如「非主专业内容由对应专业标书承担，本技术标不展开」），**不得**展开该专业专项条款。
- **禁止**主动展开、代写或详尽展开非主专业的专篇内容。若招标段落标题/用语指向**任一非主专业**，**不得**在主专业交付正文中**复述该名称并展开**；**禁止**替该非主专业代写技术方案。
- 招标文本可能多专业并存：提示词应要求模型**仅处理与主专业相关的提取/撰写**，不替表中其它专业写全套方案。
- **交付物视角下的专业隔离（禁止「B 段提 A 就写 A」）**：即使招标文件中**非主专业**章节**顺带提及**主专业或其它非主专业，也**不得**据此在主专业技术标链路里展开成**被提及那一专业**才应有的专篇论述；**禁止**在**主专业交付正文**中出现**任一非主专业**专篇式内容（**除**上述「专业清单边界块」外**零点名**）。

## 结构与契约（必须遵守）
- **充分模仿**参考提示词的层级结构（标题、条款编号习惯）、篇幅逻辑、硬性约束（如表格语法、标题层级、禁止事项），不要随意删减关键格式要求。
- analyze_user 槽位：输出中**必须原样保留**字面量 `{{{{#context#}}}}`（含大括号和井号），用于运行时注入招标文件正文；不得改写、拆分或翻译该占位符。
- params_user 槽位：输出中**必须原样保留**字面量 `{{{{#analyze_text#}}}}`（与参考一致），用于运行时注入分析步骤正文；不得改写、拆分或翻译该占位符。
- review_system 槽位：输出为**将与系统追加的「输出格式」段拼接**的校审人设与维度部分；**JSON 数组输出格式由系统在运行时段自动追加**，你只需保留审查维度表述（与参考一致或等价），**至少明确写出四类中的至少三项**（建议沿用「废标项」「幻觉」「套路」「建议」原文）。不要与「仅输出结构化数组、勿输出解释性旁白」相矛盾。

## 输出格式
- **只输出**改编后的提示词正文，不要前言、不要后语、不要用 markdown 代码块包裹（不要 ```）。
"""


def _analyze_slot_independence_block(discipline: str) -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    others = _other_disciplines(discipline)
    return f"""

## 招标文件分析槽位特别要求（成稿中须写成明确、可执行的条款）
- **专业清单须完整落地**：改编后的 analyze system / user 正文中，必须**显式列出**与本系统一致的 {n} 类专业全称：{all_d}；并写明当前**主专业**为「{discipline}」，**非主专业**为除「{discipline}」外的表中其余各项（即：{others}）。不得用「其它专业」等模糊说法替代上述专名列举。**仅此「专业清单/主非主声明」块内**可**一次性列全名**；**除此以外**的分析正文、条款、要点、括号说明中**绝对禁止**出现、点名、复述**任一非主专业**全称/简称作为**分析或响应对象**。
- **各专业原则上相对独立**：分析结果仅用于后续「{discipline}」技术标编制，不得写成多专业混合技术方案或替非主专业代写专篇。
- **非主专业绝对零提及（分析正文）**：除上条**边界块**外，**禁止**在分析输出**任何位置**以**任何理由**提及、展开、讨论表中**除「{discipline}」以外**的任一专业（**无例外**：独立成章、交叉引用、评分、废标、**均不得**在正文点名非主专业）；**禁止**括号式越界（「虽为非主专业，但…故提取…」）；**禁止**将**任一非主专业**专篇级内容写入本分析。
- **独立成章不构成例外**：若招标为**任一非主专业**另设独立专章/专册，**仍不得**按该专业专篇提取要点；**至多**一条不展开、**不点名**的归属说明。
- **禁止「非主专业段落提及主专业或其它专业 → 就展开被提及专业」**：例如招标某章出现多专业接口描述——只要当前主专业为「{discipline}」，分析产出**仍只服务 {discipline}**；**不得**把被提及专业的专篇方案、详细设计论述写进主专业分析；**在正文中不得**再出现**被提及**的非主专业名称。
- **禁止**以「招标里出现了表中任一专业名称」为由，在主专业分析中扩写该名称对应专业的技术标式正文。
"""


def _params_slot_independence_block(discipline: str) -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    others = _other_disciplines(discipline)
    return f"""

## 参数提取槽位特别要求（成稿中须写成明确、可执行的条款）
- **专业清单须完整落地**：改编后的 params system / user 正文中，必须**显式列出** {n} 类专业全称：{all_d}；并写明**主专业**为「{discipline}」，**非主专业**为：{others}。不得用「其它专业」等模糊说法替代专名列举。**仅此边界块内**可列全名；**JSON 各列表字段的字符串值**中**不得**出现**任一非主专业**名称作为**响应要点、专篇对象**（**禁止**点名表中除「{discipline}」外的任何专业）。
- **提取锚定主专业**：从分析结果抽取 JSON 时，key_requirements、scoring_items、construction_goals、deliverables 等**只收录**与**主专业「{discipline}」**技术标响应直接相关的条目；不得因分析文中出现非主专业段落，就把**另一专业**的完整技术方案、专篇要点系统性写入上述数组。
- **非主专业绝对零提及（JSON 值）**：**禁止**在 JSON 各列表中写入**任一非主专业**专篇级要点或方法论（**无**「独立成章」「交叉引用」例外）；**禁止**以「涉及主专业应用」为由混入非主专业内容。
- **禁止「B 段提 A → 参数里给 A 整套要点」**：交叉专业仅在分析中被提及时，参数层**仅可**保留与主专业**接口/边界/必须响应**相关的最小条目（**表述中不点名**非主专业）；**禁止**替非主专业生成可独立成册的要点清单。
- **不得删减或改名**参考中的 JSON 键结构、必选键及「仅输出合法 JSON」等契约；可在 system 中增补专业隔离规则，但不得与 JSON 语法要求冲突。
"""


def _framework_slot_independence_block(discipline: str) -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    others = _other_disciplines(discipline)
    return f"""

## 框架生成槽位特别要求（成稿中须写成明确、可执行的条款）
- **专业清单须完整落地**：改编后的 framework system 正文中，必须**显式列出** {n} 类专业全称：{all_d}；并写明**主专业**为「{discipline}」，**非主专业**为：{others}。**仅此边界块内**可列全名；**目录标题与章节名**中**不得**出现**任一非主专业**名称作为**并列专章/专篇**（**除**边界声明外**零点名**）。
- **目录骨架仅服务主专业技术标**：多级标题框架须围绕「{discipline}」技术标编制组织；**不得**为非主专业单独生成一整套可与主专业并列的专篇目录（如完整「结构专篇」「暖通专册」等），除非招标文件强制且须弱化为与主专业衔接的子项或引用式标题，且**不得**用非主专业目录挤占主专业评分响应结构。
- **禁止**因招标含**任一非主专业**独立专章而生成该专业的并列专章目录；**禁止**其它**任意**非主专业以专章形式涉足本技术标目录树。
- **禁止**因招标某章描述非主专业或交叉提及其它专业，就在框架中展开成**被提及专业**的独立技术标章节体系；交叉内容仅可出现在服务主专业的接口、配合或响应条款下（**标题不点名**非主专业）。
- **充分保留**参考中的版式要求（如逐章输出、编号习惯、禁止输出正文段落等）。
"""


def _slot_discipline_meta_addon(slot_key: str, discipline: str) -> str:
    if slot_key in ("analyze_system", "analyze_user"):
        return _analyze_slot_independence_block(discipline)
    if slot_key in ("params_system", "params_user"):
        return _params_slot_independence_block(discipline)
    if slot_key in ("framework_system", "framework_system_points"):
        return _framework_slot_independence_block(discipline)
    return ""


def _meta_system(slot_key: str, discipline: str) -> str:
    return _meta_system_base() + _slot_discipline_meta_addon(slot_key, discipline)


def _analyze_slots_user_extra(discipline: str) -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    others = _other_disciplines(discipline)
    return f"""【本槽改编须显式写入提示词正文】
- 系统内置专业共 {n} 项，须在成稿中**按名列举**：{all_d}。
- 当前主专业：「{discipline}」。非主专业（不得按专篇展开）：{others}。
- **硬性（绝对零提及）**：分析输出**仅**服务主专业「{discipline}」；**除**本「专业清单/主非主」块外，**禁止**在分析正文**任何位置**以**任何理由**提及、点名、复述**任一非主专业**全称/简称；**禁止**括号式越界说明；**禁止**将表中任一非「{discipline}」专业以专篇形态纳入本分析。
- 招标文件分析：任一段落若涉及非主专业或交叉配合，**不得**引导模型撰写被提及专业的专篇内容；只摘与主专业响应/评分/废标相关的最小信息（**表述不点名**非主专业）；**禁止**在正文中出现「故提取…」类针对非主专业的理由。
"""


def _params_slots_user_extra(discipline: str) -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    others = _other_disciplines(discipline)
    return f"""【本槽改编须显式写入提示词正文】
- 系统内置专业共 {n} 项，须在成稿中**按名列举**：{all_d}。
- 当前主专业：「{discipline}」。非主专业：{others}。
- 参数 JSON 各列表**只收主专业「{discipline}」**响应要点；**除**边界声明块外**禁止**在列表值中**点名**任一非主专业；**禁止**系统性写入**任一非主专业**专篇级要点；**禁止**以独立章节为由混入非主专业方法论。保留 `{{{{#analyze_text#}}}}` 占位符。
"""


def _framework_slots_user_extra(discipline: str) -> str:
    names = list_disciplines()
    all_d = "、".join(names)
    n = len(names)
    others = _other_disciplines(discipline)
    return f"""【本槽改编须显式写入提示词正文】
- 系统内置专业共 {n} 项，须在成稿中**按名列举**：{all_d}。
- 当前主专业：「{discipline}」。非主专业：{others}。
- 框架标题**仅**组织主专业「{discipline}」技术标目录；**除**边界声明块外**禁止**在章节标题中**点名**任一非主专业；**禁止**因招标含**任一非主专业**独立专章而生成并列专篇目录树；**禁止**任何非主专业以专章形式涉足本标书结构；招标交叉提及时不得展开成被提及专业的独立章节体系。
"""


def _user_payload(
    *,
    profile_name: str,
    discipline: str,
    slot_key: str,
    slot_title: str,
    reference: str,
) -> str:
    tail = (
        f"配置名称：{profile_name}\n"
        f"所选专业：{discipline}\n"
        f"其它内置专业（勿主次颠倒、勿代写专篇、交付正文勿点名）：{_other_disciplines(discipline)}\n\n"
        f"槽位 key：{slot_key}\n"
        f"槽位标题：{slot_title}\n\n"
    )
    if slot_key in ("analyze_system", "analyze_user"):
        tail += _analyze_slots_user_extra(discipline).strip() + "\n\n"
    elif slot_key in ("params_system", "params_user"):
        tail += _params_slots_user_extra(discipline).strip() + "\n\n"
    elif slot_key in ("framework_system", "framework_system_points"):
        tail += _framework_slots_user_extra(discipline).strip() + "\n\n"
    tail += "以下是参考提示词（当前工程内置默认，请在此基础上改编）：\n\n" + reference + "\n"
    return tail


def generate_one_semantic_slot(
    *,
    profile_name: str,
    discipline: str,
    slot_key: str,
) -> str:
    slot_key = slot_key.strip()
    defaults = get_default_semantic_overrides()
    if slot_key not in defaults:
        raise ValueError(f"未知的语义槽位: {slot_key!r}")
    slot_title = next((s.title for s in SEMANTIC_SLOTS if s.slot_key == slot_key), slot_key)
    reference = _prepare_reference(defaults[slot_key])
    user_content = _user_payload(
        profile_name=profile_name,
        discipline=discipline,
        slot_key=slot_key,
        slot_title=slot_title,
        reference=reference,
    )
    provider, model = get_llm_for_step("prompt_profile_generate")
    messages = [
        {"role": "system", "content": _meta_system(slot_key, discipline)},
        {"role": "user", "content": user_content},
    ]
    raw = call_llm(
        provider=provider,
        model=model,
        messages=messages,
        temperature=GEN_TEMPERATURE,
        prompt_step="prompt_profile_gen",
    )
    text = _strip_optional_fences(raw)
    _validate_generated(slot_key, text)
    return text


def generate_all_semantic_slots(*, profile_name: str, discipline: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for slot in SEMANTIC_SLOTS:
        out[slot.slot_key] = generate_one_semantic_slot(
            profile_name=profile_name,
            discipline=discipline,
            slot_key=slot.slot_key,
        )
    return out
