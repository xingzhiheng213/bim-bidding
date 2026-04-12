import { useQuery } from '@tanstack/react-query'
import { Alert, Collapse, Input, Spin, Typography } from 'antd'
import SemanticProfilesSection from '../components/SemanticProfilesSection'
import { getPromptCatalog, type PromptCatalogItem } from '../api/settings'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Text, Paragraph } = Typography

const STEP_ORDER = [
  'runtime',
  'analyze',
  'params',
  'framework',
  'chapter_outline',
  'chapter_content',
  'chapter_regenerate',
  'review',
] as const

const STEP_LABELS: Record<(typeof STEP_ORDER)[number], string> = {
  runtime: '运行时与其它契约',
  analyze: '分析',
  params: '参数提取',
  framework: '框架生成',
  chapter_outline: '章节 · 小节大纲',
  chapter_content: '章节 · 正文',
  chapter_regenerate: '章节 · 重生成',
  review: '校审',
}

function groupByStep(items: PromptCatalogItem[]): Map<string, PromptCatalogItem[]> {
  const m = new Map<string, PromptCatalogItem[]>()
  for (const it of items) {
    const list = m.get(it.step) ?? []
    list.push(it)
    m.set(it.step, list)
  }
  return m
}

function renderLayer(items: PromptCatalogItem[]) {
  const grouped = groupByStep(items)
  return (
    <div style={{ marginTop: designTokens.marginMD }}>
      {STEP_ORDER.map((step) => {
        const list = grouped.get(step)
        if (!list?.length) return null
        return (
          <div key={step} style={{ marginBottom: designTokens.marginLG }}>
            <Text strong style={{ fontSize: designTokens.fontSize }}>
              {STEP_LABELS[step]}
            </Text>
            {list.map((it) => (
              <div key={it.id} style={{ marginTop: designTokens.marginSM }}>
                <Text type="secondary">{it.title}</Text>
                <Input.TextArea
                  readOnly
                  value={it.content}
                  autoSize={{ minRows: 6, maxRows: 40 }}
                  style={{
                    marginTop: designTokens.marginXS,
                    fontFamily: 'ui-monospace, monospace',
                    fontSize: 12,
                  }}
                />
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

export default function SceneTemplatePage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['settings', 'prompt-catalog'],
    queryFn: getPromptCatalog,
  })

  return (
    <div style={{ maxWidth: 1100 }}>
      <Title level={3} style={{ marginTop: 0 }}>
        场景与模板
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: designTokens.marginMD }}>
        下方「语义配置」可新增/编辑自定义 Profile；契约层与内置语义全文仍以只读方式展示，便于对照审查。
      </Paragraph>

      {data?.semantic_items && data.semantic_items.length > 0 && (
        <SemanticProfilesSection semanticItems={data.semantic_items} />
      )}

      {isLoading && !data && (
        <div style={{ padding: designTokens.marginXL, textAlign: 'center' }}>
          <Spin size="large" />
        </div>
      )}
      {isError && (
        <Alert
          type="error"
          showIcon
          message="加载失败"
          description={error instanceof Error ? error.message : String(error)}
        />
      )}
      {data && (
        <Collapse
          defaultActiveKey={['contract', 'semantic']}
          items={[
            {
              key: 'contract',
              label: '契约层（JSON 键、占位符、用户槽位模板、输出结构、运行时约定）',
              children: renderLayer(data.contract_items),
            },
            {
              key: 'semantic',
              label: '语义层（专家人设、分析范围、写作与审查叙述）',
              children: renderLayer(data.semantic_items),
            },
          ]}
        />
      )}
    </div>
  )
}
