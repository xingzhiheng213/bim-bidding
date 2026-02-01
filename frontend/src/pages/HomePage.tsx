import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Button, message, Popconfirm, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { createTask, deleteTask, getTasks, type TaskSummary } from '../api/tasks'
import '../App.css'

const { Title } = Typography

function HomePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const {
    data: tasksData,
    isLoading: tasksLoading,
  } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
  })
  const createMutation = useMutation({
    mutationFn: () => createTask(),
    onSuccess: (res) => {
      message.success('任务已创建')
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      navigate(`/tasks/${res.id}`)
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
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
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
    { title: '任务 ID', dataIndex: 'id', key: 'id', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <span onClick={(e) => e.stopPropagation()}>
          <Link to={`/tasks/${record.id}`} style={{ marginRight: 8 }}>
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
      <Title level={2} style={{ marginBottom: 16 }}>
        我的任务
      </Title>
      <div style={{ marginTop: 24 }}>
        <Button
          type="primary"
          loading={createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          创建任务
        </Button>
      </div>
      <Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>
        任务列表
      </Title>
      <Table<TaskSummary>
        rowKey="id"
        columns={taskColumns}
        dataSource={tasksData ?? []}
        loading={tasksLoading}
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无任务，请点击上方按钮创建' }}
        onRow={(record) => ({
          onClick: () => navigate(`/tasks/${record.id}`),
          style: { cursor: 'pointer' },
        })}
      />
    </>
  )
}

export default HomePage
