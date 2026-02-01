import type { CSSProperties } from 'react'
import type { DiffItem } from '../api/compare'

const delStyle: CSSProperties = {
  backgroundColor: '#ffcccc',
  textDecoration: 'line-through',
  whiteSpace: 'pre-wrap',
}

const addStyle: CSSProperties = {
  backgroundColor: '#ccffcc',
  whiteSpace: 'pre-wrap',
}

export interface DiffViewProps {
  diff: DiffItem[]
  className?: string
  style?: CSSProperties
}

export function DiffView({ diff, className, style }: DiffViewProps) {
  if (diff.length === 0) {
    return (
      <div className={className} style={style}>
        <span style={{ color: '#888' }}>无差异</span>
      </div>
    )
  }
  return (
    <div className={className} style={{ ...style, whiteSpace: 'pre-wrap' }}>
      {diff.map((item, i) => (
        <span
          key={i}
          style={
            item.type === 'del'
              ? delStyle
              : item.type === 'add'
                ? addStyle
                : { whiteSpace: 'pre-wrap' }
          }
        >
          {item.text}
        </span>
      ))}
    </div>
  )
}
