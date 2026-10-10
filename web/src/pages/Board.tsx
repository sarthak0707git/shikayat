import { CircleCheck, Flame, Inbox, TrendingUp, type LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { toast } from 'sonner'
import { ByDomain, Daily } from '../components/BoardCharts'
import { Button, CountBadge, cx, EmptyState, PageHeader, SEVERITY_FILL, SeverityTag, Skeleton, StatusPill, Ticker } from '../components/ui'
import { api } from '../lib/api'
import { place, plural, timeAgo } from '../lib/format'
import { usePolling } from '../lib/usePolling'
import { DOMAINS, type Complaint, type Severity, type Stats } from '../types'

const SEVERITIES: Severity[] = ['urgent', 'high', 'medium', 'low']
const SPRING = { type: 'spring', duration: 0.6, bounce: 0.16 } as const

/** Highest priority first; ties go to the issue more students hit, then the most recent. */
function byPriority(a: Complaint, b: Complaint) {
  return (
    b.priority - a.priority ||
    b.report_count - a.report_count ||
    (b.last_reported_at ?? '').localeCompare(a.last_reported_at ?? '')
  )
}

export default function Board() {
  const [domain, setDomain] = useState('')
  const { data, error, refresh } = usePolling(
    () => Promise.all([api.complaints({ domain: domain || undefined }), api.stats(domain || undefined)]),
    domain,
  )

  useEffect(() => {
    if (error && data) toast.error(error, { id: 'board' })
  }, [error, data])

  const complaints = data?.[0]
  const stats = data?.[1]
  const active = useMemo(() => (complaints ?? []).filter((c) => c.status !== 'resolved').sort(byPriority), [complaints])
  const resolved = useMemo(() => (complaints ?? []).filter((c) => c.status === 'resolved').sort(byPriority), [complaints])

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <PageHeader title="What's broken, ranked." description="Every report from every student, merged into one list and sorted by how many people it is hurting.">
        <p className="glass inline-flex h-9 items-center gap-2 rounded-full px-4 text-xs font-semibold tracking-wide text-ink">
          <span className="live-dot text-green-600" aria-hidden="true" />
          Live, refreshes every 8 seconds
        </p>
      </PageHeader>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-6 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Filter by domain">
        {['', ...DOMAINS].map((name) => {
          const on = domain === name
          return (
            <button
              key={name || 'all'}
              type="button"
              aria-pressed={on}
              onClick={() => setDomain(name)}
              className={cx(
                'press relative h-11 shrink-0 rounded-full px-5 text-sm font-medium transition-colors duration-200 sm:h-10',
                on ? 'text-white' : 'bg-white text-zinc-700 ring-1 ring-zinc-900/10 hover:text-ink',
              )}
            >
              {on && <motion.span layoutId="domain-pill" className="absolute inset-0 rounded-full bg-ink" transition={SPRING} />}
              <span className="relative">{name || 'All'}</span>
            </button>
          )
        })}
      </div>

      {!data && error ? (
        <div className="tile p-6">
          <EmptyState title="The board could not load" hint={error} />
          <div className="flex justify-center">
            <Button onClick={refresh}>Try again</Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <Kpis stats={stats} />
          <div className="grid gap-3 lg:grid-cols-[3fr_2fr]">
            <TopPriority items={complaints ? active.slice(0, 8) : undefined} />
            <div className="flex flex-col gap-3">
              <div className="tile p-6">
                <ByDomain rows={domain ? stats?.by_domain.filter((row) => row.domain === domain) : stats?.by_domain} />
              </div>
              <div className="tile flex-1 p-6">
                <Daily days={stats?.daily} />
              </div>
            </div>
          </div>
          <Ranked active={complaints ? active : undefined} resolved={resolved} />
        </div>
      )}
    </div>
  )
}

