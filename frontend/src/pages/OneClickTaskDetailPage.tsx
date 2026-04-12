import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Alert, Button, Input, message, Modal, Spin, Typography } from 'antd'
import {
  acceptFrameworkStep,
  cancelTask,
  downloadTaskDocx,
  getTask,
  regenerateFrameworkStep,
  runAnalyzeStep,
  runChaptersStep,
  runExtractStep,
  runFrameworkStep,
  runParamsStep,
  runReview,
  saveFrameworkPoints,
  uploadTaskFile,
  type TaskDetail,
  type TaskStep,
} from '../api/tasks'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text } = Typography

const POLL_INTERVAL_MS = 2000
const CANCELLED_STORAGE_KEY_PREFIX = 'one_click_cancelled_'

function getCancelledStorageKey(taskId: string): string {
  return CANCELLED_STORAGE_KEY_PREFIX + taskId
}

type Phase = 'idle' | 'uploading' | 'running' | 'confirm_framework' | 'done' | 'failed' | 'cancelled'
type PipelineStep =
  | 'extract'
  | 'analyze'
  | 'params'
  | 'framework'
  | 'confirm_framework'
  | 'chapters'
  | 'review'
  | 'done'

interface FrameworkSection {
  number?: string
  title?: string
  subsections?: { number?: string; title?: string }[]
}
interface FrameworkChapter {
  number: number
  title: string
  full_name: string
  sections?: FrameworkSection[]
}

function getStep(data: TaskDetail | undefined, stepKey: string): TaskStep | undefined {
  return data?.steps?.find((s) => s.step_key === stepKey)
}

function getStatusLabel(
  phase: Phase,
  data: TaskDetail | undefined,
  pipelineStep: PipelineStep
): string {
  if (phase === 'idle') return '请上传招标文件'
  if (phase === 'uploading') return '正在上传…'
  if (phase === 'failed') return '生成失败'
  if (phase === 'done') return '完成'
  if (phase === 'cancelled') return '已取消'
  if (!data?.steps) return '请稍候…'

  const extractStep = getStep(data, 'extract')
  const analyzeStep = getStep(data, 'analyze')
  const paramsStep = getStep(data, 'params')
  const frameworkStep = getStep(data, 'framework')
  const chaptersStep = getStep(data, 'chapters')
  const reviewStep = getStep(data, 'review')

  if (extractStep?.status === 'running') return '正在解析招标文档'
  if (analyzeStep?.status === 'running') return '正在分析招标文件'
  if (paramsStep?.status === 'running') return '正在提取参数与要求'
  if (frameworkStep?.status === 'running') return '生成框架中'
  if (frameworkStep?.status === 'waiting_user' || pipelineStep === 'confirm_framework')
    return '请确认标书框架'
  if (chaptersStep?.status === 'running') {
    let total = 0
    let current = 0
    if (chaptersStep.output_snapshot) {
      try {
        const out = JSON.parse(chaptersStep.output_snapshot) as { total?: number; current?: number }
        total = typeof out.total === 'number' ? out.total : 0
        current = typeof out.current === 'number' ? out.current : 0
      } catch {
        // ignore
      }
    }
    if (total > 0) return `生成第 ${current} 章正文中（共 ${total} 章）`
    return '生成各章正文中…'
  }
  if (reviewStep?.status === 'running') return '正在校审正文'
  if (pipelineStep === 'done' || (chaptersStep?.status === 'completed' && reviewStep?.status === 'completed'))
    return '正在打包 Word 文档'

  return '请稍候…'
}

function parseFrameworkSnapshot(output: string | null): {
  chapters: FrameworkChapter[]
  extra_points: string[]
} {
  if (!output) return { chapters: [], extra_points: [] }
  try {
    const out = JSON.parse(output) as {
      chapters?: FrameworkChapter[]
      extra_points?: string[]
    }
    return {
      chapters: Array.isArray(out.chapters) ? out.chapters : [],
      extra_points: Array.isArray(out.extra_points) ? out.extra_points : [],
    }
  } catch {
    return { chapters: [], extra_points: [] }
  }
}

