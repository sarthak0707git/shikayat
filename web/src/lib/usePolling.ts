import { useEffect, useRef, useState } from 'react'

/**
 * Load now, then again every `ms`, so a merged report shows up on the board by itself.
 * Old data stays on screen while the next load runs; `key` restarts the cycle.
 */
export function usePolling<T>(load: () => Promise<T>, key: string, ms = 8000) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    let alive = true
    const tick = async () => {
      if (document.hidden) return
      try {
        const next = await loadRef.current()
        if (!alive) return
        setData(next)
        setError(null)
      } catch (cause) {
        if (alive) setError(cause instanceof Error ? cause.message : 'Something went wrong.')
      }
    }
    void tick()
    const timer = setInterval(tick, ms)
    const onVisible = () => void tick()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      alive = false
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [key, ms, nonce])

  return { data, error, refresh: () => setNonce((n) => n + 1) }
}
