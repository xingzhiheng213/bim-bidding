import { useState, useMemo, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Alert, Button, Checkbox, Collapse, message, Modal, Select, Spin, Tag, Typography } from 'antd'
import { getChaptersDiff } from '../api/compare'
import { getTask, runReview, acceptReview, regenerateAllChaptersFromReview, type TaskDetail, type TaskStep } from '../api/tasks'
import { DiffView } from '../components/DiffView'
import { designTokens } from '../theme/tokens'
import { getStepStatusLabel, type StepStatus } from '../theme/stepStatus'
import '../App.css'

const { Title, Text } = Typography

export interface ReviewItem {
  type: string
  description: string
  quote: string
}

interface ReviewOutputSnapshot {
  chapters?: Record<string, unknown[]>
}

function parseReviewChapters(outputSnapshot: string | null): Record<string, ReviewItem[]> {
  if (!outputSnapshot || typeof outputSnapshot !== 'string') return {}
  try {
    const data = JSON.parse(outputSnapshot) as ReviewOutputSnapshot
    const chapters = data?.chapters
    if (!chapters || typeof chapters !== 'object') return {}
    const out: Record<string, ReviewItem[]> = {}
    for (const [num, arr] of Object.entries(chapters)) {
      if (!Array.isArray(arr)) continue
      out[num] = arr.map((item) => {
        const o = item && typeof item === 'object' ? item as Record<string, unknown> : {}
        return {
          type: typeof o.type === 'string' ? o.type : '',
          description: typeof o.description === 'string' ? o.description : (o.description != null ? String(o.description) : ''),
          quote: typeof o.quote === 'string' ? o.quote : (o.quote != null ? String(o.quote) : ''),
        }
      })
    }
    return out
  } catch {
    return {}
  }
}

function getTagColorForType(type: string): 'default' | 'processing' | 'success' | 'warning' | 'error' {
  if (type === '废标项') return 'error'
  if (type === '幻觉') return 'warning'
  if (type === '套路') return 'default'
  if (type === '建议') return 'processing'
  return 'default'
}

function ReviewTaskPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const queryClient = useQueryClient()

  const [acceptModalOpen, setAcceptModalOpen] = useState(false)
  const [acceptModalChapterNumber, setAcceptModalChapterNumber] = useState<number | null>(null)
  const [acceptModalItems, setAcceptModalItems] = useState<ReviewItem[]>([])
  const [acceptModalSelected, setAcceptModalSelected] = useState<string[]>([])
  /** 刚接受并重生成的章节号，用于显示「正在重生成」/「重生成完成」及持续轮询 */
  const [lastAcceptedChapterNumber, setLastAcceptedChapterNumber] = useState<number | null>(null)
  /** 接受提交时间戳，90 秒内持续轮询以便拿到 chapters running -> completed */
  const [acceptSubmittedAt, setAcceptSubmittedAt] = useState<number | null>(null)
  /** 本会话内已接受并重生成的章节号，用于展示「已采纳并重生成」说明 */
  const [acceptedChapterNumbersInSession, setAcceptedChapterNumbersInSession] = useState<number[]>([])
  /** 预览「第 N 章新内容」的章节号，非空时打开预览 Modal */
  const [previewChapterNumber, setPreviewChapterNumber] = useState<number | null>(null)
  /** 是否已见过 chapters 为 running（用于仅在实际重生成完成后再显示「重生成完成」） */
  const [hasChaptersBeenRunningSinceAccept, setHasChaptersBeenRunningSinceAccept] = useState(false)
  /** 预览弹窗内「对比原文」数据 */
  const [previewDiffLoading, setPreviewDiffLoading] = useState(false)
  const [previewDiffError, setPreviewDiffError] = useState<string | null>(null)
  const [previewDiffData, setPreviewDiffData] = useState<{ original: string; modified: string; diff: { type: 'equal' | 'add' | 'del'; text: string }[] } | null>(null)
  /** 校审范围：'all' 全部章节，或具体章节号 */
  const [reviewScope, setReviewScope] = useState<'all' | number>('all')
  /** 一键重生成全部提交时间戳，90 秒内持续轮询 */
  const [regenerateAllSubmittedAt, setRegenerateAllSubmittedAt] = useState<number | null>(null)
  const acceptPollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const regenerateAllPollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    data: task,
    isLoading: taskLoading,
    isError: taskError,
  } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const d = query.state.data as TaskDetail | undefined
      const reviewStep = d?.steps?.find((s: TaskStep) => s.step_key === 'review')
      const chaptersStep = d?.steps?.find((s: TaskStep) => s.step_key === 'chapters')
      if (reviewStep?.status === 'running' || chaptersStep?.status === 'running') return 2000
      if (lastAcceptedChapterNumber != null && acceptSubmittedAt != null && Date.now() - acceptSubmittedAt < 90000) return 2000
      if (regenerateAllSubmittedAt != null && Date.now() - regenerateAllSubmittedAt < 90000) return 2000
      return false
    },
  })

  const runReviewMutation = useMutation({
    mutationFn: ({ taskId: tid, chapterNumber }: { taskId: string; chapterNumber?: number }) =>
      runReview(tid, chapterNumber),
    onSuccess: async (_, { taskId: tid, chapterNumber }) => {
      message.success(chapterNumber != null ? '单章审查已入队，请稍候…' : '审查已入队，请稍候…')
      await queryClient.invalidateQueries({ queryKey: ['task', tid] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '审查入队失败'
      message.error(detail)
    },
  })

  const acceptReviewMutation = useMutation({
    mutationFn: ({ tid, chapterNumber, acceptedItems }: { tid: string; chapterNumber: number; acceptedItems: string[] }) =>
      acceptReview(tid, chapterNumber, acceptedItems),
    onSuccess: async (_, { tid, chapterNumber }) => {
      message.success('该章已加入重生成队列，页面将自动更新重生成状态。')
      setAcceptModalOpen(false)
      setAcceptModalChapterNumber(null)
      setAcceptModalItems([])
      setAcceptModalSelected([])
      setLastAcceptedChapterNumber(chapterNumber)
      setAcceptSubmittedAt(Date.now())
      setAcceptedChapterNumbersInSession((prev) => (prev.includes(chapterNumber) ? prev : [...prev, chapterNumber]))
      await queryClient.invalidateQueries({ queryKey: ['task', tid] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '接受校审意见失败'
      message.error(detail)
    },
  })

  const regenerateAllMutation = useMutation({
    mutationFn: (tid: string) => regenerateAllChaptersFromReview(tid),
    onSuccess: async (_, tid) => {
      message.success('已入队，将按章顺序重生成全部章节，页面将自动更新。')
      setRegenerateAllSubmittedAt(Date.now())
      await queryClient.invalidateQueries({ queryKey: ['task', tid] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '一键重生成失败'
      message.error(detail)
    },
  })

  const chaptersStep = task?.steps?.find((s) => s.step_key === 'chapters')
  const reviewStep = task?.steps?.find((s) => s.step_key === 'review')
  const chaptersCompleted = chaptersStep?.status === 'completed' && !!chaptersStep?.output_snapshot
  const canStartReview = chaptersCompleted && (!reviewStep || reviewStep.status === 'pending' || reviewStep.status === 'failed')
  const reviewRunning = reviewStep?.status === 'running'
  const reviewCompleted = reviewStep?.status === 'completed'
  const reviewFailed = reviewStep?.status === 'failed'
  const reviewStatusLabel = reviewStep ? getStepStatusLabel((reviewStep.status as StepStatus) || 'pending') : '待审查'

  const reviewChapters = useMemo(() => {
    if (!reviewStep?.output_snapshot || !reviewCompleted) return {}
    return parseReviewChapters(reviewStep.output_snapshot)
  }, [reviewStep?.output_snapshot, reviewCompleted])

  const sortedChapterNumbers = useMemo(
    () => Object.keys(reviewChapters).sort((a, b) => parseInt(a, 10) - parseInt(b, 10)),
    [reviewChapters],
  )

  /** 从任务 chapters 步骤解析出的章节正文，用于「查看新内容」预览 */
  const chaptersContentFromTask = useMemo(() => {
    const step = task?.steps?.find((s) => s.step_key === 'chapters')
    if (!step?.output_snapshot) return {}
    try {
      const out = JSON.parse(step.output_snapshot) as { chapters?: Record<string, string> }
      return out.chapters && typeof out.chapters === 'object' ? out.chapters : {}
    } catch {
      return {}
    }
  }, [task?.steps])

  /** 已采纳并重生成的章节号（从服务端 chapter_points 解析，切换页面后仍保持） */
  const acceptedChapterNumbersFromServer = useMemo(() => {
    const step = task?.steps?.find((s) => s.step_key === 'chapters')
    if (!step?.output_snapshot) return []
    try {
      const out = JSON.parse(step.output_snapshot) as { chapter_points?: Record<string, unknown> }
      const cp = out.chapter_points
      if (!cp || typeof cp !== 'object') return []
      return Object.keys(cp)
        .map((k) => parseInt(k, 10))
        .filter((n) => !Number.isNaN(n))
    } catch {
      return []
    }
  }, [task?.steps])

  /** 可用于单章校审的章节号列表（chapters 完成后从 output 解析） */
  const availableChapterNumbers = useMemo(() => {
    const keys = Object.keys(chaptersContentFromTask)
    if (keys.length === 0) return []
    return keys.map((k) => parseInt(k, 10)).filter((n) => !Number.isNaN(n)).sort((a, b) => a - b)
  }, [chaptersContentFromTask])

  useEffect(() => {
    if (acceptSubmittedAt == null) return
    acceptPollingTimeoutRef.current = setTimeout(() => {
      setLastAcceptedChapterNumber(null)
      setAcceptSubmittedAt(null)
      setHasChaptersBeenRunningSinceAccept(false)
      acceptPollingTimeoutRef.current = null
    }, 90000)
    return () => {
      if (acceptPollingTimeoutRef.current) clearTimeout(acceptPollingTimeoutRef.current)
    }
  }, [acceptSubmittedAt])

  useEffect(() => {
    if (regenerateAllSubmittedAt == null) return
    regenerateAllPollingTimeoutRef.current = setTimeout(() => {
      setRegenerateAllSubmittedAt(null)
      regenerateAllPollingTimeoutRef.current = null
    }, 90000)
    return () => {
      if (regenerateAllPollingTimeoutRef.current) clearTimeout(regenerateAllPollingTimeoutRef.current)
    }
  }, [regenerateAllSubmittedAt])

  useEffect(() => {
    if (chaptersStep?.status === 'running' && lastAcceptedChapterNumber != null) {
      setHasChaptersBeenRunningSinceAccept(true)
    }
  }, [chaptersStep?.status, lastAcceptedChapterNumber])

  const openAcceptModal = (chapterNumber: number) => {
    const items = reviewChapters[String(chapterNumber)] ?? []
    setAcceptModalChapterNumber(chapterNumber)
    setAcceptModalItems(items)
    setAcceptModalSelected(items.map((i) => i.description))
    setAcceptModalOpen(true)
  }

  const handleAcceptModalOk = () => {
    if (!taskId || acceptModalChapterNumber == null) return
    if (acceptModalSelected.length === 0) {
      message.warning('请至少选择一项校审意见')
      return
    }
    acceptReviewMutation.mutate({
      tid: taskId,
      chapterNumber: acceptModalChapterNumber,
      acceptedItems: acceptModalSelected,
    })
  }

  const selectAllAccept = () => setAcceptModalSelected(acceptModalItems.map((i) => i.description))
  const deselectAllAccept = () => setAcceptModalSelected([])

  const handleViewNewContent = (chapterNum: number) => {
    setPreviewChapterNumber(chapterNum)
    setPreviewDiffData(null)
    setPreviewDiffError(null)
    setLastAcceptedChapterNumber(null)
    setAcceptSubmittedAt(null)
    setHasChaptersBeenRunningSinceAccept(false)
    if (acceptPollingTimeoutRef.current) {
      clearTimeout(acceptPollingTimeoutRef.current)
      acceptPollingTimeoutRef.current = null
    }
  }

  const handlePreviewCompare = () => {
    if (!taskId || previewChapterNumber == null) return
    setPreviewDiffLoading(true)
    setPreviewDiffError(null)
    getChaptersDiff(taskId, previewChapterNumber)
      .then((res) => setPreviewDiffData({ original: res.original, modified: res.modified, diff: res.diff }))
      .catch((e: unknown) => {
        const detail =
          e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
            ? String((e.response.data as { detail: unknown }).detail)
            : e instanceof Error ? e.message : '加载对比失败'
        setPreviewDiffError(detail)
      })
      .finally(() => setPreviewDiffLoading(false))
  }

  if (!taskId) {
    return (
      <div style={{ padding: designTokens.marginLG }}>
        <Alert type="warning" message="缺少任务 ID" />
        <Link to="/review" style={{ display: 'inline-block', marginTop: designTokens.marginSM }}>
          返回校审列表
        </Link>
      </div>
    )
  }

  if (taskLoading || !task) {
    return (
      <div style={{ padding: designTokens.marginLG, textAlign: 'center' }}>
        <Spin tip="加载任务…" size="large" />
        <div style={{ marginTop: designTokens.marginLG }}>
          <Link to="/review">返回校审列表</Link>
        </div>
      </div>
    )
  }

  if (taskError) {
    return (
      <div style={{ padding: designTokens.marginLG }}>
        <Alert type="error" message="加载任务失败" />
        <Link to="/review" style={{ display: 'inline-block', marginTop: designTokens.marginSM }}>
          返回校审列表
        </Link>
      </div>
    )
  }

  return (
    <>
      <div style={{ marginBottom: designTokens.marginLG }}>
        <Link to="/review" style={{ marginRight: designTokens.marginMD }}>
          返回校审列表
        </Link>
      </div>
      <Title level={2} style={{ marginBottom: designTokens.marginSM }}>
        任务 #{task.id} 校审
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginLG }}>
        对按章生成结果进行审查，识别废标项、幻觉与套路等；审查完成后可按章查看校审意见，勾选采纳项后触发该章重生成。
      </Text>

      {!chaptersCompleted && (
        <Alert
          type="info"
          message="请先完成按章生成"
          description="该任务尚未完成按章生成，无法开始审查。请先在任务详情页完成「按章生成」步骤。"
          style={{ marginBottom: designTokens.marginLG }}
        />
      )}

      {chaptersCompleted && !reviewRunning && (
        <div style={{ marginBottom: designTokens.marginLG }}>
          <Text type="secondary" style={{ marginRight: designTokens.marginSM }}>校审范围：</Text>
          <Select<'all' | number>
            value={reviewScope}
            onChange={(v) => setReviewScope(v ?? 'all')}
            style={{ width: 160, marginRight: designTokens.marginSM }}
            options={[
              { label: '全部章节', value: 'all' },
              ...availableChapterNumbers.map((n) => ({ label: `第 ${n} 章`, value: n })),
            ]}
          />
          <Button
            type="primary"
            loading={runReviewMutation.isPending}
            onClick={() =>
              runReviewMutation.mutate({
                taskId,
                chapterNumber: reviewScope === 'all' ? undefined : reviewScope,
              })
            }
          >
            自动校审
          </Button>
        </div>
      )}

      {chaptersCompleted && reviewRunning && (
        <Alert
          type="info"
          message="审查进行中"
          description="正在逐章审查，请稍候…"
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {chaptersCompleted && reviewCompleted && (
        <Alert
          type="success"
          message="审查已完成"
          description="下方按章展示校审意见，可勾选采纳项后点击「接受并重生成」触发该章重写；或使用「一键按校审意见重生成全部章节」顺序重写全部。"
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {chaptersCompleted && reviewCompleted && sortedChapterNumbers.length > 0 && chaptersStep?.status !== 'running' && (
        <div style={{ marginBottom: designTokens.marginLG }}>
          <Button
            type="primary"
            loading={regenerateAllMutation.isPending}
            onClick={() => taskId && regenerateAllMutation.mutate(taskId)}
          >
            一键按校审意见重生成全部章节
          </Button>
        </div>
      )}

      {chaptersCompleted && reviewCompleted && sortedChapterNumbers.length > 0 && (
        <Collapse
          defaultActiveKey={sortedChapterNumbers.length > 0 ? [sortedChapterNumbers[0]] : []}
          style={{ marginBottom: designTokens.marginLG }}
          items={sortedChapterNumbers.map((num) => {
            const items = reviewChapters[num] ?? []
            const numInt = parseInt(num, 10)
            const isRegenerating = numInt === lastAcceptedChapterNumber && chaptersStep?.status === 'running'
            const isRegenerateDone = numInt === lastAcceptedChapterNumber && chaptersStep?.status === 'completed' && hasChaptersBeenRunningSinceAccept
            const statusSuffix = isRegenerating ? '（正在重生成…）' : isRegenerateDone ? '（重生成完成）' : (items.length > 0 ? `（${items.length} 条校审意见）` : '')
            const isAccepted =
              acceptedChapterNumbersFromServer.includes(numInt) || acceptedChapterNumbersInSession.includes(numInt)
            return {
              key: num,
              label: `第 ${num} 章` + statusSuffix,
              children: (
                <div>
                  {isAccepted && (
                    <Alert
                      type="success"
                      message="已采纳并重生成"
                      description="以下校审意见已采纳并已重生成本章（为重生成前的审查结果）。"
                      showIcon
                      style={{ marginBottom: designTokens.marginMD }}
                    />
                  )}
                  {items.length === 0 ? (
                    <Text type="secondary">本章无校审意见。</Text>
                  ) : (
                    <>
                      <ul
                        style={{
                          listStyle: 'none',
                          paddingLeft: 0,
                          marginBottom: designTokens.marginMD,
                          ...(isAccepted ? { opacity: 0.65 } : {}),
                        }}
                      >
                        {items.map((item, idx) => (
                          <li
                            key={idx}
                            style={{
                              marginBottom: designTokens.marginSM,
                              padding: designTokens.marginSM,
                              background: 'rgba(0,0,0,0.02)',
                              borderRadius: 4,
                              ...(isAccepted ? { textDecoration: 'line-through' } : {}),
                            }}
                          >
                            <Tag color={getTagColorForType(item.type)} style={{ marginRight: 8 }}>
                              {item.type || '建议'}
                            </Tag>
                            <Text style={isAccepted ? { color: 'rgba(0,0,0,0.5)' } : undefined}>{item.description}</Text>
                            {item.quote && (
                              <div style={{ marginTop: 4 }}>
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  原文引用：{item.quote}
                                </Text>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <Button type="primary" onClick={() => openAcceptModal(numInt)}>
                          接受并重生成
                        </Button>
                        {isAccepted && chaptersCompleted && (
                          <Button
                            onClick={() => {
                              setPreviewChapterNumber(numInt)
                              setPreviewDiffData(null)
                              setPreviewDiffError(null)
                            }}
                          >
                            查看修改后章节内容
                          </Button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ),
            }
          })}
        />
      )}

      {chaptersCompleted && reviewFailed && reviewStep?.error_message && (
        <Alert
          type="error"
          message="审查失败"
          description={reviewStep.error_message}
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {chaptersCompleted && chaptersStep?.status === 'running' && lastAcceptedChapterNumber != null && (
        <Alert
          type="info"
          message={`第 ${lastAcceptedChapterNumber} 章正在重生成…`}
          description="已接受的校审意见正在应用于该章重写，请稍候。"
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {chaptersCompleted && chaptersStep?.status === 'completed' && lastAcceptedChapterNumber != null && hasChaptersBeenRunningSinceAccept && (
        <Alert
          type="success"
          message={`第 ${lastAcceptedChapterNumber} 章重生成完成`}
          description={
            <span>
              该章已根据校审意见重写完成，可在上方该章面板点击「查看修改后章节内容」查看。{' '}
              <Button type="link" size="small" style={{ padding: 0 }} onClick={() => handleViewNewContent(lastAcceptedChapterNumber)}>
                立即查看第 {lastAcceptedChapterNumber} 章新内容
              </Button>
            </span>
          }
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {chaptersCompleted && chaptersStep?.status === 'running' && lastAcceptedChapterNumber == null && (
        <Alert
          type="info"
          message="章节重生成进行中"
          description={
            regenerateAllSubmittedAt != null
              ? '正在按校审意见顺序重生成全部章节，请稍候…'
              : '已接受的校审意见正在应用于该章重写，请稍候…'
          }
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {chaptersCompleted && reviewStep && !reviewCompleted && !reviewRunning && (
        <Text type="secondary">
          当前审查状态：{reviewStatusLabel}
        </Text>
      )}

      <Modal
        title={acceptModalChapterNumber != null ? `第 ${acceptModalChapterNumber} 章 — 接受校审意见并重生成` : '接受校审意见'}
        open={acceptModalOpen}
        onCancel={() => {
          setAcceptModalOpen(false)
          setAcceptModalChapterNumber(null)
          setAcceptModalItems([])
          setAcceptModalSelected([])
        }}
        onOk={handleAcceptModalOk}
        okText="确认"
        cancelText="取消"
        confirmLoading={acceptReviewMutation.isPending}
        okButtonProps={{ disabled: acceptModalSelected.length === 0 }}
      >
        <div style={{ marginBottom: designTokens.marginSM }}>
          <Button type="link" size="small" onClick={selectAllAccept}>
            全选
          </Button>
          <Button type="link" size="small" onClick={deselectAllAccept}>
            取消全选
          </Button>
        </div>
        <Checkbox.Group
          style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}
          value={acceptModalSelected}
          onChange={(vals) => setAcceptModalSelected(vals as string[])}
        >
          {acceptModalItems.map((item, idx) => (
            <div key={idx} style={{ padding: 8, background: 'rgba(0,0,0,0.02)', borderRadius: 4 }}>
              <Checkbox value={item.description}>
                <Tag color={getTagColorForType(item.type)}>{item.type || '建议'}</Tag>
                {item.description}
                {item.quote && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {item.quote}
                    </Text>
                  </div>
                )}
              </Checkbox>
            </div>
          ))}
        </Checkbox.Group>
        {acceptModalSelected.length === 0 && acceptModalItems.length > 0 && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            请至少选择一项校审意见后确认。
          </Text>
        )}
      </Modal>

      <Modal
        title={previewChapterNumber != null ? `第 ${previewChapterNumber} 章 修改后内容` : '章节内容'}
        open={previewChapterNumber != null}
        onCancel={() => {
          setPreviewChapterNumber(null)
          setPreviewDiffData(null)
          setPreviewDiffError(null)
        }}
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <Button onClick={handlePreviewCompare} loading={previewDiffLoading} disabled={previewChapterNumber == null}>
              对比原文
            </Button>
            <Button onClick={() => { setPreviewChapterNumber(null); setPreviewDiffData(null); setPreviewDiffError(null) }}>
              关闭
            </Button>
          </div>
        }
        width={800}
      >
        {previewChapterNumber != null && (
          <div>
            {previewDiffLoading && (
              <div style={{ padding: 24, textAlign: 'center' }}>
                <Spin tip="加载对比中…" />
              </div>
            )}
            {previewDiffError && !previewDiffLoading && (
              <Alert
                type="warning"
                message="加载对比失败"
                description={previewDiffError}
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}
            {previewDiffData && !previewDiffLoading && (
              <div style={{ marginBottom: 16 }}>
                <Collapse
                  defaultActiveKey={['diff']}
                  items={[
                    { key: 'original', label: '重生成前原文', children: <pre style={{ whiteSpace: 'pre-wrap', marginBottom: 0, padding: 12, background: 'rgba(0,0,0,0.02)', borderRadius: 4, fontSize: 13, maxHeight: 280, overflow: 'auto' }}>{previewDiffData.original || '(空)'}</pre> },
                    { key: 'modified', label: '重生成后正文', children: <pre style={{ whiteSpace: 'pre-wrap', marginBottom: 0, padding: 12, background: 'rgba(0,0,0,0.02)', borderRadius: 4, fontSize: 13, maxHeight: 280, overflow: 'auto' }}>{previewDiffData.modified || '(空)'}</pre> },
                    {
                      key: 'diff',
                      label: '对比',
                      children: (
                        <div style={{ maxHeight: 280, overflow: 'auto', padding: 12, background: 'rgba(0,0,0,0.02)', borderRadius: 4, fontSize: 13 }}>
                          <DiffView diff={previewDiffData.diff} />
                        </div>
                      ),
                    },
                  ]}
                />
              </div>
            )}
            {!previewDiffData && !previewDiffLoading && (
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  maxHeight: 520,
                  overflow: 'auto',
                  padding: designTokens.marginMD,
                  background: 'rgba(0,0,0,0.02)',
                  borderRadius: 4,
                  fontSize: 13,
                  marginBottom: 0,
                }}
              >
                {chaptersContentFromTask[String(previewChapterNumber)] ?? '（暂无该章内容）'}
              </pre>
            )}
          </div>
        )}
      </Modal>
    </>
  )
}

export default ReviewTaskPage
