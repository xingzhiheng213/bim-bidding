/**
 * 仅用于「新增/编辑语义配置」弹窗内展示：
 * - previewInBox：对真实默认提示词的**截断、压缩、口语化改写**，并做**模糊化**（如 BIM → xx），**不照搬**工程内完整原文；
 * - 通过弹窗内「范例」按钮展示：只读、可选中复制；实际生成仍以系统内置默认提示为准（可被下方自定义覆盖）。
 *
 * 维护说明：若后端某槽默认语义大改，可在此同步调整示意口吻与结构，但勿直接复制粘贴仓库 prompts。
 */
export type SemanticSlotModalRow = {
  label: string
  /** 「范例」弹窗内展示的压缩示意正文（多行，仿 system/user 口吻） */
  previewInBox: string
}

export const SEMANTIC_SLOT_MODAL_ROWS: Record<string, SemanticSlotModalRow> = {
  analyze_system: {
    label: '分析 · system',
    previewInBox: `# xx 技术标 · 招标文件解读（示意节选）

你负责从招标文件中抽取与后续「xx 技术标」编制相关的信息。重点包括：项目概况、技术与交付要求、评分与响应要点、废标与实质性条款、时间节点等；对列举与表格宜逐项展开，不必强行套固定目录。

输出宜分条、好查找，方便后面写目录和正文时对照引用。`,
  },
  analyze_user: {
    label: '分析 · user 模板',
    previewInBox: `请按下述要求解读附件中的招标文件正文（附件中已带入当前项目相关信息）。

请兼顾：以「xx 技术标」相关条款为主干，对列举与表格逐项展开，不合并为一句空话；与当前项目弱相关的商务条款可略写或标注「非重点」。`,
  },
  params_system: {
    label: '参数提取 · system',
    previewInBox: `从招标文件分析结果中抽取结构化信息的 system 端：须仅输出合法 JSON，约定若干键（如 project_info、响应要点、废标风险、可选评分项等）。

智能生成时会强调：专业清单按系统内置逐项列举，提取内容锚定当前主专业，避免把其它专业的专篇要点系统性塞进列表字段。`,
  },
  params_user: {
    label: '参数提取 · user 模板',
    previewInBox: `从下列分析结果中提取结构化信息（正文中用约定占位符注入分析全文）。

须保持占位符以便运行时替换；列表类字段宜只收录与主专业技术标直接相关的条目，交叉专业仅作边界/接口级摘取。`,
  },
  framework_system: {
    label: '框架生成 · system（完整模式）',
    previewInBox: `你是「xx 技术标」整体目录的设计助手。请结合分析摘要、响应要点、评分项与参考资料，生成多级章节标题骨架（章 / 节 / 小节），编号与换行按常见技术标习惯即可。

需覆盖评分与必须响应点，避免遗漏关键章节类型；勿输出正文段落，仅输出标题清单。`,
  },
  framework_system_points: {
    label: '框架生成 · system（要点模式）',
    previewInBox: `当前仅提供「已有目录骨架」与「用户补充/修改要点」。请在不曲解要点的前提下调整框架：未提及的章节标题应尽量保持原样，不要做大范围无关改写。

改动宜保守：用户没明确提到的部分，尽量保持不动。`,
  },
  chapter_outline_system: {
    label: '章节 · 小节大纲 · system',
    previewInBox: `你是「xx 技术标」下单章的小节结构规划助手。依据本章标题、分析摘录、响应要点及风险与评分方面的约束，列出本级与下级标题，编号与层级要便于后面写正文时衔接。

详略要适中：既能对上评分项，又不要碎到无法成段。`,
  },
  chapter_content_system: {
    label: '章节 · 正文 · system',
    previewInBox: `你是「xx 技术标」本章正文撰写助手。根据小节大纲与项目要点成文：段落为主，表格与分点为辅；标题层级清楚，表格整齐，用语正式；需要响应评分的地方要写得可辨认、可核对。

避免过度承诺与口语；涉及标准与数据须与招标材料一致。`,
  },
  chapter_regenerate_system: {
    label: '章节 · 重生成 · system',
    previewInBox: `你将同时看到「当前本章正文」与「用户修改要点」。仅对用户明确提到的片段增删改；未提及的句子、顺序与整体版式应尽量保持原样。

若涉及表格，行列关系要清楚、不要打乱结构。输出为整章替换稿，不要加说明性旁白。`,
  },
  review_system: {
    label: '校审 · system',
    previewInBox: `你是「xx 技术标」单章正文的合规与质量校审助手。要分清「版式或格式性写法」和「真正有问题的地方」，不要把正常的标题、编号、表格线当成空话或错误。

审查结果请分条写出：每条说明属于哪一类问题、具体怎么回事；如能对应到原文，可简短摘一句以便核对。没有问题时也要明确说明。`,
  },
}

export function getSemanticSlotModalRow(slotKey: string, fallbackTitle: string): SemanticSlotModalRow {
  const row = SEMANTIC_SLOT_MODAL_ROWS[slotKey]
  if (row) return row
  return {
    label: fallbackTitle,
    previewInBox:
      '该步骤在系统中有内置的默认提示说明。若暂无专门范例，需要定制时请在下方填写完整内容并保存；留空则继续使用内置默认。',
  }
}
