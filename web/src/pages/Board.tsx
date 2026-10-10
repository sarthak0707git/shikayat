import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { toast } from 'sonner'
import { ByDomain, Daily } from '../components/BoardCharts'
import { Button, CountBadge, cx, EmptyState, PageHeader, SEVERITY_FILL, SeverityTag, Skeleton, StatusPill } from '../components/ui'
import { api } from '../lib/api'
import { place, plural, timeAgo } from '../lib/format'
import { usePolling } from '../lib/usePolling'
import { DOMAINS, type Complaint, type Severity, type Stats } from '../types'

const SEVERITIES: Severity[] = ['urgent', 'high', 'medium', 'low']

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
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <PageHeader title="Campus board" description="What students are reporting, ranked by how many are affected." />

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-6 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Filter by domain">
        {['', ...DOMAINS].map((name) => (
          <button
            key={name || 'all'}
            type="button"
            aria-pressed={domain === name}
            onClick={() => setDomain(name)}
            className={cx(
              'press h-11 shrink-0 rounded-full border px-4 text-sm font-medium transition-colors duration-150 sm:h-9 sm:px-3',
              domain === name
                ? 'border-zinc-900 bg-zinc-900 text-white'
                : 'border-zinc-200 text-zinc-700 hover:bg-zinc-50',
            )}
          >
            {name || 'All'}
          </button>
        ))}
      </div>

      {!data && error ? (
        <div className="border-t border-zinc-200">
          <EmptyState title="The board could not load" hint={error} />
          <div className="flex justify-center">
            <Button onClick={refresh}>Try again</Button>
          </div>
        </div>
      ) : (
        <>
          <Kpis stats={stats} />
          <div className="grid gap-x-12 lg:grid-cols-[3fr_2fr]">
            <TopPriority items={complaints ? active.slice(0, 8) : undefined} />
            <div className="border-t border-zinc-200 lg:border-t-0">
              <ByDomain rows={domain ? stats?.by_domain.filter((row) => row.domain === domain) : stats?.by_domain} />
              <Daily days={stats?.daily} />
            </div>
          </div>
          <Ranked active={complaints ? active : undefined} resolved={resolved} />
        </>
      )}
    </div>
  )
}

function Kpis({ stats }: { stats?: Stats }) {
  const items = [
    { label: 'Open', value: stats?.kpis.open },
    { label: 'Reported this week', value: stats?.kpis.reported_7d },
    { label: 'Resolved this week', value: stats?.kpis.resolved_7d },
    { label: 'Escalated', value: stats?.kpis.escalated },
  ]
  return (
    <dl className="grid grid-cols-2 border-y border-zinc-200 lg:grid-cols-4">
      {items.map((item, index) => (
        <div
          key={item.label}
          className={cx(
            'py-4',
            index % 2 === 1 && 'border-l border-zinc-200 pl-4',
            index >= 2 && 'border-t border-zinc-200 lg:border-t-0',
            index === 2 && 'lg:border-l lg:pl-4',
          )}
        >
          <dt className="text-xs font-medium text-zinc-500">{item.label}</dt>
          <dd className="mt-1 text-2xl font-semibold tracking-tight text-zinc-900 tabular-nums">
            {item.value ?? <Skeleton className="mt-2 h-6 w-12" />}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function TopPriority({ items }: { items?: Complaint[] }) {
  const max = Math.max(1, ...(items ?? []).map((c) => c.priority))
  return (
    <section className="py-8" aria-labelledby="top-priority">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pb-4">
        <div>
          <h2 id="top-priority" className="text-sm font-semibold text-zinc-900">
            Top priority
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">Reports multiplied by severity weight. Open and in-progress issues only.</p>
        </div>
        <ul className="flex gap-4" aria-label="Severity colours">
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
            <Skeleton key={i} className="h-9" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nothing open here" hint="No open issues in this domain right now." />
      ) : (
        <ol className="flex flex-col gap-3.5">
          {items.map((c, index) => (
            <li key={c.id}>
              <div className="flex items-baseline justify-between gap-4">
                <p className="min-w-0 truncate text-sm text-zinc-900">
                  {c.summary}
                  <span className="text-zinc-500">
                    {' '}
                    · {c.domain} · {plural(c.report_count, 'report')}
                  </span>
                </p>
                <span className="text-sm font-semibold text-zinc-900 tabular-nums">{c.priority}</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-zinc-100">
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
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function Ranked({ active, resolved }: { active?: Complaint[]; resolved: Complaint[] }) {
  return (
    <section aria-labelledby="all-issues">
      <div className="flex items-baseline justify-between border-b border-zinc-200 pb-3">
        <h2 id="all-issues" className="text-sm font-semibold text-zinc-900">
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
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : active.length + resolved.length === 0 ? (
        <EmptyState title="No complaints yet" hint="Reports from students show up here as soon as they are filed." />
      ) : (
        <ol className="divide-y divide-zinc-200">
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
  return (
    <li className="flex flex-col gap-2 py-3.5 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span className="w-6 shrink-0 pt-px text-sm text-zinc-400 tabular-nums">{rank ?? ''}</span>
        <div className="min-w-0">
          <p className={cx('text-sm font-medium', rank ? 'text-zinc-900' : 'text-zinc-500')}>
            {c.summary}
            {c.escalated && c.status !== 'resolved' && (
              <span className="ml-2 text-xs font-semibold text-zinc-900">Escalated</span>
            )}
          </p>
          <p className="mt-0.5 text-sm text-zinc-500">
            {[c.domain, c.category, place(c)].filter(Boolean).join(' · ')}
            <span className="text-zinc-400"> · last reported {timeAgo(c.last_reported_at)}</span>
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3 pl-9 sm:pl-0">
        <span className="w-16">
          <SeverityTag severity={c.severity} />
        </span>
        <CountBadge count={c.report_count} />
        <span className="flex w-[5.5rem] justify-end">
          <StatusPill status={c.status} />
        </span>
      </div>
    </li>
  )
}
