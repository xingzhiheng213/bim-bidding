import { useState } from 'react'
import {
  Alert,
  Button,
  Collapse,
  Form,
  Input,
  message,
  Radio,
  Select,
  Space,
  Spin,
  Tabs,
  Typography,
} from 'antd'
import { useQuery } from '@tanstack/react-query'
import {
  getFrameworkDiff,
  getChaptersDiff,
  postCompare,
  type DiffItem,
} from '../api/compare'
import { getTasks } from '../api/tasks'
import { DiffView } from '../components/DiffView'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text } = Typography
const { TextArea } = Input

type TaskDiffType = 'framework' | 'chapter'

const contentMaxWidth = 720

function ComparePage() {
  const [original, setOriginal] = useState('')
  const [modified, setModified] = useState('')
  const [diff, setDiff] = useState<DiffItem[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [taskId, setTaskId] = useState<number | null>(null)
  const [taskDiffType, setTaskDiffType] = useState<TaskDiffType>('framework')
  const [chapterNumber, setChapterNumber] = useState(1)
  const [taskDiffResult, setTaskDiffResult] = useState<{
    original: string
    modified: string
    diff: DiffItem[]
  } | null>(null)
  const [loadingTaskDiff, setLoadingTaskDiff] = useState(false)
  const [errorTaskDiff, setErrorTaskDiff] = useState<string | null>(null)
  const [editedModified, setEditedModified] = useState('')

  const { data: tasksData } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
  })

  const getErrorDetail = (e: unknown, fallback: string) =>
    e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
      ? String((e.response.data as { detail: unknown }).detail)
      : e instanceof Error
        ? e.message
        : fallback

  const handleCompare = async () => {
    setError(null)
    setDiff(null)
    setLoading(true)
    try {
      const res = await postCompare(original, modified)
      setDiff(res.diff)
      if (res.diff.length === 0) {
        message.info('两段文本无差异')
      }
    } catch (e: unknown) {
      const detail = getErrorDetail(e, '对比请求失败')
      setError(detail)
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadTaskDiff = async () => {
    if (taskId == null) {
      message.warning('请先选择任务')
      return
    }
    setErrorTaskDiff(null)
    setTaskDiffResult(null)
    setLoadingTaskDiff(true)
    try {
      const res =
        taskDiffType === 'framework'
          ? await getFrameworkDiff(String(taskId))
          : await getChaptersDiff(String(taskId), chapterNumber)
      setTaskDiffResult({ original: res.original, modified: res.modified, diff: res.diff })
      setEditedModified(res.modified)
    } catch (e: unknown) {
      const detail = getErrorDetail(e, '加载对比失败')
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

  return (
    <div style={{ maxWidth: contentMaxWidth, width: '100%' }}>
      <Title level={2} style={{ marginBottom: designTokens.marginLG }}>
        文本对比（标红删除、标绿新增）
      </Title>

      <Tabs
        items={[
          {
            key: 'task',
            label: '从任务加载',
            children: (
              <div style={{ paddingTop: designTokens.marginSM }}>
                <Form
                  layout="horizontal"
                  labelCol={{ style: { width: 80 } }}
                  wrapperCol={{ style: { flex: 1 } }}
                  style={{ marginBottom: designTokens.margin }}
                >
                  <Space wrap align="center" size={designTokens.margin}>
                    <Form.Item label="任务" style={{ marginBottom: 0 }}>
                      <Select
                        placeholder="选择任务"
                        value={taskId}
                        onChange={(v) => setTaskId(v ?? null)}
                        style={{ minWidth: 180 }}
                        options={(tasksData ?? []).map((t) => ({
                          value: t.id,
                          label: `任务 ${t.id} - ${t.status}`,
                        }))}
                        allowClear
                      />
                    </Form.Item>
                    <Form.Item label="对比类型" style={{ marginBottom: 0 }}>
                      <Radio.Group
                        value={taskDiffType}
                        onChange={(e) => setTaskDiffType(e.target.value)}
                        optionType="button"
                        options={[
                          { label: '框架对比', value: 'framework' },
                          { label: '章节对比', value: 'chapter' },
                        ]}
                      />
                    </Form.Item>
                    {taskDiffType === 'chapter' && (
                      <Form.Item label="章节号" style={{ marginBottom: 0 }}>
                        <Input
                          type="number"
                          min={1}
                          value={chapterNumber}
                          onChange={(e) =>
                            setChapterNumber(parseInt(e.target.value, 10) || 1)
                          }
                          style={{ width: 80 }}
                        />
                      </Form.Item>
                    )}
                    <Button
                      type="primary"
                      loading={loadingTaskDiff}
                      onClick={handleLoadTaskDiff}
                      disabled={taskId == null}
                    >
                      加载对比
                    </Button>
                  </Space>
                </Form>

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
                                <pre style={preBlockStyle}>
                                  {taskDiffResult.original || '(空)'}
                                </pre>
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
                                <pre style={preBlockStyle}>
                                  {taskDiffResult.modified || '(空)'}
                                </pre>
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
                      <Button
                        type="default"
                        loading={loadingTaskDiff}
                        onClick={handleRecompareFromEdited}
                      >
                        再次对比
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ),
          },
          {
            key: 'manual',
            label: '两段文本对比',
            children: (
              <div style={{ paddingTop: designTokens.marginSM }}>
                <div
                  style={{
                    marginBottom: designTokens.margin,
                    display: 'flex',
                    gap: designTokens.margin,
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 280 }}>
                    <Text
                      style={{
                        display: 'block',
                        marginBottom: designTokens.marginXS,
                      }}
                    >
                      修改前（original）
                    </Text>
                    <TextArea
                      value={original}
                      onChange={(e) => setOriginal(e.target.value)}
                      placeholder="输入修改前的文本"
                      rows={6}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 280 }}>
                    <Text
                      style={{
                        display: 'block',
                        marginBottom: designTokens.marginXS,
                      }}
                    >
                      修改后（modified）
                    </Text>
                    <TextArea
                      value={modified}
                      onChange={(e) => setModified(e.target.value)}
                      placeholder="输入修改后的文本"
                      rows={6}
                      style={{ width: '100%' }}
                    />
                  </div>
                </div>
                <Button
                  type="primary"
                  loading={loading}
                  onClick={handleCompare}
                  style={{ marginBottom: designTokens.margin }}
                >
                  对比
                </Button>

                {error && (
                  <Alert
                    type="error"
                    message={error}
                    style={{ marginBottom: designTokens.margin }}
                    showIcon
                  />
                )}

                {diff !== null && (
                  <div style={{ marginTop: designTokens.margin }}>
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
                      <DiffView diff={diff} />
                    </div>
                  </div>
                )}
              </div>
            ),
          },
        ]}
      />
    </div>
  )
}

export default ComparePage
