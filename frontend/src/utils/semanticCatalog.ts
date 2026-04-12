/** Catalog semantic item id is `semantic.{slot_key}` (aligned with backend semantic_slots.catalog_id_for_slot). */
const PREFIX = 'semantic.'

export function catalogIdToSemanticSlotKey(catalogId: string): string | null {
  if (!catalogId.startsWith(PREFIX)) return null
  return catalogId.slice(PREFIX.length)
}
