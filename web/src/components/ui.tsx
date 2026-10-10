import { useEffect, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import type { Severity, Status } from '../types'

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(' ')
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'md' | 'lg'
}

const BUTTON = {
  primary: 'bg-ink text-white hover:bg-zinc-800 disabled:bg-zinc-900/10 disabled:text-zinc-500',
  secondary: 'bg-white text-zinc-900 ring-1 ring-zinc-900/10 hover:bg-zinc-50 disabled:text-zinc-400',
  ghost: 'text-zinc-700 hover:bg-zinc-900/5 hover:text-zinc-900 disabled:text-zinc-400',
}

export function Button({ variant = 'secondary', size = 'md', className, type = 'button', ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        'press inline-flex shrink-0 items-center justify-center gap-2 rounded-full text-sm font-medium',
        'transition-colors duration-150 disabled:cursor-not-allowed',
        size === 'lg' ? 'h-11 px-5' : 'h-9 px-4',
        BUTTON[variant],
        className,
      )}
      {...rest}
    />
  )
}

// Severity colours are used for severity and nothing else.
const SEVERITY_DOT: Record<Severity, string> = {
  urgent: 'bg-red-600',
  high: 'bg-orange-500',
  medium: 'bg-amber-500',
  low: 'bg-slate-400',
}

export const SEVERITY_FILL: Record<Severity, string> = {
  urgent: '#dc2626',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#94a3b8',
}

export function SeverityTag({ severity, label = true }: { severity: Severity; label?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium capitalize text-zinc-700">
      <span className={cx('size-2 rounded-full', SEVERITY_DOT[severity])} aria-hidden="true" />
      {label ? severity : <span className="sr-only">{severity}</span>}
    </span>
  )
}

const STATUS: Record<Status, { text: string; className: string }> = {
  open: { text: 'Open', className: 'bg-slate-100 text-slate-700' },
  in_progress: { text: 'In progress', className: 'bg-blue-50 text-blue-700' },
  resolved: { text: 'Resolved', className: 'bg-green-50 text-green-700' },
}

export function StatusPill({ status }: { status: Status }) {
  const { text, className } = STATUS[status] ?? STATUS.open
  return (
    <span className={cx('inline-flex h-6 items-center rounded-full px-2 text-xs font-medium whitespace-nowrap', className)}>
      {text}
    </span>
  )
}

/** Decides once, when it mounts, whether to play the bump. */
function Tick({ animate, children }: { animate: boolean; children: ReactNode }) {
  const [on] = useState(animate)
  return <span className={on ? 'bump' : undefined}>{children}</span>
}

/**
 * The number of students behind a complaint. Re-keyed on change so the bump replays;
 * it stays still on first paint unless `bumpOnMount` is set.
 */
export function CountBadge({ count, className, bumpOnMount = false }: { count: number; className?: string; bumpOnMount?: boolean }) {
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
  }, [])
  return (
    <span
      className={cx(
        'inline-flex h-6 min-w-6 items-center justify-center overflow-hidden rounded-full bg-zinc-100 px-2',
        'text-xs font-semibold text-zinc-900 tabular-nums',
        className,
      )}
      title={`${count} ${count === 1 ? 'report' : 'reports'}`}
    >
      <Tick key={count} animate={bumpOnMount || mounted.current}>
        {count}
      </Tick>
    </span>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('skeleton', className)} aria-hidden="true" />
}

export function PageHeader({ title, description, children }: { title: string; description: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-6 pt-6 pb-8 sm:pt-10">
      <div className="min-w-0">
        <h1 className="font-display text-4xl leading-[1.02] font-bold tracking-tight text-balance text-ink sm:text-6xl">{title}</h1>
        <p className="mt-3 max-w-[58ch] text-base text-zinc-600">{description}</p>
      </div>
      {children}
    </div>
  )
}

/** Counts to its value: from zero on first paint, from the old number after that. */
export function Ticker({ value, className }: { value: number; className?: string }) {
  const [shown, setShown] = useState(0)
  const current = useRef(0)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      current.current = value
      setShown(value)
      return
    }
    const from = current.current
    const start = performance.now()
    let frame = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 800)
      current.current = Math.round(from + (value - from) * (1 - Math.pow(1 - t, 4)))
      setShown(current.current)
      if (t < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [value])
  return <span className={cx('tabular-nums', className)}>{shown}</span>
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="px-4 py-12 text-center">
      <p className="text-sm font-medium text-zinc-900">{title}</p>
      {hint && <p className="mt-1 text-sm text-zinc-500">{hint}</p>}
    </div>
  )
}
