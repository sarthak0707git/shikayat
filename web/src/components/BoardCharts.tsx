import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatShortDate } from '../lib/format'
import type { Stats } from '../types'
import { EmptyState, Skeleton } from './ui'

// Same hues as the status pills: open slate, in progress blue, resolved green.
const STATUS_PARTS = [
  { key: 'open', label: 'Open', className: 'bg-slate-400' },
  { key: 'in_progress', label: 'In progress', className: 'bg-blue-500' },
  { key: 'resolved', label: 'Resolved', className: 'bg-green-500' },
] as const

export function ByDomain({ rows }: { rows?: Stats['by_domain'] }) {
  const max = Math.max(1, ...(rows ?? []).map((row) => row.open + row.in_progress + row.resolved))
  return (
    <section className="py-8" aria-labelledby="by-domain">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pb-4">
        <h2 id="by-domain" className="text-sm font-semibold text-zinc-900">
          By domain
        </h2>
        <ul className="flex gap-4" aria-label="Status colours">
          {STATUS_PARTS.map((part) => (
            <li key={part.key} className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-700">
              <span className={`size-2 rounded-full ${part.className}`} aria-hidden="true" />
              {part.label}
            </li>
          ))}
        </ul>
      </div>
      {!rows ? (
        <Skeleton className="h-40" />
      ) : rows.length === 0 ? (
        <EmptyState title="No complaints in this domain" />
      ) : (
        <ul className="flex flex-col gap-3">
          {rows.map((row) => {
            const total = row.open + row.in_progress + row.resolved
            return (
              <li key={row.domain} className="grid grid-cols-[5rem_minmax(0,1fr)_2rem] items-center gap-3 text-sm">
                <span className="truncate text-zinc-700">{row.domain}</span>
                <span
                  className="flex h-2.5 gap-px overflow-hidden rounded-full"
                  style={{ width: `${(total / max) * 100}%` }}
                  role="img"
                  aria-label={`${row.open} open, ${row.in_progress} in progress, ${row.resolved} resolved`}
                >
                  {STATUS_PARTS.map(
                    (part) => row[part.key] > 0 && <span key={part.key} className={part.className} style={{ flexGrow: row[part.key] }} />,
                  )}
                </span>
                <span className="text-right font-semibold text-zinc-900 tabular-nums">{total}</span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export function Daily({ days }: { days?: Stats['daily'] }) {
  const still = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  return (
    <section className="border-t border-zinc-200 py-8" aria-labelledby="daily">
      <h2 id="daily" className="text-sm font-semibold text-zinc-900">
        Reports per day
      </h2>
      <p className="mt-0.5 pb-4 text-xs text-zinc-500">Last 14 days</p>
      {!days ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="h-40 text-xs tabular-nums">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={days} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="#e4e4e7" />
              <XAxis
                dataKey="date"
                tickFormatter={(value: string) => formatShortDate(value)}
                interval={3}
                tickLine={false}
                axisLine={{ stroke: '#e4e4e7' }}
                tick={{ fill: '#71717a' }}
              />
              <YAxis allowDecimals={false} width={28} tickLine={false} axisLine={false} tick={{ fill: '#71717a' }} />
              <Tooltip
                cursor={{ stroke: '#a1a1aa' }}
                labelFormatter={(label) => formatShortDate(String(label))}
                formatter={(value) => [value, 'Reports']}
                contentStyle={{ borderRadius: 10, border: '1px solid #e4e4e7', boxShadow: '0 4px 12px rgb(24 24 27 / 0.08)', fontSize: 12 }}
              />
              <Area
                type="monotone"
                dataKey="reports"
                stroke="#4f46e5"
                strokeWidth={2}
                fill="#4f46e5"
                fillOpacity={0.08}
                isAnimationActive={!still}
                animationDuration={280}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
