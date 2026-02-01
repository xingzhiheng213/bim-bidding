import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button, Input, Layout, message, Select, Spin, Typography } from 'antd'
import { getSettingsLlm, getSettingsModels, postSettingsLlm, postSettingsModels } from '../api/settings'
import '../App.css'

const { Header, Content } = Layout
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

function SettingsPage() {
  const queryClient = useQueryClient()
  const [inputByProvider, setInputByProvider] = useState<Record<string, string>>({})
  const [baseUrlByProvider, setBaseUrlByProvider] = useState<Record<string, string>>({})

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
          ? '无法连接后端，请确认后端已启动（默认 http://localhost:8000），并检查前端 VITE_API_BASE 与网络。'
          : msg
      message.error(detail)
    },
  })

  const getProviderStatus = (key: string) =>
    data?.providers?.find((p) => p.provider === key)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>
          BIM 标书生成
        </Title>
        <Link to="/" style={{ color: '#fff', marginLeft: 24 }}>
          首页
        </Link>
        <Link to="/settings" style={{ color: '#fff', marginLeft: 16 }}>
          设置
        </Link>
        <Link to="/compare" style={{ color: '#fff', marginLeft: 16 }}>
          对比
        </Link>
      </Header>
      <Content style={{ padding: 24 }}>
        <Title level={2} style={{ marginBottom: 16 }}>
          设置
        </Title>
        <Title level={5} style={{ marginBottom: 12 }}>
          大模型 API
        </Title>
        {isLoading && <Spin size="small" />}
        {isError && (
          <Text type="danger">
            {error instanceof Error && error.message === 'Network Error'
              ? '无法连接后端，请确认后端已启动（默认 http://localhost:8000），并检查前端 VITE_API_BASE 与网络。'
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
              <div key={key} style={{ marginBottom: 28, maxWidth: 560 }}>
                <Text strong>{label}</Text>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                    API Key
                  </Text>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <Input.Password
                      placeholder="留空表示不修改"
                      value={keyValue}
                      onChange={(e) =>
                        setInputByProvider((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      style={{ width: 280 }}
                      allowClear
                    />
                  </div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
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
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
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
                  {configured && (
                    <Text type="secondary">
                      已配置 {maskedKey != null ? `（${maskedKey}）` : ''}
                    </Text>
                  )}
                </div>
              </div>
            )
          })}

        <Title level={5} style={{ marginTop: 32, marginBottom: 12 }}>
          模型配置
        </Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          选择各步骤使用的大模型；未单独选择的步骤使用「默认模型」。模型名会对应到供应商（如 glm-4.7 → 智谱），请先在「大模型 API」中配置对应 API Key。
        </Text>
        {modelsLoading && <Spin size="small" />}
        {modelsError && (
          <Text type="danger">
            {modelsErr instanceof Error ? modelsErr.message : String(modelsErr)}
          </Text>
        )}
        {modelsData && (
          <div style={{ maxWidth: 560 }}>
            <div style={{ marginBottom: 16 }}>
              <Text strong>默认模型</Text>
              <Select
                style={{ width: 280, marginLeft: 12 }}
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
            {(['analyze', 'params', 'framework', 'chapters'] as const).map((stepKey) => {
              const stepModel = modelsData.steps[stepKey]
              const effective = stepModel || modelsData.default_model
              const stepField = `${stepKey}_model` as const
              return (
                <div key={stepKey} style={{ marginBottom: 12 }}>
                  <Text>{STEP_LABELS[stepKey]}</Text>
                  <Select
                    style={{ width: 280, marginLeft: 12 }}
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
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      当前：{effective}
                    </Text>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </Content>
    </Layout>
  )
}

export default SettingsPage