function Kpis({ stats }: { stats?: Stats }) {
  const items: { label: string; value?: number; icon: LucideIcon; tone: string; sub: string }[] = [
    { label: 'Open', value: stats?.kpis.open, icon: Inbox, tone: 'bg-ink text-white', sub: 'text-zinc-400' },
    { label: 'Reported this week', value: stats?.kpis.reported_7d, icon: TrendingUp, tone: 'bg-white text-ink', sub: 'text-zinc-500' },
    { label: 'Resolved this week', value: stats?.kpis.resolved_7d, icon: CircleCheck, tone: 'bg-white text-ink', sub: 'text-zinc-500' },
    { label: 'Escalated', value: stats?.kpis.escalated, icon: Flame, tone: 'bg-indigo-600 text-white', sub: 'text-indigo-200' },
  ]
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className={cx('tile flex min-h-36 flex-col justify-between p-5 sm:min-h-44 sm:p-6', item.tone)}>
          <dt className={cx('flex items-center justify-between gap-2 text-sm font-medium', item.sub)}>
            {item.label}
            <item.icon className="size-5 shrink-0" aria-hidden="true" />
          </dt>
          <dd className="font-display text-6xl leading-none font-extrabold tracking-tight sm:text-7xl">
            {item.value === undefined ? <span className="opacity-30">--</span> : <Ticker value={item.value} />}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function TopPriority({ items }: { items?: Complaint[] }) {
  const max = Math.max(1, ...(items ?? []).map((c) => c.priority))
  return (
    <section className="tile p-6" aria-labelledby="top-priority">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pb-6">
        <div>
          <h2 id="top-priority" className="font-display text-xl font-semibold tracking-tight text-ink">
            Top priority
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">Reports multiplied by severity weight. Open and in-progress only.</p>
        </div>
        <ul className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Severity colours">
          {SEVERITIES.map((severity) => (
            <li key={severity}>
              <SeverityTag severity={severity} />
            </li>
          ))}
        </ul>
      </div>

      {!items ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-10" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nothing open here" hint="No open issues in this domain right now." />
      ) : (
        <ol className="flex flex-col gap-4">
          {items.map((c, index) => (
            <motion.li key={c.id} layout="position" transition={SPRING}>
              <div className="flex items-baseline justify-between gap-4">
                <p className="min-w-0 truncate text-sm font-medium text-ink">
                  <span className="mr-2 text-zinc-400 tabular-nums">{String(index + 1).padStart(2, '0')}</span>
                  {c.summary}
                  <span className="font-normal text-zinc-500">
                    {' '}
                    · {c.domain} · {plural(c.report_count, 'report')}
                  </span>
                </p>
                <span className="font-display text-lg leading-none font-bold text-ink tabular-nums">{c.priority}</span>
              </div>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-zinc-900/[0.06]">
                <div
                  className="bar h-full rounded-full"
                  style={
                    {
                      background: SEVERITY_FILL[c.severity],
                      '--offset': `${-(1 - c.priority / max) * 100}%`,
                      '--i': index,
                    } as CSSProperties
                  }
                />
              </div>
            </motion.li>
          ))}
        </ol>
      )}
    </section>
  )
}

function Ranked({ active, resolved }: { active?: Complaint[]; resolved: Complaint[] }) {
  return (
    <section className="tile p-6" aria-labelledby="all-issues">
      <div className="flex items-baseline justify-between pb-2">
        <h2 id="all-issues" className="font-display text-xl font-semibold tracking-tight text-ink">
          All issues
        </h2>
        {active && (
          <p className="text-xs text-zinc-500 tabular-nums">
            {active.length} active · {resolved.length} resolved
          </p>
        )}
      </div>

      {!active ? (
        <div className="flex flex-col gap-3 pt-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : active.length + resolved.length === 0 ? (
        <EmptyState title="No complaints yet" hint="Reports from students show up here as soon as they are filed." />
      ) : (
        <ol className="divide-y divide-zinc-900/[0.07]">
          {active.map((c, index) => (
            <Row key={c.id} complaint={c} rank={index + 1} />
          ))}
          {resolved.map((c) => (
            <Row key={c.id} complaint={c} />
          ))}
        </ol>
      )}
    </section>
  )
}

function Row({ complaint: c, rank }: { complaint: Complaint; rank?: number }) {
  const podium = rank !== undefined && rank <= 3
  return (
    <motion.li layout="position" transition={SPRING} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex min-w-0 flex-1 items-start gap-4">
        <span
          className={cx(
            'w-9 shrink-0 font-display leading-none font-bold tabular-nums',
            podium ? 'text-3xl text-indigo-600' : 'pt-1 text-base text-zinc-400',
          )}
        >
          {rank ?? ''}
        </span>
        <div className="min-w-0">
          <p className={cx('font-medium', podium ? 'text-base' : 'text-sm', rank ? 'text-ink' : 'text-zinc-500')}>
            {c.summary}
            {c.escalated && c.status !== 'resolved' && (
              <span className="ml-2 inline-flex h-5 items-center gap-1 rounded-full bg-ink px-2 align-middle text-[11px] font-semibold text-white">
                <Flame className="size-3" aria-hidden="true" />
                Escalated
              </span>
            )}
          </p>
          <p className="mt-0.5 text-sm text-zinc-500">
            {[c.domain, c.category, place(c)].filter(Boolean).join(' · ')}
            <span className="text-zinc-400"> · last reported {timeAgo(c.last_reported_at)}</span>
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3 pl-[3.25rem] sm:pl-0">
        <span className="w-16">
          <SeverityTag severity={c.severity} />
        </span>
        <CountBadge count={c.report_count} />
        <span className="flex w-[5.5rem] justify-end">
          <StatusPill status={c.status} />
        </span>
      </div>
    </motion.li>
  )
}
