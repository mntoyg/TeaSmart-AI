export type ThemeChoice = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export const themeStorageKey = 'teasmart.theme.v1'

export function readThemeChoice(storage: Pick<Storage, 'getItem'> | undefined = safeStorage()): ThemeChoice {
  const value = storage?.getItem(themeStorageKey)
  return value === 'light' || value === 'dark' || value === 'system' ? value : 'system'
}

export function saveThemeChoice(choice: ThemeChoice, storage: Pick<Storage, 'setItem'> | undefined = safeStorage()) {
  try { storage?.setItem(themeStorageKey, choice) } catch { /* private mode: the choice lasts for this visit only */ }
}

export function resolveTheme(choice: ThemeChoice, prefersDark: boolean): ResolvedTheme {
  if (choice === 'system') return prefersDark ? 'dark' : 'light'
  return choice
}

/** The next choice when the user taps the toggle: it flips what is on screen now. */
export function nextThemeChoice(current: ThemeChoice, prefersDark: boolean): ThemeChoice {
  return resolveTheme(current, prefersDark) === 'dark' ? 'light' : 'dark'
}

export function systemPrefersDark(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function applyTheme(theme: ResolvedTheme, root: HTMLElement = document.documentElement) {
  root.dataset.theme = theme
  root.style.colorScheme = theme
  const meta = root.ownerDocument.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (meta) meta.content = theme === 'dark' ? '#0f1f17' : '#193c2b'
}

function safeStorage(): Storage | undefined {
  try { return typeof window !== 'undefined' ? window.localStorage : undefined } catch { return undefined }
}
