import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

const STORAGE_KEY = 'bim_selected_profile_id'

function readStoredProfileId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw == null || raw === '') return null
    const v = JSON.parse(raw) as unknown
    if (v === null) return null
    if (typeof v === 'number' && Number.isFinite(v)) return v
    return null
  } catch {
    return null
  }
}

function writeStoredProfileId(id: number | null): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(id))
  } catch {
    // ignore quota / private mode
  }
}

type SelectedProfileContextValue = {
  selectedProfileId: number | null
  setSelectedProfileId: (id: number | null) => void
}

const SelectedProfileContext = createContext<SelectedProfileContextValue | null>(null)

export function SelectedProfileProvider({ children }: { children: ReactNode }) {
  const [selectedProfileId, setState] = useState<number | null>(() => readStoredProfileId())

  const setSelectedProfileId = useCallback((id: number | null) => {
    setState(id)
    writeStoredProfileId(id)
  }, [])

  const value = useMemo(
    () => ({ selectedProfileId, setSelectedProfileId }),
    [selectedProfileId, setSelectedProfileId],
  )

  return (
    <SelectedProfileContext.Provider value={value}>{children}</SelectedProfileContext.Provider>
  )
}

export function useSelectedProfile(): SelectedProfileContextValue {
  const ctx = useContext(SelectedProfileContext)
  if (!ctx) {
    throw new Error('useSelectedProfile must be used within SelectedProfileProvider')
  }
  return ctx
}

/** Ant Design Select: "default" ↔ null, else numeric id string */
export function profileIdToSelectValue(id: number | null): string {
  return id == null ? 'default' : String(id)
}

export function selectValueToProfileId(v: string): number | null {
  if (v === 'default' || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}
