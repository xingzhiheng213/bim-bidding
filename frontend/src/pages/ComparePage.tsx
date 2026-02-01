import { useState } from 'react'
import { Button, Collapse, Input, message, Radio, Select, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import {
  getFrameworkDiff,
  getChaptersDiff,
  postCompare,
  type DiffItem,
} from '../api/compare'
import { getTasks } from '../api/tasks'
import { DiffView } from '../components/DiffView'
import '../App.css'

const { Title } = Typography
const { TextArea } = Input

type TaskDiffType = 'framework' | 'chapter'

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
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '对比请求失败'
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
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '加载对比失败'
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
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '再次对比失败'
      setErrorTaskDiff(detail)
      message.error(detail)
    } finally {
      setLoadingTaskDiff(false)
    }
  }

  return (
    <>
      <Title level={2} style={{ marginBottom: 16 }}>
        文本对比（标红删除、标绿新增）
      </Title>

        {/* 从任务查看对比 */}
        <div style={{ marginBottom: 32 }}>
          <Title level={5} style={{ marginBottom: 12 }}>
            从任务查看对比
          </Title>
          <div style={{ marginBottom: 12, display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
            <span>任务：</span>
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
            <span>对比类型：</span>
            <Radio.Group
              value={taskDiffType}
              onChange={(e) => setTaskDiffType(e.target.value)}
              optionType="button"
              options={[
                { label: '框架对比', value: 'framework' },
                { label: '章节对比', value: 'chapter' },
              ]}
            />
            {taskDiffType === 'chapter' && (
              <>
                <span>章节号：</span>
                <Input
                  type="number"
                  min={1}
                  value={chapterNumber}
                  onChange={(e) => setChapterNumber(parseInt(e.target.value, 10) || 1)}
                  style={{ width: 80 }}
                />
              </>
            )}
            <Button
              type="primary"
              loading={loadingTaskDiff}
              onClick={handleLoadTaskDiff}
              disabled={taskId == null}
            >
              加载对比
            </Button>
          </div>
          {errorTaskDiff && (
            <div style={{ color: '#cf1322', marginBottom: 12 }}>{errorTaskDiff}</div>
          )}
          {taskDiffResult && (
            <div style={{ marginTop: 12 }}>
              <Collapse
                size="small"
                items={[
                  {
                    key: '1',
                    label: '修改前 / 修改后原文（可折叠）',
                    children: (
                      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                        <div style={{ flex: 1, minWidth: 200 }}>
                          <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>修改前</div>
                          <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
                            {taskDiffResult.original || '(空)'}
                          </pre>
                        </div>
                        <div style={{ flex: 1, minWidth: 200 }}>
                          <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>修改后</div>
                          <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
                            {taskDiffResult.modified || '(空)'}
                          </pre>
                        </div>
                      </div>
                    ),
                  },
                ]}
              />
              <div style={{ marginTop: 12 }}>
                <div style={{ marginBottom: 8 }}>对比结果（红=删除，绿=新增）</div>
                <div
                  style={{
                    border: '1px solid #d9d9d9',
                    borderRadius: 4,
                    padding: 12,
                    background: '#fafafa',
                    minHeight: 60,
                  }}
                >
                  <DiffView diff={taskDiffResult.diff} />
                </div>
              </div>
              {/* 可选：编辑修改后再次对比 */}
              <div style={{ marginTop: 12 }}>
                <div style={{ marginBottom: 8 }}>编辑「修改后」再次对比（可选）</div>
                <TextArea
                  value={editedModified}
                  onChange={(e) => setEditedModified(e.target.value)}
                  placeholder="编辑后点击「再次对比」"
                  rows={4}
                  style={{ width: '100%', marginBottom: 8 }}
                />
                <Button type="default" loading={loadingTaskDiff} onClick={handleRecompareFromEdited}>
                  再次对比
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 两段文本对比 */}
        <div style={{ borderTop: '1px solid #eee', paddingTop: 24 }}>
          <Title level={5} style={{ marginBottom: 12 }}>
            两段文本对比
          </Title>
          <div style={{ marginBottom: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 280 }}>
              <div style={{ marginBottom: 8 }}>修改前（original）</div>
              <TextArea
                value={original}
                onChange={(e) => setOriginal(e.target.value)}
                placeholder="输入修改前的文本"
                rows={6}
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 280 }}>
              <div style={{ marginBottom: 8 }}>修改后（modified）</div>
              <TextArea
                value={modified}
                onChange={(e) => setModified(e.target.value)}
                placeholder="输入修改后的文本"
                rows={6}
                style={{ width: '100%' }}
              />
            </div>
          </div>
          <Button type="primary" loading={loading} onClick={handleCompare} style={{ marginBottom: 16 }}>
            对比
          </Button>
          {error && (
            <div style={{ color: '#cf1322', marginBottom: 16 }}>{error}</div>
          )}
          {diff !== null && (
            <div style={{ marginTop: 16 }}>
              <Title level={5} style={{ marginBottom: 8 }}>
                对比结果（红=删除，绿=新增）
              </Title>
              <div
                style={{
                  border: '1px solid #d9d9d9',
                  borderRadius: 4,
                  padding: 12,
                  background: '#fafafa',
                  minHeight: 60,
                }}
              >
                <DiffView diff={diff} />
              </div>
            </div>
          )}
        </div>
    </>
  )
}

export default ComparePage