function derivePhaseFromTask(data: TaskDetail): { phase: Phase; pipelineStep: PipelineStep; errorMessage?: string } {
  const uploadStep = getStep(data, 'upload')
  const extractStep = getStep(data, 'extract')
  const analyzeStep = getStep(data, 'analyze')
  const paramsStep = getStep(data, 'params')
  const frameworkStep = getStep(data, 'framework')
  const chaptersStep = getStep(data, 'chapters')
  const reviewStep = getStep(data, 'review')

  if (!uploadStep || uploadStep.status !== 'completed') return { phase: 'idle', pipelineStep: 'extract' }
  if (extractStep?.status === 'failed') return { phase: 'failed', pipelineStep: 'extract', errorMessage: extractStep.error_message || '解析失败' }
  if (analyzeStep?.status === 'failed') return { phase: 'failed', pipelineStep: 'analyze', errorMessage: analyzeStep.error_message || '分析失败' }
  if (paramsStep?.status === 'failed') return { phase: 'failed', pipelineStep: 'params', errorMessage: paramsStep.error_message || '参数提取失败' }
  if (frameworkStep?.status === 'failed') return { phase: 'failed', pipelineStep: 'framework', errorMessage: frameworkStep.error_message || '框架生成失败' }
  if (chaptersStep?.status === 'failed') return { phase: 'failed', pipelineStep: 'chapters', errorMessage: chaptersStep.error_message || '按章生成失败' }
  if (reviewStep?.status === 'failed') return { phase: 'failed', pipelineStep: 'review', errorMessage: reviewStep.error_message || '校审失败' }
  if (frameworkStep?.status === 'waiting_user') return { phase: 'confirm_framework', pipelineStep: 'confirm_framework' }
  if (reviewStep?.status === 'completed') return { phase: 'done', pipelineStep: 'done' }
  if (chaptersStep?.status === 'completed') return { phase: 'running', pipelineStep: 'review' }
  if (frameworkStep?.status === 'completed') return { phase: 'running', pipelineStep: 'chapters' }
  if (paramsStep?.status === 'completed') return { phase: 'running', pipelineStep: 'framework' }
  if (analyzeStep?.status === 'completed') return { phase: 'running', pipelineStep: 'params' }
  if (extractStep?.status === 'completed') return { phase: 'running', pipelineStep: 'analyze' }
  return { phase: 'running', pipelineStep: 'extract' }
}

