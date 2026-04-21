import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import type { PromptCatalogItem } from '../api/settings'
import {
  createPromptProfile,
  deletePromptProfile,
  fetchPromptProfileDisciplines,
  generatePromptProfileSemantic,
  getPromptProfile,
  listPromptProfiles,
  updatePromptProfile,
  type PromptProfileSummary,
} from '../api/promptProfiles'
import { getIdentityScopeKey } from '../api/client'
import { getSemanticSlotModalRow } from '../config/semanticSlotModalDisplay'
import { useSelectedProfile } from '../context/SelectedProfileContext'
import { designTokens } from '../theme/tokens'
import { catalogIdToSemanticSlotKey } from '../utils/semanticCatalog'

const { Text } = Typography

type ModalMode = 'closed' | 'create' | 'edit'

/** 仅提交非空槽位；与弹窗内是否展示 catalog 全文无关（弹窗不预填默认提示词）。 */
function buildOverridesPayload(
  semanticItems: PromptCatalogItem[],
  raw: Record<string, string> | undefined,
): Record<string, string> | null {
  if (!raw) return null
  const out: Record<string, string> = {}
  for (const it of semanticItems) {
    const key = catalogIdToSemanticSlotKey(it.id)
    if (!key) continue
    const v = raw[key]
    if (typeof v === 'string' && v.trim()) out[key] = v.trim()
  }
  return Object.keys(out).length ? out : null
}

