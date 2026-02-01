import type { CSSProperties } from 'react'
import type { DiffItem } from '../api/compare'
import { designTokens } from '../theme/tokens'

function getDelStyle(): CSSProperties {
  return {
    backgroundColor: `${designTokens.colorError}20`,
    color: designTokens.colorError,
    textDecoration: 'line-through',
    whiteSpace: 'pre-wrap',
    fontSize: designTokens.fontSize,
    lineHeight: designTokens.lineHeight,
  }
}

function getAddStyle(): CSSProperties {
  return {
    backgroundColor: `${designTokens.colorSuccess}20`,
    color: designTokens.colorSuccess,
    whiteSpace: 'pre-wrap',
    fontSize: designTokens.fontSize,
    lineHeight: designTokens.lineHeight,
  }
}

const equalStyle: CSSProperties = {
  whiteSpace: 'pre-wrap',
  fontSize: designTokens.fontSize,
  lineHeight: designTokens.lineHeight,
}

export interface DiffViewProps {
  diff: DiffItem[]
  className?: string
  style?: CSSProperties
}

export function DiffView({ diff, className, style }: DiffViewProps) {
  const delStyle = getDelStyle()
  const addStyle = getAddStyle()

  if (diff.length === 0) {
    return (
      <div className={className} style={style}>
        <span style={{ color: designTokens.colorTextTertiary }}>无差异</span>
      </div>
    )
  }
  return (
    <div
      className={className}
      style={{
        ...style,
        whiteSpace: 'pre-wrap',
        fontSize: designTokens.fontSize,
        lineHeight: designTokens.lineHeight,
      }}
    >
      {diff.map((item, i) => (
        <span
          key={i}
          style={
            item.type === 'del'
              ? delStyle
              : item.type === 'add'
                ? addStyle
                : equalStyle
          }
        >
          {item.text}
        </span>
      ))}
    </div>
  )
}
