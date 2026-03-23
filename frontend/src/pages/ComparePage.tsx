import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useQuery } from '@tanstack/react-query'
import { getTasks, type TaskSummary } from '../api/tasks'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text } = Typography

function formatTaskLabel(task: { id: number; name: string | null; status: string; compare_summary?: { has_framework: boolean; chapter_count: number } | null }) {
  const base = task.name ? `${task.name} (#${task.id})` : `任务 ${task.id}`
  const status = task.status
  const summary = task.compare_summary
  if (!summary) {
    return `${base} - ${status}（暂无可对比）`
  }
  const parts: string[] = []
  if (summary.has_framework) parts.push('框架')
  if (summary.chapter_count > 0) parts.push(`${summary.chapter_count} 章`)
  const summaryText = parts.length > 0 ? parts.join(' + ') : '无'
  return `${base} - ${status}（可对比：${summaryText}）`
}

function ComparePage() {
  const navigate = useNavigate()
  const [taskId, setTaskId] = useState<number | null>(null)

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
  })

  const taskColumns: ColumnsType<TaskSummary> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (_: string | null, record) => (
        <div style={{ maxWidth: 520 }}>
          <Text strong ellipsis={{ tooltip: record.name || `任务 #${record.id}` }}>
            {record.name || `任务 #${record.id}`}
          </Text>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              #{record.id}
            </Text>
          </div>
          <div>
            <Tag
              color={record.compare_summary ? 'success' : 'default'}
              style={{ fontSize: 12, paddingInline: 8 }}
            >
              {record.compare_summary ? '可对比' : '无对比'}
            </Tag>
          </div>
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      render: (v: string) =>
        new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
    },
  ]

  return (
    <div>
      <Title level={2} style={{ marginBottom: designTokens.marginLG }}>
        前后对比
      </Title>
      <Title
        level={5}
        style={{
          marginTop: designTokens.marginXL,
          marginBottom: designTokens.marginSM,
        }}
      >
        任务列表
      </Title>
      <Table<TaskSummary>
        rowKey="id"
        columns={taskColumns}
        dataSource={tasksData ?? []}
        loading={tasksLoading}
        pagination={false}
        onRow={(record) => ({
          onClick: () => navigate(`/compare/tasks/${record.id}`),
          style: {
            cursor: 'pointer',
            backgroundColor: record.id === taskId ? designTokens.colorBgLayout : undefined,
          },
        })}
      />
    </div>
  )
}

export default ComparePage
