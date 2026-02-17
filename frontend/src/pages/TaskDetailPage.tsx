import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { DownloadOutlined, LoadingOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Checkbox, Collapse, Input, message, Modal, Progress, Spin, Steps, Table, Tag, Typography } from 'antd'
import type { StepStatus } from '../theme/stepStatus'
import {
  getStepsStatus,
  getStepStatusLabel,
  stepStatusDisplay,
  TASK_STEP_ORDER,
  STEP_TITLES,
} from '../theme/stepStatus'
import { designTokens } from '../theme/tokens'
import type { ColumnsType } from 'antd/es/table'
import {
  getFrameworkDiff,
  getChaptersDiff,
} from '../api/compare'
import {
  getTask,
  runAnalyzeStep,
  runExtractStep,
  runParamsStep,
  runFrameworkStep,
  regenerateFrameworkStep,
  saveFrameworkPoints,
  acceptFrameworkStep,
  runChaptersStep,
  saveChapterPoints,
  regenerateChapter,
  uploadTaskFile,
  downloadTaskDocx,
  type TaskDetail,
  type TaskStep,
} from '../api/tasks'
import { DiffView } from '../components/DiffView'
import '../App.css'

const { Title, Text } = Typography

const PREVIEW_LEN = 400
const ANALYZE_PREVIEW_LEN = 500

/** 校审维度说明（任务页展示「审什么」；后续可扩展为从配置/接口读取并合并自定义项） */
const REVIEW_DIMENSIONS: { key: string; label: string; desc: string; tagColor: 'error' | 'warning' | 'default' | 'processing' }[] = [
  { key: 'feibiao', label: '废标项', desc: '与招标废标条款、实质性响应不符或遗漏必须项', tagColor: 'error' },
  { key: 'huanjue', label: '幻觉', desc: '无依据的承诺、编造的数据或条款', tagColor: 'warning' },
  { key: 'taolu', label: '套路', desc: '空话、AI惯用模板化表述、缺乏针对本项目的具体内容', tagColor: 'default' },
  { key: 'jianyi', label: '建议', desc: '可优化表述、补充依据、增强针对性', tagColor: 'processing' },
]

