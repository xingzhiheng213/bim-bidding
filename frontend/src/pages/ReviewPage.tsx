import { useQueries, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Button, Empty, Spin, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { getTask, getTasks, type TaskDetail, type TaskSummary } from '../api/tasks'
import { getIdentityScopeKey } from '../api/client'
import { useSelectedProfile } from '../context/SelectedProfileContext'
import { designTokens } from '../theme/tokens'
import { getStepStatusLabel, stepStatusDisplay, type StepStatus } from '../theme/stepStatus'
import '../App.css'

const { Title, Text } = Typography

const STEP_STATUS_VALUES: StepStatus[] = ['pending', 'running', 'waiting_user', 'completed', 'failed']

function getReviewStatusDisplay(status: string): { tagColor: 'default' | 'primary' | 'success' | 'warning' | 'error'; label: string } {
  if (STEP_STATUS_VALUES.includes(status as StepStatus)) {
    const s = status as StepStatus
    return { tagColor: stepStatusDisplay[s].tagColor, label: getStepStatusLabel(s) }
  }
  return { tagColor: 'default', label: status || '待审查' }
}

function ReviewPage() {
  const navigate = useNavigate()
  const identityScope = getIdentityScopeKey()
  const { selectedProfileId } = useSelectedProfile()

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', identityScope, selectedProfileId],
    queryFn: () => getTasks(selectedProfileId),
  })

  const taskIds = tasksData?.map((t) => String(t.id)) ?? []
  const detailQueries = useQueries({
    queries: taskIds.map((id) => ({
      queryKey: ['task', identityScope, id],
      queryFn: () => getTask(id),
      enabled: taskIds.length > 0,
    })),
  })

  const tasksWithChaptersCompleted: (TaskSummary & { detail?: TaskDetail })[] = []
  if (tasksData) {
    for (let i = 0; i < tasksData.length; i++) {
      const summary = tasksData[i]
      const detail = detailQueries[i]?.data
      if (!detail?.steps) continue
      const chaptersStep = detail.steps.find((s) => s.step_key === 'chapters')
      if (chaptersStep?.status !== 'completed' || !chaptersStep.output_snapshot) continue
      tasksWithChaptersCompleted.push({ ...summary, detail })
    }
  }

  const isLoadingDetails = detailQueries.some((q) => q.isLoading)
  const isLoading = tasksLoading || (taskIds.length > 0 && isLoadingDetails)

  const columns: ColumnsType<TaskSummary & { detail?: TaskDetail }> = [
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
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
    },
    {
      title: '审查状态',
      key: 'review_status',
      width: 120,
      render: (_, record) => {
        const reviewStep = record.detail?.steps?.find((s) => s.step_key === 'review')
        const status = reviewStep?.status ?? 'pending'
        const { tagColor, label } = getReviewStatusDisplay(status === 'pending' && !reviewStep ? '待审查' : status)
        return <Tag color={tagColor}>{reviewStep ? label : '待审查'}</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button type="primary" size="small" onClick={() => navigate(`/review/${record.id}`)}>
          进入审查
        </Button>
      ),
    },
  ]

  return (
    <>
      <Title level={2} style={{ marginBottom: designTokens.marginLG }}>
        校审
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginLG }}>
        对「按章生成完成」的任务进行审查，查看校审意见并可接受后重生成章节
      </Text>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={tasksWithChaptersCompleted}
        loading={isLoading}
        pagination={{ pageSize: 10 }}
        locale={{
          emptyText: (
            <div style={{ padding: designTokens.paddingLG }}>
              <Empty
                description={
                  tasksLoading || isLoadingDetails ? (
                    <Spin tip="加载任务列表…" />
                  ) : (
                    '暂无章节已生成完成的任务，请先在首页创建任务并完成按章生成'
                  )
                }
              />
            </div>
          ),
        }}
      />
    </>
  )
}

export default ReviewPage