export default function SemanticProfilesSection({
  semanticItems,
}: {
  semanticItems: PromptCatalogItem[]
}) {
  const queryClient = useQueryClient()
  const identityScope = getIdentityScopeKey()
  const { setSelectedProfileId } = useSelectedProfile()
  const [searchParams, setSearchParams] = useSearchParams()

  const [modalMode, setModalMode] = useState<ModalMode>('closed')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm<{
    name: string
    discipline: string
    slug?: string
    semantic_overrides?: Record<string, string>
  }>()
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [genSlotKey, setGenSlotKey] = useState<string | null>(null)
  const [genAllLoading, setGenAllLoading] = useState(false)
  const [exampleModal, setExampleModal] = useState<{
    open: boolean
    title: string
    content: string
  }>({ open: false, title: '', content: '' })
  const generationControllersRef = useRef<Set<AbortController>>(new Set())
  const generationGuardRef = useRef(0)

  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ['prompt-profiles', identityScope],
    queryFn: listPromptProfiles,
  })

  const { data: disciplinesRes } = useQuery({
    queryKey: ['prompt-profile-disciplines', identityScope],
    queryFn: fetchPromptProfileDisciplines,
  })
  const disciplineOptions = disciplinesRes?.items ?? []

  useEffect(() => {
    if (searchParams.get('create') !== '1') return
    if (semanticItems.length === 0) return
    setModalMode('create')
    setEditingId(null)
    form.resetFields()
    const overrides: Record<string, string> = {}
    for (const it of semanticItems) {
      const key = catalogIdToSemanticSlotKey(it.id)
      if (key) overrides[key] = ''
    }
    form.setFieldsValue({
      name: '',
      slug: '',
      discipline: '建筑',
      semantic_overrides: overrides,
    })
    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams, form, semanticItems])

  const abortOngoingGeneration = () => {
    generationGuardRef.current += 1
    for (const controller of generationControllersRef.current) {
      controller.abort()
    }
    generationControllersRef.current.clear()
    setGenSlotKey(null)
    setGenAllLoading(false)
  }

  const closeModal = () => {
    abortOngoingGeneration()
    setModalMode('closed')
    setEditingId(null)
    form.resetFields()
  }

  const openCreate = () => {
    setModalMode('create')
    setEditingId(null)
    const overrides: Record<string, string> = {}
    for (const it of semanticItems) {
      const key = catalogIdToSemanticSlotKey(it.id)
      if (key) overrides[key] = ''
    }
    form.setFieldsValue({
      name: '',
      slug: '',
      discipline: '建筑',
      semantic_overrides: overrides,
    })
  }

  const openEdit = async (row: PromptProfileSummary) => {
    setModalMode('edit')
    setEditingId(row.id)
    setLoadingDetail(true)
    try {
      const detail = await getPromptProfile(row.id)
      const overrides: Record<string, string> = {}
      const hideStored = row.is_builtin
      for (const it of semanticItems) {
        const key = catalogIdToSemanticSlotKey(it.id)
        if (!key) continue
        const stored = detail.semantic_overrides?.[key]
        if (hideStored) {
          overrides[key] = ''
        } else {
          overrides[key] = typeof stored === 'string' && stored.trim() ? stored : ''
        }
      }
      form.setFieldsValue({
        name: detail.name,
        slug: detail.slug ?? '',
        discipline: detail.discipline || '建筑',
        semantic_overrides: overrides,
      })
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载配置失败')
      setModalMode('closed')
      setEditingId(null)
    } finally {
      setLoadingDetail(false)
    }
  }

  const createMut = useMutation({
    mutationFn: async () => {
      const v = await form.validateFields()
      const payload = buildOverridesPayload(semanticItems, v.semantic_overrides)
      return createPromptProfile({
        name: v.name.trim(),
        discipline: v.discipline,
        slug: v.slug?.trim() || undefined,
        semantic_overrides: payload,
      })
    },
    onSuccess: (data) => {
      message.success('已创建语义配置')
      queryClient.invalidateQueries({ queryKey: ['prompt-profiles', identityScope] })
      setSelectedProfileId(data.id)
      closeModal()
    },
    onError: (e: Error & { response?: { data?: { detail?: string } } }) => {
      const d = e?.response?.data?.detail
      message.error(typeof d === 'string' ? d : e.message || '创建失败')
    },
  })

  const updateMut = useMutation({
    mutationFn: async () => {
      const v = await form.validateFields()
      const payload = buildOverridesPayload(semanticItems, v.semantic_overrides)
      if (editingId == null) throw new Error('missing id')
      return updatePromptProfile(editingId, {
        name: v.name.trim(),
        discipline: v.discipline,
        slug: v.slug?.trim() || undefined,
        semantic_overrides: payload,
      })
    },
    onSuccess: () => {
      message.success('已保存')
      queryClient.invalidateQueries({ queryKey: ['prompt-profiles', identityScope] })
      closeModal()
    },
    onError: (e: Error & { response?: { data?: { detail?: string } } }) => {
      const d = e?.response?.data?.detail
      message.error(typeof d === 'string' ? d : e.message || '保存失败')
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deletePromptProfile(id),
    onSuccess: () => {
      message.success('已删除')
      queryClient.invalidateQueries({ queryKey: ['prompt-profiles', identityScope] })
    },
    onError: (e: Error & { response?: { data?: { detail?: string } } }) => {
      const d = e?.response?.data?.detail
      message.error(typeof d === 'string' ? d : e.message || '删除失败')
    },
  })

  const editingBuiltin = useMemo(() => {
    if (editingId == null) return false
    return profiles.some((p) => p.id === editingId && p.is_builtin)
  }, [editingId, profiles])

  const slotFields = useMemo(() => {
    return semanticItems
      .map((it) => {
        const key = catalogIdToSemanticSlotKey(it.id)
        if (!key) return null
        return { key, title: it.title }
      })
      .filter((x): x is { key: string; title: string } => x != null)
  }, [semanticItems])

  const readonly = modalMode === 'edit' && editingBuiltin

  const runGenerateOne = async (slotKey: string) => {
    const name = String(form.getFieldValue('name') ?? '').trim()
    const disc = form.getFieldValue('discipline')
    if (!name) {
      message.warning('请先填写配置名称')
      return
    }
    if (!disc) {
      message.warning('请先选择专业')
      return
    }
    const controller = new AbortController()
    generationControllersRef.current.add(controller)
    const guard = generationGuardRef.current
    setGenSlotKey(slotKey)
    try {
      const res = await generatePromptProfileSemantic({
        profile_name: name,
        discipline: disc,
        slot_key: slotKey,
      }, { signal: controller.signal })
      if (guard !== generationGuardRef.current || controller.signal.aborted) return
      if (res.text != null && res.text !== '') {
        form.setFieldValue(['semantic_overrides', slotKey], res.text)
        message.success('该槽位已生成')
      }
    } catch (e: unknown) {
      const err = e as { code?: string; name?: string; response?: { data?: { detail?: string | string[] } } }
      if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return
      const d = err?.response?.data?.detail
      const msg =
        typeof d === 'string' ? d : Array.isArray(d) ? d.join('; ') : e instanceof Error ? e.message : '生成失败'
      message.error(msg)
    } finally {
      generationControllersRef.current.delete(controller)
      if (guard === generationGuardRef.current) setGenSlotKey(null)
    }
  }

  const handleGenerateOne = (slotKey: string, slotTitle: string) => {
    if (readonly) return
    const name = String(form.getFieldValue('name') ?? '').trim()
    const disc = form.getFieldValue('discipline')
    if (!name) {
      message.warning('请先填写配置名称')
      return
    }
    if (!disc) {
      message.warning('请先选择专业')
      return
    }
    const current = form.getFieldValue(['semantic_overrides', slotKey]) as string | undefined
    if (current?.trim()) {
      Modal.confirm({
        title: '覆盖已有内容？',
        content: `「${slotTitle}」中已有文字，生成结果将替换当前内容。`,
        okText: '生成并覆盖',
        onOk: () => runGenerateOne(slotKey),
      })
    } else {
      void runGenerateOne(slotKey)
    }
  }

  const runGenerateAll = async () => {
    const name = String(form.getFieldValue('name') ?? '').trim()
    const disc = form.getFieldValue('discipline')
    if (!name) {
      message.warning('请先填写配置名称')
      return
    }
    if (!disc) {
      message.warning('请先选择专业')
      return
    }
    const controller = new AbortController()
    generationControllersRef.current.add(controller)
    const guard = generationGuardRef.current
    setGenAllLoading(true)
    try {
      const res = await generatePromptProfileSemantic({
        profile_name: name,
        discipline: disc,
      }, { signal: controller.signal })
      if (guard !== generationGuardRef.current || controller.signal.aborted) return
      if (res.overrides) {
        for (const [k, t] of Object.entries(res.overrides)) {
          form.setFieldValue(['semantic_overrides', k], t)
        }
        message.success('全部槽位已生成，请检查后保存')
      } else {
        message.warning('未收到生成结果')
      }
    } catch (e: unknown) {
      const err = e as { code?: string; name?: string; response?: { data?: { detail?: string | string[] } } }
      if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return
      const d = err?.response?.data?.detail
      const msg =
        typeof d === 'string' ? d : Array.isArray(d) ? d.join('; ') : e instanceof Error ? e.message : '生成失败'
      message.error(msg)
    } finally {
      generationControllersRef.current.delete(controller)
      if (guard === generationGuardRef.current) setGenAllLoading(false)
    }
  }

  const handleGenerateAll = () => {
    if (readonly) return
    const name = String(form.getFieldValue('name') ?? '').trim()
    const disc = form.getFieldValue('discipline')
    if (!name) {
      message.warning('请先填写配置名称')
      return
    }
    if (!disc) {
      message.warning('请先选择专业')
      return
    }
    const overrides = (form.getFieldValue('semantic_overrides') || {}) as Record<string, string>
    const nonEmpty = slotFields.filter(({ key }) => overrides[key]?.trim())
    if (nonEmpty.length > 0) {
      Modal.confirm({
        title: '覆盖已有内容？',
        content: `以下槽位已有文字将被替换：${nonEmpty.map((x) => x.title).join('、')}。将依次调用大模型 ${slotFields.length} 次，耗时较长。`,
        okText: '开始生成',
        onOk: () => runGenerateAll(),
      })
    } else {
      void runGenerateAll()
    }
  }

  return (
    <div style={{ marginBottom: designTokens.marginXL }}>
      <Text strong style={{ fontSize: designTokens.fontSizeLG }}>
        语义配置（Profile）
      </Text>
      <div style={{ marginTop: designTokens.marginSM, marginBottom: designTokens.marginMD }}>
        <Button type="primary" onClick={openCreate}>
          新增配置
        </Button>
      </div>
      <Table<PromptProfileSummary>
        size="small"
        rowKey="id"
        loading={isLoading}
        dataSource={profiles}
        pagination={false}
        columns={[
          { title: '名称', dataIndex: 'name', ellipsis: true },
          { title: '专业', dataIndex: 'discipline', width: 88, ellipsis: true },
          { title: 'slug', dataIndex: 'slug', ellipsis: true, render: (s) => s || '—' },
          {
            title: '类型',
            dataIndex: 'is_builtin',
            width: 100,
            render: (b: boolean) => (b ? <Tag>内置</Tag> : <Tag color="blue">自定义</Tag>),
          },
          {
            title: '操作',
            key: 'actions',
            width: 200,
            render: (_, row) => (
              <Space size="small">
                <Button type="link" size="small" onClick={() => openEdit(row)}>
                  {row.is_builtin ? '查看' : '编辑'}
                </Button>
                {!row.is_builtin && (
                  <Popconfirm
                    title="确定删除该配置？"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => deleteMut.mutate(row.id)}
                  >
                    <Button type="link" size="small" danger loading={deleteMut.isPending}>
                      删除
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={modalMode === 'create' ? '新增语义配置' : readonly ? '查看内置配置' : '编辑语义配置'}
        open={modalMode !== 'closed'}
        onCancel={closeModal}
        closable={false}
        maskClosable={false}
        keyboard={false}
        width={880}
        destroyOnClose
        footer={
          readonly ? (
            <Button onClick={closeModal}>关闭</Button>
          ) : (
            <Space>
              <Button onClick={closeModal}>取消</Button>
              <Button
                type="primary"
                loading={createMut.isPending || updateMut.isPending || loadingDetail}
                onClick={() => {
                  if (modalMode === 'create') createMut.mutate()
                  else updateMut.mutate()
                }}
              >
                保存
              </Button>
            </Space>
          )
        }
      >
        <Form form={form} layout="vertical" disabled={readonly || loadingDetail}>
          <Form.Item
            name="name"
            label="配置名称"
            rules={readonly ? [] : [{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="如：建筑技术标" maxLength={255} />
          </Form.Item>
          <Form.Item name="slug" label="slug（可选）">
            <Input placeholder="唯一标识，可空" maxLength={128} />
          </Form.Item>
          <Form.Item
            name="discipline"
            label="专业"
            rules={readonly ? [] : [{ required: true, message: '请选择专业' }]}
          >
            <Select
              placeholder="选择主专业"
              options={disciplineOptions.map((d) => ({ label: d, value: d }))}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
            各槽位输入框旁可点「范例」查看压缩示意；点「智能生成」将按配置名称与专业对照系统内置提示词调用大模型生成完整覆盖文案（须配置
            API Key）。留空表示不覆盖默认；填写完整内容并保存后才会写入该槽位。
          </Text>
          {!readonly && (
            <div style={{ marginBottom: designTokens.marginMD }}>
              <Button type="primary" loading={genAllLoading} onClick={handleGenerateAll}>
                一键智能生成全部槽位
              </Button>
            </div>
          )}
          <div style={{ maxHeight: 480, overflowY: 'auto', paddingRight: 8 }}>
            {slotFields.map(({ key, title }) => {
              const row = getSemanticSlotModalRow(key, title)
              return (
                <div key={key} style={{ marginBottom: designTokens.marginLG }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: designTokens.marginSM,
                      marginBottom: designTokens.marginXXS,
                    }}
                  >
                    <Text strong style={{ marginBottom: 0 }}>
                      {row.label}
                    </Text>
                    <Space size="small" wrap>
                      <Button
                        type="link"
                        size="small"
                        style={{ padding: 0, height: 'auto' }}
                        onClick={() =>
                          setExampleModal({
                            open: true,
                            title: row.label,
                            content: row.previewInBox,
                          })
                        }
                      >
                        范例
                      </Button>
                      {!readonly && (
                        <Button
                          type="link"
                          size="small"
                          style={{ padding: 0, height: 'auto' }}
                          loading={genSlotKey === key}
                          onClick={() => handleGenerateOne(key, row.label)}
                        >
                          智能生成
                        </Button>
                      )}
                    </Space>
                  </div>
                  <Text type="secondary" style={{ display: 'block', fontSize: 11, marginBottom: designTokens.marginXS }}>
                    自定义覆盖（可选）
                  </Text>
                  <Form.Item name={['semantic_overrides', key]} noStyle>
                    <Input.TextArea
                      autoSize={{ minRows: 3, maxRows: 20 }}
                      placeholder="留空则使用系统内置默认；填写完整提示词后保存即写入该槽位"
                      style={{ fontSize: 13 }}
                    />
                  </Form.Item>
                </div>
              )
            })}
          </div>
        </Form>
      </Modal>

      <Modal
        title={`范例 · ${exampleModal.title}`}
        open={exampleModal.open}
        onCancel={() => setExampleModal((s) => ({ ...s, open: false }))}
        width={720}
        destroyOnClose
        footer={
          <Space>
            <Button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(exampleModal.content)
                  message.success('已复制到剪贴板')
                } catch {
                  message.warning('复制失败，请直接在文本框中选中文本复制')
                }
              }}
            >
              复制全文
            </Button>
            <Button type="primary" onClick={() => setExampleModal((s) => ({ ...s, open: false }))}>
              关闭
            </Button>
          </Space>
        }
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM, fontSize: 12 }}>
          以下为压缩示意，与系统内置默认在细节上可能不完全一致；可直接选中复制或点「复制全文」。
        </Text>
        <Input.TextArea
          readOnly
          value={exampleModal.content}
          autoSize={{ minRows: 12, maxRows: 22 }}
          style={{ fontSize: 13, lineHeight: 1.65 }}
        />
      </Modal>
    </div>
  )
}
