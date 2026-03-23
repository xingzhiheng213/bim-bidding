import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Alert, Button, Collapse, Input, message, Space, Spin, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import {
  getFrameworkDiff,
  getChaptersDiff,
  getTaskCompareMeta,
  postCompare,
  type DiffItem,
  type CompareMetaResponse,
} from '../api/compare'
import { getTask, type TaskDetail } from '../api/tasks'
import { DiffView } from '../components/DiffView'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text } = Typography
const { TextArea } = Input

const contentMaxWidth = 960

function CompareTaskDetailPage() {
  const params = useParams()
  const taskIdParam = params.id as string | undefined

  const [taskDiffResult, setTaskDiffResult] = useState<{
    original: string
    modified: string
    diff: DiffItem[]
  } | null>(null)
  const [loadingTaskDiff, setLoadingTaskDiff] = useState(false)
  const [errorTaskDiff, setErrorTaskDiff] = useState<string | null>(null)
  const [editedModified, setEditedModified] = useState('')

  const {
    data: taskDetail,
    isLoading: loadingTaskDetail,
    error: taskDetailError,
  } = useQuery<TaskDetail | undefined>({
    queryKey: ['task', taskIdParam],
    queryFn: async () => (taskIdParam ? getTask(taskIdParam) : undefined),
    enabled: !!taskIdParam,
  })

  const {
    data: taskCompareMeta,
    isLoading: loadingCompareMeta,
    error: compareMetaError,
  } = useQuery<CompareMetaResponse | undefined>({
    queryKey: ['task-compare-meta', taskIdParam],
    queryFn: async () => (taskIdParam ? getTaskCompareMeta(taskIdParam) : undefined),
    enabled: !!taskIdParam,
  })

  const getErrorDetail = (e: unknown, fallback: string) =>
    e &&
    typeof e === 'object' &&
    'response' in e &&
    e.response &&
    typeof e.response === 'object' &&
    'data' in e.response &&
    e.response.data &&
    typeof e.response.data === 'object' &&
    'detail' in e.response.data
      ? String((e.response.data as { detail: unknown }).detail)
      : e instanceof Error
        ? e.message
        : fallback

  const handleLoadFrameworkDiff = async () => {
    if (!taskIdParam) {
      message.warning('无效的任务 ID')
      return
    }
    setErrorTaskDiff(null)
    setTaskDiffResult(null)
    setLoadingTaskDiff(true)
    try {
      const res = await getFrameworkDiff(taskIdParam)
      setTaskDiffResult({ original: res.original, modified: res.modified, diff: res.diff })
      setEditedModified(res.modified)
    } catch (e: unknown) {
      const detail = getErrorDetail(e, '加载框架对比失败')
      setErrorTaskDiff(detail)
      message.error(detail)
    } finally {
      setLoadingTaskDiff(false)
    }
  }

  const handleLoadChapterDiff = async (chapterNumber: number) => {
    if (!taskIdParam) {
      message.warning('无效的任务 ID')
      return
    }
    setErrorTaskDiff(null)
    setTaskDiffResult(null)
    setLoadingTaskDiff(true)
    try {
      const res = await getChaptersDiff(taskIdParam, chapterNumber)
      setTaskDiffResult({ original: res.original, modified: res.modified, diff: res.diff })
      setEditedModified(res.modified)
    } catch (e: unknown) {
      const detail = getErrorDetail(e, `加载第 ${chapterNumber} 章对比失败`)
      setErrorTaskDiff(detail)
      message.error(detail)
    } finally {
      setLoadingTaskDiff(false)
    }
  }

  const handleRecompareFromEdited = async () => {
    if (taskDiffResult == null) return
    setErrorTaskDiff(null)
    setLoadingTaskDiff(true)
    try {
      const res = await postCompare(taskDiffResult.original, editedModified)
      setTaskDiffResult((prev) =>
        prev ? { ...prev, modified: editedModified, diff: res.diff } : null,
      )
      if (res.diff.length === 0) {
        message.info('两段文本无差异')
      }
    } catch (e: unknown) {
      const detail = getErrorDetail(e, '再次对比失败')
      setErrorTaskDiff(detail)
      message.error(detail)
    } finally {
      setLoadingTaskDiff(false)
    }
  }

  const diffResultBoxStyle = {
    border: `1px solid ${designTokens.colorBorder}`,
    borderRadius: designTokens.borderRadiusSM,
    padding: designTokens.paddingSM,
    background: designTokens.colorBgLayout,
    minHeight: 60,
  }

  const preBlockStyle = {
    whiteSpace: 'pre-wrap' as const,
    background: designTokens.colorBgLayout,
    padding: designTokens.paddingXS,
    borderRadius: designTokens.borderRadiusSM,
    maxHeight: 200,
    overflow: 'auto' as const,
    border: `1px solid ${designTokens.colorBorderSecondary}`,
  }

  const taskTitle =
    taskDetail?.name != null && taskDetail.name.trim()
      ? `${taskDetail.name} (#${taskDetail.id})`
      : taskDetail
        ? `任务 #${taskDetail.id}`
        : taskIdParam
          ? `任务 #${taskIdParam}`
          : '任务'

  return (
    <div style={{ maxWidth: contentMaxWidth, width: '100%' }}>
      <div style={{ marginBottom: designTokens.marginLG }}>
        <Link to="/compare" style={{ marginRight: designTokens.marginSM }}>
          返回对比任务列表
        </Link>
      </div>
      <Title level={2} style={{ marginBottom: designTokens.marginSM }}>
        文本对比 - {taskTitle}
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginLG }}>
        基于任务的框架与章节前后版本进行对比，可从下方选择具体对比项。
      </Text>

      {loadingTaskDetail && (
        <Spin size="small" style={{ display: 'block', marginBottom: designTokens.marginSM }} />
      )}
      {taskDetailError && (
        <Alert
          type="error"
          message={getErrorDetail(taskDetailError as unknown, '加载任务信息失败')}
          style={{ marginBottom: designTokens.marginSM }}
          showIcon
        />
      )}

      {taskIdParam && loadingCompareMeta && (
        <Spin size="small" style={{ display: 'block', marginBottom: designTokens.marginSM }} />
      )}

      {compareMetaError && (
        <Alert
          type="error"
          message={getErrorDetail(compareMetaError as unknown, '加载任务对比信息失败')}
          style={{ marginBottom: designTokens.marginSM }}
          showIcon
        />
      )}

      {taskCompareMeta && !taskCompareMeta.has_any && (
        <Alert
          type="info"
          message="该任务暂无可对比版本"
          description="当前任务还没有框架或章节的前后版本记录。完成至少一次重生成后即可在此查看对比。"
          style={{ marginBottom: designTokens.marginLG }}
          showIcon
        />
      )}

      {taskCompareMeta && taskCompareMeta.has_any && (
        <div style={{ marginBottom: designTokens.marginLG }}>
          <Text
            type="secondary"
            style={{ display: 'block', marginBottom: designTokens.marginXS }}
          >
            选择要查看的对比项：
          </Text>
          <Space wrap size={designTokens.marginXS}>
            {taskCompareMeta.framework?.has_diff && (
              <Button
                type="default"
                onClick={handleLoadFrameworkDiff}
                loading={loadingTaskDiff}
              >
                框架前后对比
              </Button>
            )}
            {taskCompareMeta.chapters.map((c) => (
              <Button
                key={c.number}
                type="default"
                onClick={() => handleLoadChapterDiff(c.number)}
                loading={loadingTaskDiff}
              >
                {c.label}前后对比
              </Button>
            ))}
          </Space>
        </div>
      )}

      {errorTaskDiff && (
        <Alert
          type="error"
          message={errorTaskDiff}
          style={{ marginBottom: designTokens.marginSM }}
          showIcon
        />
      )}

      {loadingTaskDiff && !taskDiffResult && (
        <Spin size="small" style={{ display: 'block', marginBottom: designTokens.marginSM }} />
      )}

      {taskDiffResult && (
        <div style={{ marginTop: designTokens.marginSM }}>
          <Collapse
            size="small"
            items={[
              {
                key: '1',
                label: '修改前 / 修改后原文（可折叠）',
                children: (
                  <div
                    style={{
                      display: 'flex',
                      gap: designTokens.margin,
                      flexWrap: 'wrap',
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 200 }}>
                      <Text
                        type="secondary"
                        style={{
                          display: 'block',
                          marginBottom: designTokens.marginXXS,
                          fontSize: designTokens.fontSizeSM,
                        }}
                      >
                        修改前
                      </Text>
                      <pre style={preBlockStyle}>{taskDiffResult.original || '(空)'}</pre>
                    </div>
                    <div style={{ flex: 1, minWidth: 200 }}>
                      <Text
                        type="secondary"
                        style={{
                          display: 'block',
                          marginBottom: designTokens.marginXXS,
                          fontSize: designTokens.fontSizeSM,
                        }}
                      >
                        修改后
                      </Text>
                      <pre style={preBlockStyle}>{taskDiffResult.modified || '(空)'}</pre>
                    </div>
                  </div>
                ),
              },
            ]}
          />
          <div style={{ marginTop: designTokens.marginSM }}>
            <Text
              strong
              style={{
                display: 'block',
                marginBottom: designTokens.marginXS,
              }}
            >
              对比结果（红=删除，绿=新增）
            </Text>
            <div style={diffResultBoxStyle}>
              <DiffView diff={taskDiffResult.diff} />
            </div>
          </div>
          <div style={{ marginTop: designTokens.marginSM }}>
            <Text
              style={{
                display: 'block',
                marginBottom: designTokens.marginXS,
              }}
            >
              编辑「修改后」再次对比（可选）
            </Text>
            <TextArea
              value={editedModified}
              onChange={(e) => setEditedModified(e.target.value)}
              placeholder="编辑后点击「再次对比」"
              rows={4}
              style={{
                width: '100%',
                marginBottom: designTokens.marginXS,
              }}
            />
            <Button type="default" loading={loadingTaskDiff} onClick={handleRecompareFromEdited}>
              再次对比
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CompareTaskDetailPage

