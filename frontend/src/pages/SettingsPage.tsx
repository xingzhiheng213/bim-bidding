import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Checkbox, Input, InputNumber, message, Select, Spin, Tag, Typography } from 'antd'
import {
  type ExportFormatConfig,
  getSettingsExportFormat,
  getSettingsLlm,
  getSettingsModels,
  postSettingsExportFormat,
  postSettingsLlm,
  postSettingsModels,
} from '../api/settings'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text } = Typography

const STEP_LABELS: Record<string, string> = {
  analyze: '分析',
  params: '参数提取',
  framework: '框架生成',
  chapters: '按章生成',
}

const PROVIDERS = [
  { key: 'deepseek', label: 'DeepSeek', defaultBaseUrl: 'https://api.deepseek.com' },
  { key: 'zhipu', label: '智谱', defaultBaseUrl: 'https://open.bigmodel.cn/api/paas/v4' },
] as const

const DEFAULT_EXPORT_FORMAT: ExportFormatConfig = {
  heading_1_font: '宋体',
  heading_1_size_pt: 22,
  heading_2_font: '宋体',
  heading_2_size_pt: 16,
  heading_3_font: '宋体',
  heading_3_size_pt: 14,
  body_font: '宋体',
  body_size_pt: 12,
  table_font: '宋体',
  table_size_pt: 12,
  first_line_indent_pt: 24,
  line_spacing: 1.5,
}

const LINE_SPACING_OPTIONS = [
  { label: '1 倍', value: 1.0 },
  { label: '1.5 倍', value: 1.5 },
]