function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    data,
    isLoading: taskLoading,
    isError: taskError,
    error: taskErr,
  } = useQuery({
    queryKey: ['task', id],
    queryFn: () => getTask(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const d = query.state.data as TaskDetail | undefined
      const ex = d?.steps?.find((s: TaskStep) => s.step_key === 'extract')
      const an = d?.steps?.find((s: TaskStep) => s.step_key === 'analyze')
      const pa = d?.steps?.find((s: TaskStep) => s.step_key === 'params')
      const fw = d?.steps?.find((s: TaskStep) => s.step_key === 'framework')
      const ch = d?.steps?.find((s: TaskStep) => s.step_key === 'chapters')
      const rv = d?.steps?.find((s: TaskStep) => s.step_key === 'review')
      return ex?.status === 'running' || an?.status === 'running' || pa?.status === 'running' || fw?.status === 'running' || ch?.status === 'running' || rv?.status === 'running' ? 2000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: ({ taskId, file }: { taskId: string; file: File }) =>
      uploadTaskFile(taskId, file),
    onSuccess: async (_, { taskId }) => {
      message.success('上传成功')
      try {
        await runExtractStep(taskId)
        await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
      } catch (e: unknown) {
        const detail =
          e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
            ? String((e.response.data as { detail: unknown }).detail)
            : e instanceof Error
              ? e.message
              : '请先完成文件上传'
        message.error(detail)
      }
    },
  })

  const extractRunMutation = useMutation({
    mutationFn: (taskId: string) => runExtractStep(taskId),
    onSuccess: async (_, taskId) => {
      message.success('解析已入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '解析入队失败'
      message.error(detail)
    },
  })

  const uploadStep = data?.steps?.find((s) => s.step_key === 'upload')
  const extractStep = data?.steps?.find((s) => s.step_key === 'extract')
  const analyzeStep = data?.steps?.find((s) => s.step_key === 'analyze')
  const paramsStep = data?.steps?.find((s) => s.step_key === 'params')
  const showUploadArea = uploadStep && uploadStep.status !== 'completed'
  const uploadOutput =
    uploadStep?.status === 'completed' && uploadStep.output_snapshot
      ? (() => {
          try {
            return JSON.parse(uploadStep.output_snapshot) as { original_filename?: string }
          } catch {
            return null
          }
        })()
      : null
  let extractText: string | null = null
  if (extractStep?.status === 'completed' && extractStep.output_snapshot) {
    try {
      const out = JSON.parse(extractStep.output_snapshot) as { text?: string }
      extractText = typeof out.text === 'string' ? out.text : null
    } catch {
      extractText = null
    }
  }
  let analyzeText: string | null = null
  if (analyzeStep?.status === 'completed' && analyzeStep.output_snapshot) {
    try {
      const out = JSON.parse(analyzeStep.output_snapshot) as { text?: string }
      analyzeText = typeof out.text === 'string' ? out.text : null
    } catch {
      analyzeText = null
    }
  }
  const showAnalyzeTrigger =
    extractStep?.status === 'completed' &&
    analyzeStep &&
    (analyzeStep.status === 'pending' || analyzeStep.status === 'failed')
  const analyzeRunning = analyzeStep?.status === 'running'
  let paramsOutput: { project_info?: Record<string, unknown>; bim_requirements?: string[]; risk_points?: string[] } | null = null
  if (paramsStep?.status === 'completed' && paramsStep.output_snapshot) {
    try {
      const out = JSON.parse(paramsStep.output_snapshot) as { project_info?: Record<string, unknown>; bim_requirements?: string[]; risk_points?: string[] }
      paramsOutput = out
    } catch {
      paramsOutput = null
    }
  }
  const showParamsTrigger =
    analyzeStep?.status === 'completed' &&
    (!paramsStep || paramsStep.status === 'pending' || paramsStep.status === 'failed')
  const paramsRunning = paramsStep?.status === 'running'

  const frameworkStep = data?.steps?.find((s) => s.step_key === 'framework')
  const frameworkStepDone =
    frameworkStep?.status === 'completed' || frameworkStep?.status === 'waiting_user'
  type FrameworkSection = { number?: string; title?: string; subsections?: { number?: string; title?: string }[] }
  type FrameworkChapter = { number: number; title: string; full_name: string; sections?: FrameworkSection[] }
  let frameworkChapters: FrameworkChapter[] = []
  let frameworkExtraPoints: string[] = []
  if (frameworkStepDone && frameworkStep?.output_snapshot) {
    try {
      const out = JSON.parse(frameworkStep.output_snapshot) as {
        chapters?: FrameworkChapter[]
        extra_points?: string[]
      }
      frameworkChapters = Array.isArray(out.chapters) ? out.chapters : []
      frameworkExtraPoints = Array.isArray(out.extra_points) ? out.extra_points : []
    } catch {
      frameworkChapters = []
      frameworkExtraPoints = []
    }
  }
  const showFrameworkTrigger =
    paramsStep?.status === 'completed' &&
    (!frameworkStep || frameworkStep.status === 'pending' || frameworkStep.status === 'failed')
  const frameworkRunning = frameworkStep?.status === 'running'

  const chaptersStep = data?.steps?.find((s) => s.step_key === 'chapters')
  const showChaptersTrigger =
    frameworkStep?.status === 'completed' &&
    (!chaptersStep || chaptersStep.status === 'pending' || chaptersStep.status === 'failed')
  const chaptersRunning = chaptersStep?.status === 'running'
  let chaptersTotal = 0
  let chaptersCurrent = 0
  let chaptersContent: Record<string, string> = {}
  let chaptersPoints: Record<string, string[]> = {}
  if (chaptersStep?.output_snapshot) {
    try {
      const out = JSON.parse(chaptersStep.output_snapshot) as {
        total?: number
        current?: number
        chapters?: Record<string, string>
        chapter_points?: Record<string, string[]>
      }
      chaptersTotal = typeof out.total === 'number' ? out.total : 0
      chaptersCurrent = typeof out.current === 'number' ? out.current : 0
      chaptersContent = out.chapters && typeof out.chapters === 'object' ? out.chapters : {}
      chaptersPoints = out.chapter_points && typeof out.chapter_points === 'object' ? out.chapter_points : {}
    } catch {
      chaptersTotal = 0
      chaptersCurrent = 0
      chaptersContent = {}
      chaptersPoints = {}
    }
  }

  const stepColumns: ColumnsType<TaskStep> = [
    { title: '步骤', dataIndex: 'step_key', key: 'step_key' },
    { title: '状态', dataIndex: 'status', key: 'status' },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => new Date(t).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
    },
  ]

  const stepsItems =
    data?.steps != null
      ? TASK_STEP_ORDER.map((stepKey) => {
          const step = data.steps.find((s) => s.step_key === stepKey)
          const status: StepStatus =
            step && ['pending', 'running', 'waiting_user', 'completed', 'failed'].includes(step.status)
              ? (step.status as StepStatus)
              : 'pending'
          const stepsStatus = getStepsStatus(status)
          const label = getStepStatusLabel(status)
          return {
            title: STEP_TITLES[stepKey] ?? stepKey,
            description: label,
            status: stepsStatus,
            icon: status === 'running' ? <LoadingOutlined /> : undefined,
          }
        })
      : []

  const stepsCurrent =
    data?.steps != null
      ? (() => {
          const runningOrWaitingIdx = TASK_STEP_ORDER.findIndex((key) =>
            data.steps.some(
              (s) => s.step_key === key && (s.status === 'running' || s.status === 'waiting_user')
            )
          )
          if (runningOrWaitingIdx >= 0) return runningOrWaitingIdx
          const firstNotDoneIdx = TASK_STEP_ORDER.findIndex((key) => {
            const step = data.steps.find((s) => s.step_key === key)
            const status = step?.status ?? 'pending'
            return status !== 'completed' && status !== 'failed'
          })
          return firstNotDoneIdx >= 0 ? firstNotDoneIdx : TASK_STEP_ORDER.length - 1
        })()
      : 0

  const handleStepClick = (nowStepIndex: number) => {
    const stepKey = TASK_STEP_ORDER[nowStepIndex]
    if (stepKey) {
      document.getElementById(`step-${stepKey}`)?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleUpload = () => {
    if (!id || !selectedFile) return
    uploadMutation.mutate({ taskId: id, file: selectedFile })
  }

  const analyzeMutation = useMutation({
    mutationFn: (taskId: string) => runAnalyzeStep(taskId),
    onSuccess: async (_, taskId) => {
      message.success('分析已入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '分析请求失败'
      message.error(detail)
    },
  })

  const handleRunAnalyze = () => {
    if (!id) return
    analyzeMutation.mutate(id)
  }

  const paramsMutation = useMutation({
    mutationFn: (taskId: string) => runParamsStep(taskId),
    onSuccess: async (_, taskId) => {
      message.success('参数提取已入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '参数提取请求失败'
      message.error(detail)
    },
  })

  const handleRunParams = () => {
    if (!id) return
    paramsMutation.mutate(id)
  }

  const frameworkMutation = useMutation({
    mutationFn: (taskId: string) => runFrameworkStep(taskId),
    onSuccess: async (_, taskId) => {
      message.success('框架已入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '框架生成请求失败'
      message.error(detail)
    },
  })

  const handleRunFramework = () => {
    if (!id) return
    frameworkMutation.mutate(id)
  }

  const regenerateFrameworkMutation = useMutation({
    mutationFn: (taskId: string) => regenerateFrameworkStep(taskId),
    onSuccess: async (_, taskId) => {
      message.success('框架已重新入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '重新生成框架请求失败'
      message.error(detail)
    },
  })

  const handleRegenerateFramework = () => {
    if (!id) return
    regenerateFrameworkMutation.mutate(id)
  }

  const savePointsMutation = useMutation({
    mutationFn: ({ taskId, added_points }: { taskId: string; added_points: string[] }) =>
      saveFrameworkPoints(taskId, added_points),
    onSuccess: async (_, { taskId }) => {
      message.success('已保存要点，可点击「重新生成框架」使框架按您的要点更新')
      setAddPointsModalOpen(false)
      setAddPointsText('')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '保存要点失败'
      message.error(detail)
    },
  })

  const acceptFrameworkMutation = useMutation({
    mutationFn: ({ taskId, added_points }: { taskId: string; added_points: string[] }) =>
      acceptFrameworkStep(taskId, added_points),
    onSuccess: async (_, { taskId }) => {
      message.success('已接受并继续')
      setAddPointsModalOpen(false)
      setAddPointsText('')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '接受框架请求失败'
      message.error(detail)
    },
  })

  const [selectedChapterNumbers, setSelectedChapterNumbers] = useState<number[]>([])

  useEffect(() => {
    if (frameworkChapters.length > 0) {
      setSelectedChapterNumbers(frameworkChapters.map((ch) => ch.number))
    }
  }, [frameworkChapters.length])

  const runChaptersMutation = useMutation({
    mutationFn: ({ taskId, chapterNumbers }: { taskId: string; chapterNumbers?: number[] }) =>
      runChaptersStep(taskId, chapterNumbers),
    onSuccess: async (_, { taskId }) => {
      message.success('按章生成已入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '按章生成请求失败'
      message.error(detail)
    },
  })

  const handleRunChapters = () => {
    if (!id) return
    if (selectedChapterNumbers.length === 0) {
      message.warning('请至少选择一章')
      return
    }
    const chapterNumbers =
      selectedChapterNumbers.length === frameworkChapters.length
        ? undefined
        : [...selectedChapterNumbers].sort((a, b) => a - b)
    runChaptersMutation.mutate({ taskId: id, chapterNumbers })
  }

  const [addPointsModalOpen, setAddPointsModalOpen] = useState(false)
  const [addPointsText, setAddPointsText] = useState('')
  const [chapterAddPointsModalOpen, setChapterAddPointsModalOpen] = useState(false)
  const [chapterAddPointsText, setChapterAddPointsText] = useState('')
  const [chapterAddPointsForChapter, setChapterAddPointsForChapter] = useState<number | null>(null)
  const [diffModalOpen, setDiffModalOpen] = useState(false)
  const [diffModalTitle, setDiffModalTitle] = useState('')
  const [diffModalLoading, setDiffModalLoading] = useState(false)
  const [diffModalError, setDiffModalError] = useState<string | null>(null)
  const [diffModalData, setDiffModalData] = useState<{
    original: string
    modified: string
    diff: { type: 'equal' | 'add' | 'del'; text: string }[]
  } | null>(null)

  const saveChapterPointsMutation = useMutation({
    mutationFn: ({
      taskId,
      chapterNumber,
      added_points,
    }: {
      taskId: string
      chapterNumber: number
      added_points: string[]
    }) => saveChapterPoints(taskId, chapterNumber, added_points),
    onSuccess: async (_, { taskId }) => {
      message.success('已保存要点，可点击「重新生成本章」使该章按您的要点更新')
      setChapterAddPointsModalOpen(false)
      setChapterAddPointsText('')
      setChapterAddPointsForChapter(null)
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '保存要点失败'
      message.error(detail)
    },
  })

  const regenerateChapterMutation = useMutation({
    mutationFn: ({
      taskId,
      chapterNumber,
      added_points,
    }: {
      taskId: string
      chapterNumber: number
      added_points?: string[]
    }) => regenerateChapter(taskId, chapterNumber, added_points),
    onSuccess: async (_, { taskId }) => {
      message.success('该章已重新入队')
      await queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '重新生成本章请求失败'
      message.error(detail)
    },
  })

  const handleAcceptAndContinue = () => {
    if (!id) return
    acceptFrameworkMutation.mutate({ taskId: id, added_points: [] })
  }

  const handleOpenAddPoints = () => setAddPointsModalOpen(true)
  const handleOpenChapterAddPoints = (chapterNumber: number) => {
    setChapterAddPointsForChapter(chapterNumber)
    setChapterAddPointsText((chaptersPoints[String(chapterNumber)] || []).join('\n'))
    setChapterAddPointsModalOpen(true)
  }
  const handleChapterAddPointsSubmit = () => {
    if (!id || chapterAddPointsForChapter == null) return
    const points = chapterAddPointsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    saveChapterPointsMutation.mutate({
      taskId: id,
      chapterNumber: chapterAddPointsForChapter,
      added_points: points,
    })
  }
  const handleRegenerateChapter = (chapterNumber: number) => {
    if (!id) return
    regenerateChapterMutation.mutate({ taskId: id, chapterNumber })
  }
  const handleOpenFrameworkDiff = () => {
    if (!id) return
    setDiffModalTitle('框架对比')
    setDiffModalOpen(true)
    setDiffModalError(null)
    setDiffModalData(null)
    setDiffModalLoading(true)
    getFrameworkDiff(id)
      .then((res) => setDiffModalData({ original: res.original, modified: res.modified, diff: res.diff }))
      .catch((e: unknown) => {
        const detail =
          e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
            ? String((e.response.data as { detail: unknown }).detail)
            : e instanceof Error
              ? e.message
              : '加载对比失败'
        setDiffModalError(detail)
      })
      .finally(() => setDiffModalLoading(false))
  }
  const handleOpenChapterDiff = (chapterNumber: number) => {
    if (!id) return
    setDiffModalTitle(`第 ${chapterNumber} 章对比`)
    setDiffModalOpen(true)
    setDiffModalError(null)
    setDiffModalData(null)
    setDiffModalLoading(true)
    getChaptersDiff(id, chapterNumber)
      .then((res) => setDiffModalData({ original: res.original, modified: res.modified, diff: res.diff }))
      .catch((e: unknown) => {
        const detail =
          e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
            ? String((e.response.data as { detail: unknown }).detail)
            : e instanceof Error
              ? e.message
              : '加载对比失败'
        setDiffModalError(detail)
      })
      .finally(() => setDiffModalLoading(false))
  }
  const handleAddPointsSubmit = () => {
    if (!id) return
    const points = addPointsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    savePointsMutation.mutate({ taskId: id, added_points: points })
  }

  const [downloadLoading, setDownloadLoading] = useState(false)
  const handleDownloadDocx = async () => {
    if (!id) return
    setDownloadLoading(true)
    const hide = message.loading('正在生成 Word 文档…', 0)
    try {
      const blob = await downloadTaskDocx(id)
      if (blob.type && blob.type.includes('application/json')) {
        const text = await blob.text()
        const err = JSON.parse(text) as { detail?: unknown }
        throw new Error(String(err.detail ?? '下载失败'))
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `BIM标书_任务${id}.docx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('下载成功')
    } catch (e: unknown) {
      const detail =
        e instanceof Error ? e.message : '下载失败'
      message.error(detail)
    } finally {
      hide()
      setDownloadLoading(false)
    }
  }

  if (!id) {
    return (
      <>
        <Text type="danger">缺少任务 ID</Text>
        <Link to="/" style={{ marginLeft: 16 }}>
          返回首页
        </Link>
      </>
    )
  }

  return (
    <>
      <Title level={2} style={{ marginBottom: 16 }}>
        {data?.name ? data.name : '任务详情'}
      </Title>
        {taskLoading && <Spin />}
        {taskError && (
          <Text type="danger">
            {taskErr instanceof Error ? taskErr.message : String(taskErr)}
          </Text>
        )}
        {data && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Text strong>任务名称：</Text>
              <Text>{data.name || '（未命名）'}</Text>
              <span style={{ marginLeft: 24 }} />
              <Text strong>任务 ID：</Text>
              <Text>{data.id}</Text>
              <span style={{ marginLeft: 24 }} />
              <Text strong>状态：</Text>
              <Text>{data.status}</Text>
              <span style={{ marginLeft: 24 }} />
              <Text strong>创建时间：</Text>
              <Text>{new Date(data.created_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}</Text>
            </div>

            {stepsItems.length > 0 && (
              <Steps
                current={stepsCurrent}
                items={stepsItems}
                onChange={handleStepClick}
                style={{ marginBottom: designTokens.marginLG }}
              />
            )}

            {frameworkStep?.status === 'waiting_user' && (
              <Alert
                type="warning"
                message="当前步骤：框架待确认 — 请确认框架或添加要点后继续。"
                showIcon
                style={{ marginBottom: designTokens.marginLG }}
              />
            )}

            {TASK_STEP_ORDER.map((stepKey) => {
              const step = data.steps?.find((s) => s.step_key === stepKey)
              const status: StepStatus =
                step && ['pending', 'running', 'waiting_user', 'completed', 'failed'].includes(step.status)
                  ? (step.status as StepStatus)
                  : 'pending'
              const cardStyle: React.CSSProperties =
                stepKey === 'framework' && status === 'waiting_user'
                  ? {
                      marginBottom: designTokens.marginLG,
                      borderLeft: `4px solid ${designTokens.colorWarning}`,
                      background: 'rgba(250, 173, 20, 0.06)',
                    }
                  : { marginBottom: designTokens.marginLG }
              return (
                <Card
                  key={stepKey}
                  id={`step-${stepKey}`}
                  title={STEP_TITLES[stepKey]}
                  extra={<Tag color={stepStatusDisplay[status].tagColor}>{getStepStatusLabel(status)}</Tag>}
                  style={cardStyle}
                >
                  {stepKey === 'upload' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {showUploadArea ? '上传招标文件' : uploadOutput?.original_filename ? `已上传：${uploadOutput.original_filename}` : '待上传'}
                      </Text>
                      {showUploadArea && (
                        <>
                          <input
                            type="file"
                            accept=".pdf,.doc,.docx"
                            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                            style={{ marginRight: 8 }}
                          />
                          <Button
                            type="primary"
                            loading={uploadMutation.isPending}
                            disabled={!selectedFile}
                            onClick={handleUpload}
                          >
                            上传
                          </Button>
                        </>
                      )}
                    </>
                  )}
                  {stepKey === 'extract' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {uploadStep?.status !== 'completed'
                          ? '请先完成上传'
                          : extractStep?.status === 'running'
                            ? '解析中，请稍候…'
                            : extractStep?.status === 'completed' && extractText !== null
                              ? `解析完成，共 ${extractText.length} 字。`
                              : extractStep?.status === 'failed'
                                ? '解析失败'
                                : '待解析'}
                      </Text>
                      {extractStep?.status === 'failed' && extractStep.error_message && (
                        <Alert
                          type="error"
                          message="解析失败"
                          description={extractStep.error_message}
                          showIcon
                          style={{ marginTop: designTokens.marginSM }}
                          action={
                            <Button
                              size="small"
                              danger
                              onClick={() => id && extractRunMutation.mutate(id)}
                              loading={extractRunMutation.isPending}
                            >
                              重试
                            </Button>
                          }
                        />
                      )}
                      {extractStep?.status === 'completed' && extractText !== null && (
                        <Collapse defaultActiveKey={[]} style={{ marginTop: designTokens.marginSM }} items={[{ key: 'preview', label: '预览', children: <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>{extractText.slice(0, PREVIEW_LEN)}{extractText.length > PREVIEW_LEN ? '…' : ''}</Typography.Paragraph> }]} />
                      )}
                    </>
                  )}
                  {stepKey === 'analyze' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {extractStep?.status !== 'completed'
                          ? '请先完成解析'
                          : analyzeRunning
                            ? '分析中，请稍候…'
                            : showAnalyzeTrigger
                              ? '可开始分析'
                              : analyzeStep?.status === 'completed'
                                ? '分析完成。'
                                : analyzeStep?.status === 'failed'
                                  ? '分析失败'
                                  : '待分析'}
                      </Text>
                      {showAnalyzeTrigger && (
                        <Button type="primary" loading={analyzeMutation.isPending} onClick={handleRunAnalyze} style={{ marginBottom: designTokens.marginSM }}>
                          开始分析
                        </Button>
                      )}
                      {analyzeStep?.status === 'failed' && analyzeStep.error_message && (
                        <Alert type="error" message="分析失败" description={analyzeStep.error_message} showIcon style={{ marginTop: designTokens.marginSM }} action={<Button size="small" danger onClick={handleRunAnalyze}>重试</Button>} />
                      )}
                      {analyzeStep?.status === 'completed' && analyzeText !== null && (
                        <Collapse defaultActiveKey={[]} style={{ marginTop: designTokens.marginSM }} items={[{ key: 'analyze', label: '分析结果', children: <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }} ellipsis={analyzeText.length > ANALYZE_PREVIEW_LEN ? { rows: 8, expandable: true } : false}>{analyzeText}</Typography.Paragraph> }]} />
                      )}
                    </>
                  )}
                  {stepKey === 'params' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {analyzeStep?.status !== 'completed'
                          ? '请先完成分析'
                          : paramsRunning
                            ? '参数提取中，请稍候…'
                            : showParamsTrigger
                              ? '可开始参数提取'
                              : paramsStep?.status === 'completed'
                                ? '参数提取完成。'
                                : paramsStep?.status === 'failed'
                                  ? '参数提取失败'
                                  : '待参数提取'}
                      </Text>
                      {showParamsTrigger && (
                        <Button type="primary" loading={paramsMutation.isPending} onClick={handleRunParams} style={{ marginBottom: designTokens.marginSM }}>
                          开始参数提取
                        </Button>
                      )}
                      {paramsStep?.status === 'failed' && paramsStep.error_message && (
                        <Alert type="error" message="参数提取失败" description={paramsStep.error_message} showIcon style={{ marginTop: designTokens.marginSM }} action={<Button size="small" danger onClick={handleRunParams}>重试</Button>} />
                      )}
                      {paramsStep?.status === 'completed' && paramsOutput && (
                        <Collapse
                          defaultActiveKey={[]}
                          style={{ marginTop: designTokens.marginSM }}
                          items={[
                            { key: 'project_info', label: '项目信息', children: <Typography.Paragraph style={{ marginBottom: 0 }}>{Object.keys(paramsOutput.project_info || {}).length === 0 ? '（无）' : Object.entries(paramsOutput.project_info || {}).map(([k, v]) => <span key={k} style={{ display: 'block', marginBottom: 4 }}><Text strong>{k}：</Text>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>)}</Typography.Paragraph> },
                            { key: 'bim_requirements', label: 'BIM 要求', children: <ul style={{ marginBottom: 0, paddingLeft: 20 }}>{(paramsOutput.bim_requirements || []).length === 0 ? '（无）' : (paramsOutput.bim_requirements || []).map((item, i) => <li key={i}>{item}</li>)}</ul> },
                            { key: 'risk_points', label: '风险点', children: <ul style={{ marginBottom: 0, paddingLeft: 20 }}>{(paramsOutput.risk_points || []).length === 0 ? '（无）' : (paramsOutput.risk_points || []).map((item, i) => <li key={i}>{item}</li>)}</ul> },
                          ]}
                        />
                      )}
                    </>
                  )}

                  {stepKey === 'framework' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {paramsStep?.status !== 'completed'
                          ? '请先完成参数提取'
                          : frameworkRunning
                            ? '框架生成中，请稍候…'
                            : showFrameworkTrigger
                              ? '可开始生成框架'
                              : frameworkStep?.status === 'waiting_user'
                                ? '框架已生成，等待您审核。'
                                : frameworkStep?.status === 'completed'
                                  ? '框架已确认，可进入按章生成。'
                                  : frameworkStep?.status === 'failed'
                                    ? '框架生成失败'
                                    : '待生成框架'}
                      </Text>
                      {showFrameworkTrigger && (
                        <Button type="primary" loading={frameworkMutation.isPending} onClick={handleRunFramework} style={{ marginBottom: designTokens.marginSM }}>
                          开始生成框架
                        </Button>
                      )}
                      {frameworkStep?.status === 'waiting_user' && frameworkChapters.length > 0 && (
                        <div style={{ marginBottom: designTokens.marginSM }}>
                          <Alert
                            type="warning"
                            message="请确认框架或添加要点后继续。"
                            showIcon
                            style={{ marginBottom: designTokens.marginSM }}
                          />
                          <Button type="primary" style={{ marginRight: 8 }} loading={acceptFrameworkMutation.isPending} onClick={handleAcceptAndContinue}>接受并继续</Button>
                          <Button style={{ marginRight: 8 }} loading={regenerateFrameworkMutation.isPending} onClick={handleRegenerateFramework}>重新生成框架</Button>
                          <Button style={{ marginRight: 8 }} loading={savePointsMutation.isPending} onClick={handleOpenAddPoints}>添加要点</Button>
                          <Button onClick={handleOpenFrameworkDiff}>查看框架对比</Button>
                        </div>
                      )}
                      {frameworkStep?.status === 'completed' && frameworkChapters.length > 0 && (
                        <div style={{ marginBottom: designTokens.marginSM }}>
                          <Button size="small" onClick={handleOpenFrameworkDiff}>查看框架对比</Button>
                        </div>
                      )}
                      {frameworkStep?.status === 'failed' && frameworkStep.error_message && (
                        <Alert type="error" message="框架生成失败" description={frameworkStep.error_message} showIcon style={{ marginTop: designTokens.marginSM }} action={<Button size="small" danger onClick={handleRunFramework}>重试</Button>} />
                      )}
                      {frameworkStepDone && (
                        <Collapse
                          defaultActiveKey={[]}
                          style={{ marginTop: designTokens.marginSM }}
                          items={[
                            ...(frameworkChapters.length > 0 ? [{ key: 'chapters', label: '章节框架', children: <ul style={{ marginBottom: 0, paddingLeft: 20 }}>{frameworkChapters.map((ch, i) => (
                              <li key={i}>
                                <Text strong>第{ch.number}章</Text> {ch.title}
                                {Array.isArray(ch.sections) && ch.sections.length > 0 && (
                                  <ul style={{ marginBottom: 0, paddingLeft: 20, marginTop: 4 }}>
                                    {ch.sections.map((sec, j) => (
                                      <li key={j}>
                                        {sec.number} {sec.title}
                                        {Array.isArray(sec.subsections) && sec.subsections.length > 0 && (
                                          <ul style={{ marginBottom: 0, paddingLeft: 20, marginTop: 2 }}>
                                            {sec.subsections.map((sub, k) => (
                                              <li key={k}>{sub.number} {sub.title}</li>
                                            ))}
                                          </ul>
                                        )}
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </li>
                            ))}</ul> }] : []),
                            ...(frameworkStep?.status === 'completed' && frameworkExtraPoints.length > 0 ? [{ key: 'points', label: '已添加要点', children: <ul style={{ marginBottom: 0, paddingLeft: 20 }}>{frameworkExtraPoints.map((p, i) => <li key={i}>{p}</li>)}</ul> }] : []),
                          ]}
                        />
                      )}
                      {frameworkStepDone && frameworkChapters.length === 0 && <Text type="secondary">框架已生成，但未解析到章节（可查看步骤列表）。</Text>}
                    </>
                  )}

                  {stepKey === 'chapters' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {frameworkStep?.status !== 'completed'
                          ? '请先确认框架（接受并继续）'
                          : chaptersRunning
                            ? (chaptersCurrent > 0 ? `正在生成第 ${chaptersCurrent} 章 / 共 ${chaptersTotal} 章…` : `正在生成…（共 ${chaptersTotal} 章）`)
                            : showChaptersTrigger
                              ? '选择章节后开始按章生成'
                              : chaptersStep?.status === 'completed'
                                ? '生成完成。'
                                : chaptersStep?.status === 'failed'
                                  ? '按章生成失败'
                                  : '待按章生成'}
                      </Text>
                      {chaptersRunning && (
                        <Progress percent={chaptersTotal > 0 ? Math.round((Object.keys(chaptersContent).length / chaptersTotal) * 100) : 0} status="active" style={{ marginBottom: designTokens.marginSM, maxWidth: 400 }} />
                      )}
                      {showChaptersTrigger && frameworkChapters.length > 0 && (
                        <div style={{ marginBottom: designTokens.marginSM }}>
                          <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginXS }}>选择要生成的章节：</Text>
                          <Checkbox.Group value={selectedChapterNumbers} onChange={(vals) => setSelectedChapterNumbers(vals as number[])} options={frameworkChapters.map((ch) => ({ label: `第${ch.number}章 ${ch.title}`, value: ch.number }))} />
                          <div style={{ marginTop: 4 }}>
                            <Button type="link" size="small" onClick={() => setSelectedChapterNumbers(frameworkChapters.map((ch) => ch.number))}>全选</Button>
                            <Button type="link" size="small" onClick={() => setSelectedChapterNumbers([])}>取消全选</Button>
                          </div>
                          <Button type="primary" loading={runChaptersMutation.isPending} onClick={handleRunChapters} disabled={selectedChapterNumbers.length === 0} style={{ marginTop: designTokens.marginSM }}>
                            开始按章生成
                          </Button>
                        </div>
                      )}
                      {chaptersStep?.status === 'failed' && chaptersStep.error_message && (
                        <Alert type="error" message="按章生成失败" description={chaptersStep.error_message} showIcon style={{ marginTop: designTokens.marginSM }} action={<Button size="small" danger onClick={handleRunChapters}>重试</Button>} />
                      )}
                      {chaptersStep?.status === 'completed' && Object.keys(chaptersContent).length > 0 && (
                        <Collapse
                          defaultActiveKey={[]}
                          size="small"
                          style={{ marginTop: designTokens.marginSM }}
                          items={Object.keys(chaptersContent)
                            .sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
                            .map((num) => {
                              const numInt = parseInt(num, 10)
                              return {
                                key: num,
                                label: `第${num}章`,
                                children: (
                                  <div>
                                    <div style={{ marginBottom: 8 }}>
                                      <Button size="small" style={{ marginRight: 8 }} onClick={() => handleOpenChapterAddPoints(numInt)}>添加要点</Button>
                                      <Button size="small" style={{ marginRight: 8 }} onClick={() => handleRegenerateChapter(numInt)} loading={regenerateChapterMutation.isPending}>重新生成本章</Button>
                                      <Button size="small" onClick={() => handleOpenChapterDiff(numInt)}>查看本章对比</Button>
                                      {(chaptersPoints[num] || []).length > 0 && <Text type="secondary" style={{ marginLeft: 8 }}>已添加 {(chaptersPoints[num] || []).length} 个要点</Text>}
                                    </div>
                                    <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 360, overflow: 'auto', marginBottom: 0, padding: 12, background: '#fafafa', borderRadius: 4, fontSize: 13 }}>{chaptersContent[num]}</pre>
                                  </div>
                                ),
                              }
                            })}
                        />
                      )}
                    </>
                  )}
                  {stepKey === 'review' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {chaptersStep?.status !== 'completed'
                          ? '请先完成按章生成'
                          : step?.status === 'running'
                            ? '审查中…'
                            : step?.status === 'completed'
                              ? '审查完成。'
                              : step?.status === 'failed'
                                ? '审查失败'
                                : '可进入校审模块开始审查'}
                      </Text>
                      <div style={{ marginBottom: designTokens.marginMD }}>
                        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                          校审将从以下维度检查各章：
                        </Text>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {REVIEW_DIMENSIONS.map((d) => (
                            <div
                              key={d.key}
                              style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: 8,
                                padding: '6px 10px',
                                background: 'rgba(0,0,0,0.02)',
                                borderRadius: 6,
                              }}
                            >
                              <Tag
                                color={d.tagColor}
                                style={{
                                  marginRight: 0,
                                  flexShrink: 0,
                                  fontSize: 12,
                                  minWidth: 56,
                                  textAlign: 'center',
                                  display: 'inline-block',
                                }}
                              >
                                {d.label}
                              </Tag>
                              <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.5, marginBottom: 0, flex: 1 }}>
                                {d.desc}
                              </Text>
                            </div>
                          ))}
                        </div>
                      </div>
                      {step?.status === 'failed' && step?.error_message && (
                        <Alert type="error" message="审查失败" description={step.error_message} showIcon style={{ marginTop: designTokens.marginSM }} />
                      )}
                      {chaptersStep?.status === 'completed' && id && (
                        <Button type="primary" onClick={() => navigate(`/review/${id}`)}>
                          进入校审
                        </Button>
                      )}
                    </>
                  )}
                  {stepKey === 'export' && (
                    <>
                      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
                        {chaptersStep?.status !== 'completed' ? '请先完成按章生成' : '生成完成，可下载 Word 文档。'}
                      </Text>
                      {chaptersStep?.status === 'completed' && (
                        <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownloadDocx} loading={downloadLoading}>
                          下载 Word
                        </Button>
                      )}
                    </>
                  )}
                </Card>
              )
            })}

            <Title level={4} style={{ marginTop: 24 }}>
              步骤列表
            </Title>
            <Table
              rowKey="id"
              columns={stepColumns}
              dataSource={data.steps}
              pagination={false}
              size="small"
            />
          </>
        )}
      <Modal
        title="添加要点 / 修改建议"
        open={addPointsModalOpen}
        onCancel={() => setAddPointsModalOpen(false)}
        onOk={handleAddPointsSubmit}
        okText="保存要点"
        cancelText="取消"
        confirmLoading={savePointsMutation.isPending}
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          每行一个要点或修改建议，保存后可点击「重新生成框架」，新框架会按您的要点调整。
        </Typography.Paragraph>
        <Input.TextArea
          rows={6}
          value={addPointsText}
          onChange={(e) => setAddPointsText(e.target.value)}
          placeholder="要点1&#10;要点2&#10;..."
        />
      </Modal>
      <Modal
        title={chapterAddPointsForChapter != null ? `为第 ${chapterAddPointsForChapter} 章添加要点` : '添加要点'}
        open={chapterAddPointsModalOpen}
        onCancel={() => {
          setChapterAddPointsModalOpen(false)
          setChapterAddPointsText('')
          setChapterAddPointsForChapter(null)
        }}
        onOk={handleChapterAddPointsSubmit}
        okText="保存要点"
        cancelText="取消"
        confirmLoading={saveChapterPointsMutation.isPending}
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          每行一个要点或修改建议，保存后可点击「重新生成本章」使该章按您的要点更新。
        </Typography.Paragraph>
        <Input.TextArea
          rows={6}
          value={chapterAddPointsText}
          onChange={(e) => setChapterAddPointsText(e.target.value)}
          placeholder="要点1&#10;要点2&#10;..."
        />
      </Modal>
      <Modal
        title={diffModalTitle || '对比'}
        open={diffModalOpen}
        onCancel={() => setDiffModalOpen(false)}
        footer={null}
        width={800}
      >
        {diffModalLoading && (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <Spin tip="加载对比中…" />
          </div>
        )}
        {diffModalError && !diffModalLoading && (
          <Alert
            type="warning"
            message="无法加载对比"
            description={diffModalError}
            showIcon
            style={{ marginTop: 8 }}
          />
        )}
        {diffModalData && !diffModalLoading && (
          <div>
            <Collapse
              size="small"
              style={{ marginBottom: 12 }}
              items={[
                {
                  key: '1',
                  label: '修改前 / 修改后原文（可折叠）',
                  children: (
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>修改前</div>
                        <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 200, overflow: 'auto', fontSize: 12 }}>
                          {diffModalData.original || '(空)'}
                        </pre>
                      </div>
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>修改后</div>
                        <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 200, overflow: 'auto', fontSize: 12 }}>
                          {diffModalData.modified || '(空)'}
                        </pre>
                      </div>
                    </div>
                  ),
                },
              ]}
            />
            <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>对比结果（红=删除，绿=新增）</div>
            <div
              style={{
                border: '1px solid #d9d9d9',
                borderRadius: 4,
                padding: 12,
                background: '#fafafa',
                minHeight: 80,
                maxHeight: 400,
                overflow: 'auto',
              }}
            >
              <DiffView diff={diffModalData.diff} />
            </div>
          </div>
        )}
      </Modal>
    </>
  )
}

export default TaskDetailPage