export default function OneClickTaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const taskId = id != null ? parseInt(id, 10) : null
  const [phase, setPhase] = useState<Phase>('idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [frameworkModalOpen, setFrameworkModalOpen] = useState(false)
  const [addPointsText, setAddPointsText] = useState('')
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [frameworkActionLoading, setFrameworkActionLoading] = useState(false)
  const pipelineStepRef = useRef<PipelineStep>('extract')
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>('extract')
  const hasSyncedFromTaskRef = useRef(false)

  const { data: taskData, isFetching, isError, refetch: refetchTask } = useQuery({
    queryKey: ['task', id ?? ''],
    queryFn: () => getTask(id!),
    enabled: !!id,
    refetchInterval:
      !!id && (phase === 'running' || phase === 'confirm_framework') ? POLL_INTERVAL_MS : false,
  })

  useEffect(() => {
    if (id == null) return
    hasSyncedFromTaskRef.current = false
  }, [id])

  useEffect(() => {
    if (!taskData || taskId == null || hasSyncedFromTaskRef.current) return
    if (id != null && typeof sessionStorage !== 'undefined' && sessionStorage.getItem(getCancelledStorageKey(id))) {
      hasSyncedFromTaskRef.current = true
      setPhase('cancelled')
      return
    }
    const { phase: p, pipelineStep: s, errorMessage: err } = derivePhaseFromTask(taskData)
    hasSyncedFromTaskRef.current = true
    setPhase(p)
    setPipelineStep(s)
    pipelineStepRef.current = s
    if (err) setErrorMessage(err)
    if (p === 'confirm_framework') setFrameworkModalOpen(true)
  }, [taskData, taskId, id])

  useEffect(() => {
    if (!taskData || taskId == null || (phase !== 'running' && phase !== 'confirm_framework')) return
    const step = pipelineStepRef.current
    const extractStep = getStep(taskData, 'extract')
    const analyzeStep = getStep(taskData, 'analyze')
    const paramsStep = getStep(taskData, 'params')
    const frameworkStep = getStep(taskData, 'framework')
    const chaptersStep = getStep(taskData, 'chapters')
    const reviewStep = getStep(taskData, 'review')

    if (extractStep?.status === 'failed') {
      setErrorMessage(extractStep.error_message || '解析失败')
      setPhase('failed')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
      return
    }
    if (analyzeStep?.status === 'failed') {
      setErrorMessage(analyzeStep.error_message || '分析失败')
      setPhase('failed')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
      return
    }
    if (paramsStep?.status === 'failed') {
      setErrorMessage(paramsStep.error_message || '参数提取失败')
      setPhase('failed')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
      return
    }
    if (frameworkStep?.status === 'failed') {
      setErrorMessage(frameworkStep.error_message || '框架生成失败')
      setPhase('failed')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
      return
    }
    if (chaptersStep?.status === 'failed') {
      setErrorMessage(chaptersStep.error_message || '按章生成失败')
      setPhase('failed')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
      return
    }
    if (reviewStep?.status === 'failed') {
      setErrorMessage(reviewStep.error_message || '校审失败')
      setPhase('failed')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
      return
    }

    if (step === 'extract' && extractStep?.status === 'completed') {
      setPipelineStep('analyze')
      pipelineStepRef.current = 'analyze'
      runAnalyzeStep(String(taskId)).catch((e) => {
        setErrorMessage(e instanceof Error ? e.message : '分析入队失败')
        setPhase('failed')
      })
      return
    }
    if (step === 'analyze' && analyzeStep?.status === 'completed') {
      setPipelineStep('params')
      pipelineStepRef.current = 'params'
      runParamsStep(String(taskId)).catch((e) => {
        setErrorMessage(e instanceof Error ? e.message : '参数入队失败')
        setPhase('failed')
      })
      return
    }
    if (step === 'params' && paramsStep?.status === 'completed') {
      setPipelineStep('framework')
      pipelineStepRef.current = 'framework'
      runFrameworkStep(String(taskId)).catch((e) => {
        setErrorMessage(e instanceof Error ? e.message : '框架入队失败')
        setPhase('failed')
      })
      return
    }
    if (step === 'framework' && frameworkStep?.status === 'waiting_user') {
      setPhase('confirm_framework')
      setPipelineStep('confirm_framework')
      pipelineStepRef.current = 'confirm_framework'
      setFrameworkModalOpen(true)
      return
    }
    if (step === 'chapters' && chaptersStep?.status === 'completed') {
      setPipelineStep('review')
      pipelineStepRef.current = 'review'
      runReview(String(taskId)).catch((e) => {
        setErrorMessage(e instanceof Error ? e.message : '校审入队失败')
        setPhase('failed')
      })
      return
    }
    if (step === 'review' && reviewStep?.status === 'completed') {
      setPipelineStep('done')
      pipelineStepRef.current = 'done'
      setPhase('done')
      if (id != null) sessionStorage.removeItem(getCancelledStorageKey(id))
    }
  }, [taskData, taskId, phase, id])

  useEffect(() => {
    if (phase !== 'confirm_framework' || !taskData) return
    const frameworkStep = getStep(taskData, 'framework')
    if (frameworkStep?.status === 'waiting_user') setFrameworkModalOpen(true)
  }, [phase, taskData])

  const handleStart = async () => {
    if (!id || !selectedFile) {
      message.warning('请选择招标文件')
      return
    }
    setErrorMessage(null)
    setPhase('uploading')
    try {
      await uploadTaskFile(id, selectedFile)
      await runExtractStep(id)
      setPhase('running')
      setPipelineStep('extract')
      pipelineStepRef.current = 'extract'
      queryClient.invalidateQueries({ queryKey: ['task', id] })
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail != null
          ? String((e as { response: { data: { detail: unknown } } }).response.data.detail)
          : e instanceof Error
            ? e.message
            : '上传或解析失败'
      setErrorMessage(detail)
      setPhase('failed')
    }
  }

  const handleAcceptFramework = async () => {
    if (!id || frameworkActionLoading) return
    const points = addPointsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    setFrameworkActionLoading(true)
    try {
      await acceptFrameworkStep(id, points)
      setFrameworkModalOpen(false)
      setAddPointsText('')
      setPhase('running')
      setPipelineStep('chapters')
      pipelineStepRef.current = 'chapters'
      await runChaptersStep(id)
      queryClient.invalidateQueries({ queryKey: ['task', id] })
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail != null
          ? String((e as { response: { data: { detail: unknown } } }).response.data.detail)
          : e instanceof Error
            ? e.message
            : '接受失败'
      message.error(detail)
    } finally {
      setFrameworkActionLoading(false)
    }
  }

  const handleSaveFrameworkPoints = async () => {
    if (!id || frameworkActionLoading) return
    const points = addPointsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    setFrameworkActionLoading(true)
    try {
      await saveFrameworkPoints(id, points)
      message.success('已保存要点')
      setAddPointsText('')
      queryClient.invalidateQueries({ queryKey: ['task', id] })
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail != null
          ? String((e as { response: { data: { detail: unknown } } }).response.data.detail)
          : e instanceof Error
            ? e.message
            : '保存失败'
      message.error(detail)
    } finally {
      setFrameworkActionLoading(false)
    }
  }

  const handleRegenerateFramework = async () => {
    if (!id || frameworkActionLoading) return
    setFrameworkActionLoading(true)
    try {
      await regenerateFrameworkStep(id)
      setFrameworkModalOpen(false)
      setPhase('running')
      setPipelineStep('framework')
      pipelineStepRef.current = 'framework'
      queryClient.invalidateQueries({ queryKey: ['task', id] })
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail != null
          ? String((e as { response: { data: { detail: unknown } } }).response.data.detail)
          : e instanceof Error
            ? e.message
            : '重新生成失败'
      message.error(detail)
    } finally {
      setFrameworkActionLoading(false)
    }
  }

  const handleCancel = async () => {
    if (id == null) return
    try {
      await cancelTask(id)
    } catch {
      message.warning('取消请求未生效，请稍后重试')
    }
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(getCancelledStorageKey(id), '1')
    }
    setPhase('cancelled')
    setFrameworkModalOpen(false)
    queryClient.invalidateQueries({ queryKey: ['task', id] })
    message.info('已取消生成')
  }

  const handleResume = async () => {
    if (!id) return
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem(getCancelledStorageKey(id))
    }
    try {
      const { data: latest } = await refetchTask()
      if (!latest) {
        message.error('无法获取任务状态')
        return
      }
      const ext = getStep(latest, 'extract')
      const an = getStep(latest, 'analyze')
      const pa = getStep(latest, 'params')
      const fw = getStep(latest, 'framework')
      const ch = getStep(latest, 'chapters')
      const rv = getStep(latest, 'review')
      if (ext?.status === 'completed' && (!an || an.status === 'pending' || an.status === 'failed')) {
        await runAnalyzeStep(id)
        setPipelineStep('analyze')
        pipelineStepRef.current = 'analyze'
      } else if (an?.status === 'completed' && (!pa || pa.status === 'pending' || pa.status === 'failed')) {
        await runParamsStep(id)
        setPipelineStep('params')
        pipelineStepRef.current = 'params'
      } else if (pa?.status === 'completed' && (!fw || fw.status === 'pending' || fw.status === 'failed')) {
        await runFrameworkStep(id)
        setPipelineStep('framework')
        pipelineStepRef.current = 'framework'
      } else if (fw?.status === 'waiting_user') {
        setPhase('confirm_framework')
        setPipelineStep('confirm_framework')
        pipelineStepRef.current = 'confirm_framework'
        setFrameworkModalOpen(true)
        return
      } else if (fw?.status === 'completed' && (!ch || ch.status === 'pending' || ch.status === 'failed')) {
        await runChaptersStep(id)
        setPipelineStep('chapters')
        pipelineStepRef.current = 'chapters'
      } else if (ch?.status === 'completed' && (!rv || rv.status === 'pending' || rv.status === 'failed')) {
        await runReview(id)
        setPipelineStep('review')
        pipelineStepRef.current = 'review'
      } else {
        message.info('当前无需继续，或请刷新后重试')
        return
      }
      setPhase('running')
      queryClient.invalidateQueries({ queryKey: ['task', id] })
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail != null
          ? String((e as { response: { data: { detail: unknown } } }).response.data.detail)
          : e instanceof Error
            ? e.message
            : '继续失败'
      message.error(detail)
    }
  }

  const handleDownload = async () => {
    if (!id) return
    setDownloadLoading(true)
    const hide = message.loading('正在生成 Word 文档…', 0)
    try {
      const blob = await downloadTaskDocx(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `标书_任务${id}.docx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('下载已开始')
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail != null
          ? String((e as { response: { data: { detail: unknown } } }).response.data.detail)
          : e instanceof Error
            ? e.message
            : '下载失败'
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
        <Link to="/one-click" style={{ marginLeft: 16 }}>返回任务列表</Link>
      </>
    )
  }

  if (isError) {
    return (
      <>
        <Text type="danger">任务不存在或加载失败</Text>
        <Link to="/one-click" style={{ marginLeft: 16 }}>返回任务列表</Link>
      </>
    )
  }

  const frameworkStep = getStep(taskData, 'framework')
  const { chapters: frameworkChapters, extra_points: frameworkExtraPoints } = parseFrameworkSnapshot(
    frameworkStep?.output_snapshot ?? null
  )
  const statusLabel = getStatusLabel(phase, taskData, pipelineStep)

  return (
    <>
      <div style={{ marginBottom: designTokens.marginLG }}>
        <Link to="/one-click">← 返回任务列表</Link>
      </div>
      <Title level={2} style={{ marginBottom: designTokens.marginLG }}>
        {taskData?.name || '一键生成任务'}
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginLG }}>
        上传招标文件后自动完成解析、分析、框架与正文生成，仅需在生成框架后确认一次即可。
      </Text>
      {taskData && (
        <div style={{ marginBottom: designTokens.marginMD }}>
          <Text strong>当前语义配置：</Text>
          <Text>
            {taskData.profile_id != null
              ? taskData.profile_name || `配置 #${taskData.profile_id}`
              : 'BIM技术标（内置）'}
          </Text>
        </div>
      )}

      {phase === 'idle' && (
        <div style={{ marginBottom: designTokens.marginLG, maxWidth: 520 }}>
          <div style={{ marginBottom: designTokens.marginSM }}>
            <Text type="secondary">招标文件（PDF / Word）：</Text>
          </div>
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            style={{ marginBottom: designTokens.marginSM, display: 'block' }}
          />
          <Button type="primary" size="large" onClick={handleStart} disabled={!selectedFile}>
            开始生成
          </Button>
        </div>
      )}

      {(phase === 'uploading' || phase === 'running' || phase === 'confirm_framework') && (
        <div
          style={{
            padding: designTokens.paddingLG,
            background: designTokens.colorBgLayout,
            borderRadius: designTokens.borderRadius,
            marginBottom: designTokens.marginLG,
            maxWidth: 560,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: designTokens.marginSM }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: designTokens.marginSM }}>
              {(phase === 'running' || phase === 'uploading') && (isFetching || phase === 'uploading') && (
                <Spin size="small" />
              )}
              <Text strong>{statusLabel}</Text>
            </div>
            <Button danger onClick={handleCancel}>
              取消生成
            </Button>
          </div>
        </div>
      )}

      {phase === 'cancelled' && (
        <Alert
          type="info"
          message="已取消生成"
          description="当前任务的自动生成已中断。您可以点击「继续生成」从当前进度继续，或到高级生成中分步操作。"
          showIcon
          style={{ marginBottom: designTokens.marginLG, maxWidth: 560 }}
          action={
            <span style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              <Button type="primary" onClick={handleResume}>
                继续生成
              </Button>
              <Link to="/one-click">
                <Button>返回任务列表</Button>
              </Link>
              <Link to={`/tasks/${id}`}>
                <Button>在高级生成中查看</Button>
              </Link>
            </span>
          }
        />
      )}

      {phase === 'failed' && errorMessage && (
        <Alert
          type="error"
          message="生成失败"
          description={errorMessage}
          showIcon
          style={{ marginBottom: designTokens.marginLG, maxWidth: 560 }}
          action={
            <span style={{ display: 'flex', gap: 8 }}>
              <Button
                size="small"
                onClick={() => {
                  setPhase('idle')
                  setErrorMessage(null)
                  setSelectedFile(null)
                }}
              >
                重新上传
              </Button>
              <Link to="/one-click">
                <Button size="small">返回任务列表</Button>
              </Link>
              <Link to={`/tasks/${id}`}>
                <Button size="small">在高级生成中继续</Button>
              </Link>
            </span>
          }
        />
      )}

      {phase === 'done' && (
        <div style={{ marginBottom: designTokens.marginLG }}>
          <Button
            type="primary"
            size="large"
            loading={downloadLoading}
            onClick={handleDownload}
            style={{ marginRight: designTokens.marginSM }}
          >
            下载 Word
          </Button>
          <Link to={`/tasks/${id}`}>
            <Button size="large">在高级生成中查看</Button>
          </Link>
          <Link to="/one-click">
            <Button size="large">返回任务列表</Button>
          </Link>
        </div>
      )}

      <Modal
        title="确认标书框架"
        open={frameworkModalOpen}
        onCancel={() => {}}
        footer={null}
        width={640}
        maskClosable={false}
        closable={false}
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
          请查阅生成的章节框架，可添加要点或重新生成，确认后将继续自动生成正文与校审。
        </Text>
        {frameworkChapters.length > 0 && (
          <ul
            style={{
              marginBottom: designTokens.marginLG,
              paddingLeft: 20,
              maxHeight: 320,
              overflow: 'auto',
            }}
          >
            {frameworkChapters.map((ch, i) => (
              <li key={i}>
                <Text strong>第{ch.number}章</Text> {ch.title}
                {Array.isArray(ch.sections) && ch.sections.length > 0 && (
                  <ul style={{ marginBottom: 0, paddingLeft: 20, marginTop: 4 }}>
                    {ch.sections.map((sec, j) => (
                      <li key={j}>
                        {sec.number} {sec.title}
                        {Array.isArray(sec.subsections) &&
                          sec.subsections.length > 0 && (
                            <ul style={{ marginBottom: 0, paddingLeft: 20, marginTop: 2 }}>
                              {sec.subsections.map((sub, k) => (
                                <li key={k}>
                                  {sub.number} {sub.title}
                                </li>
                              ))}
                            </ul>
                          )}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
        {frameworkExtraPoints.length > 0 && (
          <div style={{ marginBottom: designTokens.marginSM }}>
            <Text type="secondary">已添加要点：</Text>
            <ul style={{ paddingLeft: 20, marginTop: 4 }}>
              {frameworkExtraPoints.map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          </div>
        )}
        <div style={{ marginBottom: designTokens.marginSM }}>
          <Text type="secondary">补充要点（每行一条，可选）：</Text>
          <Input.TextArea
            rows={3}
            value={addPointsText}
            onChange={(e) => setAddPointsText(e.target.value)}
            placeholder="可输入希望框架中体现的要点，保存后再重新生成框架；或直接接受并继续。"
            style={{ marginTop: 4 }}
          />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <Button
            type="primary"
            loading={frameworkActionLoading}
            onClick={handleAcceptFramework}
          >
            接受并继续
          </Button>
          <Button
            loading={frameworkActionLoading}
            onClick={handleSaveFrameworkPoints}
          >
            保存要点
          </Button>
          <Button
            loading={frameworkActionLoading}
            onClick={handleRegenerateFramework}
          >
            重新生成框架
          </Button>
        </div>
      </Modal>
    </>
  )
}
