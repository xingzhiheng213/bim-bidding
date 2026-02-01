/**
 * BIM 标书生成 App — 步骤状态展示配置（阶段 0.3）
 *
 * 与 theme/README.md「步骤状态约定」一致，供阶段 2 任务详情页 Steps、Tag 等直接引用。
 */

/** 后端步骤状态 */
export type StepStatus = 'pending' | 'running' | 'waiting_user' | 'completed' | 'failed'

/** Ant Design Steps 的 status */
export type StepsStatus = 'wait' | 'process' | 'finish' | 'error'

/** 单状态展示配置 */
export interface StepStatusDisplay {
  /** Ant Design Tag 的 color */
  tagColor: 'default' | 'primary' | 'success' | 'warning' | 'error'
  /** 简短文案 */
  label: string
  /** Ant Design Steps 的 status */
  stepsStatus: StepsStatus
  /** 图标名称（可选，如 LoadingOutlined、CheckCircleOutlined），由使用方按需引入 */
  iconName?: string
}

export const stepStatusDisplay: Record<StepStatus, StepStatusDisplay> = {
  pending: {
    tagColor: 'default',
    label: '待执行',
    stepsStatus: 'wait',
  },
  running: {
    tagColor: 'primary',
    label: '进行中',
    stepsStatus: 'process',
    iconName: 'LoadingOutlined',
  },
  waiting_user: {
    tagColor: 'warning',
    label: '待确认',
    stepsStatus: 'process',
    iconName: 'ExclamationCircleOutlined',
  },
  completed: {
    tagColor: 'success',
    label: '已完成',
    stepsStatus: 'finish',
    iconName: 'CheckCircleOutlined',
  },
  failed: {
    tagColor: 'error',
    label: '失败',
    stepsStatus: 'error',
    iconName: 'CloseCircleOutlined',
  },
}

/** 根据后端状态返回 Ant Steps 的 status */
export function getStepsStatus(stepStatus: StepStatus): StepsStatus {
  return stepStatusDisplay[stepStatus].stepsStatus
}

/** 根据后端状态返回展示文案 */
export function getStepStatusLabel(stepStatus: StepStatus): string {
  return stepStatusDisplay[stepStatus].label
}

/** 任务详情页步骤条顺序（阶段 2.1） */
export const TASK_STEP_ORDER: readonly string[] = [
  'upload',
  'extract',
  'analyze',
  'params',
  'framework',
  'chapters',
  'export',
]

/** 步骤条展示标题 */
export const STEP_TITLES: Record<string, string> = {
  upload: '上传',
  extract: '解析',
  analyze: '分析',
  params: '参数',
  framework: '框架',
  chapters: '按章生成',
  export: '导出',
}
