import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useQuery } from '@tanstack/react-query'
import { getTasks, type TaskSummary } from '../api/tasks'
import { getIdentityScopeKey } from '../api/client'
import { useSelectedProfile } from '../context/SelectedProfileContext'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text } = Typography

function ComparePage() {
  const navigate = useNavigate()
  const identityScope = getIdentityScopeKey()
  const { selectedProfileId } = useSelectedProfile()
  const [taskId, setTaskId] = useState<number | null>(null)

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', identityScope, selectedProfileId],
    queryFn: () => getTasks(selectedProfileId),
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
          onClick: () => {
            setTaskId(record.id)
            navigate(`/compare/tasks/${record.id}`)
          },
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
