import { expect, it } from 'vitest'
import { applyTheme, nextThemeChoice, readThemeChoice, resolveTheme, saveThemeChoice, themeStorageKey } from './theme'

function memoryStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial))
  return { getItem: (key: string) => map.get(key) ?? null, setItem: (key: string, value: string) => { map.set(key, value) }, map }
}

it('falls back to system when nothing or garbage is stored', () => {
  expect(readThemeChoice(memoryStorage())).toBe('system')
  expect(readThemeChoice(memoryStorage({ [themeStorageKey]: 'blue' }))).toBe('system')
  expect(readThemeChoice(memoryStorage({ [themeStorageKey]: 'dark' }))).toBe('dark')
})

it('resolves system against the OS preference and flips from what is on screen', () => {
  expect(resolveTheme('system', true)).toBe('dark')
  expect(resolveTheme('system', false)).toBe('light')
  expect(resolveTheme('light', true)).toBe('light')
  expect(nextThemeChoice('system', true)).toBe('light')
  expect(nextThemeChoice('system', false)).toBe('dark')
  expect(nextThemeChoice('dark', false)).toBe('light')
})

it('remembers the choice and marks the document root', () => {
  const storage = memoryStorage()
  saveThemeChoice('dark', storage)
  expect(storage.map.get(themeStorageKey)).toBe('dark')
  applyTheme('dark')
  expect(document.documentElement.dataset.theme).toBe('dark')
  applyTheme('light')
  expect(document.documentElement.dataset.theme).toBe('light')
})
