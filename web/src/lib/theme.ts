import { useSyncExternalStore } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'shikayat-theme'
const listeners = new Set<() => void>()

const read = (): Theme => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* private window: the choice just lasts for this visit */
  }
  listeners.forEach((listener) => listener())
}

export function useTheme() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener)
    return () => listeners.delete(listener)
  }, read)
}

// Apply a saved choice before the first paint. Light stays the default: projectors wash out dark screens.
// A link can ask for a theme too: /board?theme=dark.
try {
  const asked = new URLSearchParams(window.location.search).get('theme')
  if (asked === 'dark' || asked === 'light') localStorage.setItem(KEY, asked)
  if (localStorage.getItem(KEY) === 'dark') document.documentElement.dataset.theme = 'dark'
} catch {
  /* no storage: stay light */
}
