import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Empty, Input, message, Modal, Popconfirm, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { createTask, deleteTask, getTasks, type TaskSummary } from '../api/tasks'
import { getIdentityScopeKey } from '../api/client'
import { useSelectedProfile } from '../context/SelectedProfileContext'
import { designTokens } from '../theme/tokens'
import { getStepStatusLabel, stepStatusDisplay, type StepStatus } from '../theme/stepStatus'
import '../App.css'

const { Title, Text } = Typography

const TASK_STATUS_VALUES: StepStatus[] = ['pending', 'running', 'waiting_user', 'completed', 'failed']
function getTaskStatusDisplay(status: string): { tagColor: 'default' | 'primary' | 'success' | 'warning' | 'error'; label: string } {
  if (TASK_STATUS_VALUES.includes(status as StepStatus)) {
    const s = status as StepStatus
    return { tagColor: stepStatusDisplay[s].tagColor, label: getStepStatusLabel(s) }
  }
  return { tagColor: 'default', label: status || '待执行' }
}

function OneClickPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const identityScope = getIdentityScopeKey()
  const { selectedProfileId } = useSelectedProfile()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createTaskName, setCreateTaskName] = useState('')
  const {
    data: tasksData,
    isLoading: tasksLoading,
  } = useQuery({
    queryKey: ['tasks', identityScope, selectedProfileId],
    queryFn: () => getTasks(selectedProfileId),
  })
  const createMutation = useMutation({
    mutationFn: (name: string) =>
      createTask({
        name: name.trim() || undefined,
        profileId: selectedProfileId ?? undefined,
      }),
    onSuccess: (res) => {
      message.success('任务已创建')
      queryClient.invalidateQueries({ queryKey: ['tasks', identityScope] })
      navigate(`/one-click/tasks/${res.id}`)
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '创建任务失败'
      message.error(detail)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => deleteTask(taskId),
    onSuccess: () => {
      message.success('已删除')
      queryClient.invalidateQueries({ queryKey: ['tasks', identityScope] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '删除失败'
      message.error(detail)
    },
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
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const { tagColor, label } = getTaskStatusDisplay(status)
        return <Tag color={tagColor}>{label}</Tag>
      },
    },
    {
      title: '语义配置',
      key: 'profile',
      width: 160,
      ellipsis: true,
      render: (_, record) => (
        <Text type="secondary" ellipsis={{ tooltip: true }}>
          {record.profile_id != null
            ? record.profile_name || `配置 #${record.profile_id}`
            : '内置默认'}
        </Text>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      render: (v: string) => new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <span onClick={(e) => e.stopPropagation()}>
          <Link to={`/one-click/tasks/${record.id}`} style={{ marginRight: designTokens.marginXS }}>
            进入
          </Link>
          <Popconfirm
            title="确定删除该任务？"
            onConfirm={() => deleteMutation.mutate(String(record.id))}
          >
            <Button type="link" danger size="small" loading={deleteMutation.isPending}>
              删除
            </Button>
          </Popconfirm>
        </span>
      ),
    },
  ]

  return (
    <>
      <Title level={2} style={{ marginBottom: designTokens.marginLG }}>
        一键生成
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginLG }}>
        上传招标文件后自动完成解析、分析、框架与正文生成，仅需在生成框架后确认一次即可。
      </Text>
      <div style={{ marginBottom: designTokens.marginLG }}>
        <Button
          type="primary"
          loading={createMutation.isPending}
          onClick={() => setCreateModalOpen(true)}
        >
          创建任务
        </Button>
      </div>
      <Modal
        title="创建任务"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        okText="创建"
        confirmLoading={createMutation.isPending}
        onOk={() => {
          createMutation.mutate(createTaskName, {
            onSuccess: () => {
              setCreateModalOpen(false)
              setCreateTaskName('')
            },
          })
        }}
      >
        <div style={{ marginBottom: designTokens.marginSM }}>
          <Text type="secondary">任务名称（可选）：</Text>
        </div>
        <Input
          placeholder="例如：XX项目BIM技术标"
          value={createTaskName}
          onChange={(e) => setCreateTaskName(e.target.value)}
          maxLength={255}
          allowClear
        />
        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
          不填写将自动生成默认名称，创建后进入任务上传招标文件并开始生成。
        </Text>
        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
          将使用侧栏当前选中的语义配置；选「BIM技术标（内置）」则不绑定自定义 Profile。
        </Text>
      </Modal>
      <Title level={5} style={{ marginTop: designTokens.marginXL, marginBottom: designTokens.marginSM }}>
        任务列表
      </Title>
      <Table<TaskSummary>
        rowKey="id"
        columns={taskColumns}
        dataSource={tasksData ?? []}
        loading={tasksLoading}
        pagination={{ pageSize: 10 }}
        locale={{
          emptyText: (
            <div style={{ padding: designTokens.paddingLG }}>
              <Empty description="暂无任务，点击下方按钮创建第一个一键生成任务">
                <Button
                  type="primary"
                  loading={createMutation.isPending}
                  onClick={() => setCreateModalOpen(true)}
                >
                  创建任务
                </Button>
              </Empty>
            </div>
          ),
        }}
        onRow={(record) => ({
          onClick: () => navigate(`/one-click/tasks/${record.id}`),
          style: { cursor: 'pointer' },
        })}
      />
    </>
  )
}

export default OneClickPage
