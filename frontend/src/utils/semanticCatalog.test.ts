import { describe, expect, it } from 'vitest'
import { catalogIdToSemanticSlotKey } from './semanticCatalog'

describe('catalogIdToSemanticSlotKey', () => {
  it('parses semantic.* ids', () => {
    expect(catalogIdToSemanticSlotKey('semantic.analyze_system')).toBe('analyze_system')
  })
  it('returns null for non-semantic ids', () => {
    expect(catalogIdToSemanticSlotKey('contract.foo')).toBeNull()
    expect(catalogIdToSemanticSlotKey('')).toBeNull()
  })
})
