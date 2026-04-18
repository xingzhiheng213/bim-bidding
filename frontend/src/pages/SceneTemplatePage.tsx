import { useQuery } from '@tanstack/react-query'
import { Alert, Spin, Typography } from 'antd'
import SemanticProfilesSection from '../components/SemanticProfilesSection'
import { getPromptCatalog } from '../api/settings'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Title, Paragraph } = Typography

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
        在此管理语义配置（Prompt Profile）：新增、编辑、智能生成与删除自定义配置。
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
    </div>
  )
}