function SettingsPage() {
  const queryClient = useQueryClient()
  const [inputByProvider, setInputByProvider] = useState<Record<string, string>>({})
  const [baseUrlByProvider, setBaseUrlByProvider] = useState<Record<string, string>>({})
  const [exportFormat, setExportFormat] = useState<ExportFormatConfig>(DEFAULT_EXPORT_FORMAT)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['settings', 'llm'],
    queryFn: getSettingsLlm,
  })

  const {
    data: modelsData,
    isLoading: modelsLoading,
    isError: modelsError,
    error: modelsErr,
  } = useQuery({
    queryKey: ['settings', 'models'],
    queryFn: getSettingsModels,
  })

  const { data: exportFormatData, isLoading: exportFormatLoading } = useQuery({
    queryKey: ['settings', 'export-format'],
    queryFn: getSettingsExportFormat,
  })

  useEffect(() => {
    if (exportFormatData) {
      setExportFormat({
        ...DEFAULT_EXPORT_FORMAT,
        ...exportFormatData,
      })
    }
  }, [exportFormatData])

  const saveExportFormatMutation = useMutation({
    mutationFn: postSettingsExportFormat,
    onSuccess: (res) => {
      message.success('导出格式已保存')
      setExportFormat((prev) => ({ ...prev, ...res }))
      queryClient.invalidateQueries({ queryKey: ['settings', 'export-format'] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '保存失败'
      message.error(detail)
    },
  })

  const saveModelsMutation = useMutation({
    mutationFn: postSettingsModels,
    onSuccess: () => {
      message.success('模型配置已保存')
      queryClient.invalidateQueries({ queryKey: ['settings', 'models'] })
    },
    onError: (e: unknown) => {
      const detail =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '保存失败'
      message.error(detail)
    },
  })

  const saveMutation = useMutation({
    mutationFn: ({
      provider,
      apiKey,
      baseUrl,
    }: {
      provider: string
      apiKey: string | undefined
      baseUrl: string | undefined
    }) => postSettingsLlm(provider, apiKey, baseUrl),
    onSuccess: (_, { provider }) => {
      message.success('已保存')
      setInputByProvider((prev) => ({ ...prev, [provider]: '' }))
      setBaseUrlByProvider((prev) => ({ ...prev, [provider]: '' }))
      queryClient.invalidateQueries({ queryKey: ['settings', 'llm'] })
    },
    onError: (e: unknown) => {
      const msg =
        e && typeof e === 'object' && 'response' in e && e.response && typeof e.response === 'object' && 'data' in e.response && e.response.data && typeof e.response.data === 'object' && 'detail' in e.response.data
          ? String((e.response.data as { detail: unknown }).detail)
          : e instanceof Error
            ? e.message
            : '保存失败'
      const detail =
        msg === 'Network Error'
          ? '无法连接后端，请确认后端已启动（默认 http://localhost:8001），并检查前端 VITE_API_BASE 与网络。'
          : msg
      message.error(detail)
    },
  })

  const getProviderStatus = (key: string) =>
    data?.providers?.find((p) => p.provider === key)

  const contentMaxWidth = 640

  return (
    <div style={{ maxWidth: contentMaxWidth, width: '100%' }}>
      <Title level={2} style={{ marginBottom: designTokens.marginLG }}>
        设置
      </Title>

      <Card title="大模型 API" style={{ marginBottom: designTokens.marginLG, width: '100%' }}>
        {isLoading && <Spin size="small" style={{ marginBottom: designTokens.marginSM }} />}
        {isError && (
          <Text type="danger" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
            {error instanceof Error && error.message === 'Network Error'
              ? '无法连接后端，请确认后端已启动（默认 http://localhost:8001），并检查前端 VITE_API_BASE 与网络。'
              : error instanceof Error
                ? error.message
                : String(error)}
          </Text>
        )}
        {data?.providers &&
          PROVIDERS.map(({ key, label, defaultBaseUrl }) => {
            const status = getProviderStatus(key)
            const configured = status?.configured ?? false
            const maskedKey = status?.masked_key ?? null
            const currentBaseUrl = status?.base_url ?? null
            const keyValue = inputByProvider[key] ?? ''
            const baseUrlValue = baseUrlByProvider[key] ?? currentBaseUrl ?? ''
            const hasKeyInput = keyValue.trim() !== ''
            const hasBaseUrlInput = baseUrlValue !== (currentBaseUrl ?? '')
            const canSave = hasKeyInput || hasBaseUrlInput
            return (
              <div
                key={key}
                style={{
                  marginBottom: designTokens.marginLG,
                  paddingBottom: designTokens.marginLG,
                  borderBottom: key !== PROVIDERS[PROVIDERS.length - 1].key ? `1px solid ${designTokens.colorBorderSecondary}` : undefined,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: designTokens.marginXS, marginBottom: designTokens.marginSM }}>
                  <Text strong>{label}</Text>
                  {configured ? (
                    <Tag color="success">已配置</Tag>
                  ) : (
                    <Tag>未配置</Tag>
                  )}
                  {configured && maskedKey != null && (
                    <Text type="secondary" style={{ fontSize: 12 }}>{maskedKey}</Text>
                  )}
                </div>
                <div style={{ marginTop: designTokens.marginXS }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginXXS }}>
                    API Key
                  </Text>
                  <div style={{ display: 'flex', gap: designTokens.marginXS, flexWrap: 'wrap', alignItems: 'center' }}>
                    <Input.Password
                      placeholder="留空表示不修改"
                      value={keyValue}
                      onChange={(e) =>
                        setInputByProvider((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      style={{ width: 400 }}
                      allowClear
                    />
                  </div>
                </div>
                <div style={{ marginTop: designTokens.marginSM }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginXXS }}>
                    Base URL（可选，留空使用默认）
                  </Text>
                  <Input
                    placeholder={defaultBaseUrl}
                    value={baseUrlValue}
                    onChange={(e) =>
                      setBaseUrlByProvider((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                    style={{ width: 400 }}
                    allowClear
                  />
                </div>
                <div style={{ marginTop: designTokens.marginXS, display: 'flex', alignItems: 'center', gap: designTokens.marginXS }}>
                  <Button
                    type="primary"
                    loading={saveMutation.isPending}
                    onClick={() => {
                      if (!canSave) {
                        message.warning('请至少填写 API Key 或 Base URL 后再保存')
                        return
                      }
                      saveMutation.mutate({
                        provider: key,
                        apiKey: keyValue.trim() || undefined,
                        baseUrl: hasBaseUrlInput ? baseUrlValue : undefined,
                      })
                    }}
                    disabled={!canSave}
                  >
                    保存
                  </Button>
                </div>
              </div>
            )
          })}
      </Card>

      <Card title="模型配置" style={{ marginBottom: designTokens.marginLG, width: '100%' }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
          选择各步骤使用的大模型；未单独选择的步骤使用「默认模型」。模型名会对应到供应商（如 glm-4.7 → 智谱），请先在「大模型 API」中配置对应 API Key。
        </Text>
        {modelsLoading && <Spin size="small" style={{ marginBottom: designTokens.marginSM }} />}
        {modelsError && (
          <Text type="danger" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
            {modelsErr instanceof Error ? modelsErr.message : String(modelsErr)}
          </Text>
        )}
        {modelsData && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: designTokens.margin }}>
              <div style={{ width: 100, minWidth: 100, flexShrink: 0 }}>
                <Text strong>默认模型</Text>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: designTokens.marginXS, flex: 1 }}>
                <Select
                  style={{ width: 280 }}
                  value={modelsData.default_model}
                  onChange={(v) =>
                    saveModelsMutation.mutate({
                      default_model: v ?? undefined,
                      analyze_model: modelsData.steps.analyze ?? null,
                      params_model: modelsData.steps.params ?? null,
                      framework_model: modelsData.steps.framework ?? null,
                      chapters_model: modelsData.steps.chapters ?? null,
                    })
                  }
                  loading={saveModelsMutation.isPending}
                  options={modelsData.supported_models.map((m) => ({
                    label: `${m.name} (${m.provider})`,
                    value: m.id,
                  }))}
                />
              </div>
            </div>
            {(['analyze', 'params', 'framework', 'chapters'] as const).map((stepKey) => {
              const stepModel = modelsData.steps[stepKey]
              const effective = stepModel || modelsData.default_model
              const stepField = `${stepKey}_model` as const
              return (
                <div key={stepKey} style={{ display: 'flex', alignItems: 'center', marginBottom: designTokens.marginSM }}>
                  <div style={{ width: 100, minWidth: 100, flexShrink: 0 }}>
                    <Text>{STEP_LABELS[stepKey]}</Text>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: designTokens.marginXS, flex: 1 }}>
                    <Select
                      style={{ width: 280 }}
                      value={stepModel ?? ''}
                      placeholder="使用默认"
                      allowClear
                      onChange={(v) => {
                        const payload = {
                          default_model: modelsData.default_model,
                          analyze_model: modelsData.steps.analyze ?? null,
                          params_model: modelsData.steps.params ?? null,
                          framework_model: modelsData.steps.framework ?? null,
                          chapters_model: modelsData.steps.chapters ?? null,
                        }
                        payload[stepField] = v ?? null
                        saveModelsMutation.mutate(payload)
                      }}
                      loading={saveModelsMutation.isPending}
                      options={[
                        { label: '使用默认', value: '' },
                        ...modelsData.supported_models.map((m) => ({
                          label: `${m.name} (${m.provider})`,
                          value: m.id,
                        })),
                      ]}
                    />
                    {effective && (
                      <Text type="secondary">
                        当前：{effective}
                      </Text>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      <Card title="导出格式" style={{ marginBottom: designTokens.marginLG, width: '100%' }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: designTokens.marginSM }}>
          配置导出 Word 文档的标题、正文、表格字体与字号，以及首行缩进、行距。
        </Text>
        {exportFormatLoading && <Spin size="small" style={{ marginBottom: designTokens.marginSM }} />}
        {!exportFormatLoading && (
          <div>
            {[
              { key: 'heading_1', label: '一级标题', fontKey: 'heading_1_font', sizeKey: 'heading_1_size_pt' },
              { key: 'heading_2', label: '二级标题', fontKey: 'heading_2_font', sizeKey: 'heading_2_size_pt' },
              { key: 'heading_3', label: '三级标题', fontKey: 'heading_3_font', sizeKey: 'heading_3_size_pt' },
              { key: 'body', label: '正文', fontKey: 'body_font', sizeKey: 'body_size_pt' },
              { key: 'table', label: '表格内', fontKey: 'table_font', sizeKey: 'table_size_pt' },
            ].map(({ key, label, fontKey, sizeKey }) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', marginBottom: designTokens.marginSM }}>
                <div style={{ width: 140, minWidth: 140, flexShrink: 0 }}>
                  <Text>{label}字体</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: designTokens.marginXS, flex: 1 }}>
                  <Input
                    style={{ width: 120 }}
                    value={exportFormat[fontKey as keyof ExportFormatConfig] ?? ''}
                    onChange={(e) =>
                      setExportFormat((prev) => ({ ...prev, [fontKey]: e.target.value }))
                    }
                  />
                  <Text type="secondary">字号</Text>
                  <InputNumber
                    min={8}
                    max={72}
                    step={1}
                    style={{ width: 80 }}
                    value={exportFormat[sizeKey as keyof ExportFormatConfig] ?? 12}
                    onChange={(v) =>
                      setExportFormat((prev) => ({ ...prev, [sizeKey]: v ?? undefined }))
                    }
                  />
                </div>
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: designTokens.marginSM }}>
              <div style={{ width: 140, minWidth: 140, flexShrink: 0 }}>
                <Text>首行缩进</Text>
              </div>
              <div style={{ flex: 1 }}>
                <Checkbox
                  checked={(exportFormat.first_line_indent_pt ?? 0) > 0}
                  onChange={(e) =>
                    setExportFormat((prev) => ({
                      ...prev,
                      first_line_indent_pt: e.target.checked ? 24 : 0,
                    }))
                  }
                >
                  首行缩进两字符
                </Checkbox>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: designTokens.marginSM }}>
              <div style={{ width: 140, minWidth: 140, flexShrink: 0 }}>
                <Text>行距</Text>
              </div>
              <div style={{ flex: 1 }}>
                <Select
                  style={{ width: 120 }}
                  value={exportFormat.line_spacing ?? 1.5}
                  onChange={(v) =>
                    setExportFormat((prev) => ({ ...prev, line_spacing: v ?? undefined }))
                  }
                  options={LINE_SPACING_OPTIONS}
                />
              </div>
            </div>
            <div style={{ marginTop: designTokens.margin }}>
              <Button
                type="primary"
                loading={saveExportFormatMutation.isPending}
                onClick={() => {
                  saveExportFormatMutation.mutate({
                    heading_1_font: exportFormat.heading_1_font,
                    heading_1_size_pt: exportFormat.heading_1_size_pt,
                    heading_2_font: exportFormat.heading_2_font,
                    heading_2_size_pt: exportFormat.heading_2_size_pt,
                    heading_3_font: exportFormat.heading_3_font,
                    heading_3_size_pt: exportFormat.heading_3_size_pt,
                    body_font: exportFormat.body_font,
                    body_size_pt: exportFormat.body_size_pt,
                    table_font: exportFormat.table_font,
                    table_size_pt: exportFormat.table_size_pt,
                    first_line_indent_pt: exportFormat.first_line_indent_pt ?? 0,
                    line_spacing: exportFormat.line_spacing,
                  })
                }}
              >
                保存
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

export default SettingsPage
