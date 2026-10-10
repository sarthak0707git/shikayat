import { CircleCheck, Flame, Inbox, TrendingUp, type LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { ByDomain, Daily } from '../components/BoardCharts'
import { ProblemMap } from '../components/ProblemMap'
import { Sheet } from '../components/Sheet'
import { Button, CountBadge, cx, EmptyState, PageHeader, SEVERITY_FILL, SeverityTag, Skeleton, StatusPill, Ticker } from '../components/ui'
import { api } from '../lib/api'
import { formatDate, formatTime, place, plural, timeAgo } from '../lib/format'
import { usePolling } from '../lib/usePolling'
import { DOMAINS, type Complaint, type Severity } from '../types'

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
  // A link like /board?domain=Mess opens the board already filtered.
  const [domain, setDomain] = useState(() => {
    const asked = new URLSearchParams(window.location.search).get('domain') ?? ''
    return (DOMAINS as readonly string[]).includes(asked) ? asked : ''
  })
  // Every complaint, loaded once and refreshed. The chips filter in the browser, so a switch is instant.
  const all = usePolling(() => api.complaints(), 'all')
  // Week totals and the daily chart need the stats endpoint. If the filtered call fails, use campus-wide and label it.
  const statsPoll = usePolling(
    () =>
      api.stats(domain || undefined).then(
        (stats) => ({ stats, domain, scoped: true }),
        (cause) => (domain ? api.stats().then((stats) => ({ stats, domain, scoped: false })) : Promise.reject(cause)),
      ),
    domain,
  )
  const [params, setParams] = useSearchParams()
  const focusId = Number(params.get('focus')) || null
  const [flash, setFlash] = useState<Set<number>>(new Set())
  const [picked, setPicked] = useState<Complaint | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const seen = useRef(new Map<number, number>())
  const flashTimer = useRef(0)

  function light(ids: number[]) {
    setFlash(new Set(ids))
    window.clearTimeout(flashTimer.current)
    flashTimer.current = window.setTimeout(() => setFlash(new Set()), 2800)
  }

  const everything = all.data ?? undefined
  const stats = statsPoll.data?.stats
  // True while the week numbers on screen are not for the selected domain.
  const campusOnly = Boolean(domain) && !(statsPoll.data?.domain === domain && statsPoll.data.scoped)

  useEffect(() => {
    if (all.error && everything) toast.error(all.error, { id: 'board' })
  }, [all.error, everything])

  // A row lights up when its count rises or a brand-new complaint appears.
  useEffect(() => {
    if (!everything) return
    const firstLoad = seen.current.size === 0
    const changed = everything
      .filter((c) => {
        const before = seen.current.get(c.id)
        return before === undefined ? !firstLoad : c.report_count > before
      })
      .map((c) => c.id)
    for (const c of everything) seen.current.set(c.id, c.report_count)
    if (changed.length) light(changed)
  }, [everything])

  // Arriving from a report: scroll to that complaint and light it up, once.
  const loaded = Boolean(everything)
  useEffect(() => {
    if (!focusId || !loaded) return
    const row = document.getElementById(`c-${focusId}`)
    if (row) {
      const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      row.scrollIntoView({ block: 'center', behavior: calm ? 'auto' : 'smooth' })
      light([focusId])
    }
    setParams({}, { replace: true })
  }, [focusId, loaded])

  const complaints = useMemo(() => everything?.filter((c) => !domain || c.domain === domain), [everything, domain])
  const active = useMemo(() => (complaints ?? []).filter((c) => c.status !== 'resolved').sort(byPriority), [complaints])
  const resolved = useMemo(() => (complaints ?? []).filter((c) => c.status === 'resolved').sort(byPriority), [complaints])
  const pick = (name: string) => setDomain((current) => (current === name ? '' : name))

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <PageHeader title="What's broken, ranked." description="Every report from every student, merged into one list and sorted by how many people it is hurting.">
        <p className="inline-flex h-9 items-center gap-2 rounded-full bg-white px-4 text-xs font-semibold tracking-wide text-ink ring-1 ring-zinc-900/10">
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
                'press relative h-11 shrink-0 rounded-full px-5 text-sm font-medium transition-colors duration-150 sm:h-10',
                on ? 'text-white' : 'bg-white text-zinc-700 ring-1 ring-zinc-900/10 hover:bg-zinc-50 hover:text-ink',
              )}
            >
              {on && <motion.span layoutId="domain-pill" className="absolute inset-0 rounded-full bg-ink" transition={SPRING} />}
              <span className="relative">{name || 'All'}</span>
            </button>
          )
        })}
      </div>

      {!everything && all.error ? (
        <div className="tile p-6">
          <EmptyState title="The board could not load" hint={all.error} />
          <div className="flex justify-center">
            <Button onClick={all.refresh}>Try again</Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <Kpis
            open={complaints?.filter((c) => c.status === 'open').length}
            escalated={complaints?.filter((c) => c.escalated && c.status !== 'resolved').length}
            reported={stats?.kpis.reported_7d}
            resolved={stats?.kpis.resolved_7d}
            campusOnly={campusOnly}
          />
          <ProblemMap complaints={everything} selected={domain} onPick={pick} />
          <div className="grid gap-3 lg:grid-cols-[3fr_2fr]">
            <TopPriority key={domain} items={complaints ? active.slice(0, 8) : undefined} />
            <div className="flex flex-col gap-3">
              <div className="tile p-6">
                <ByDomain rows={stats?.by_domain} selected={domain} onPick={pick} />
              </div>
              <div className="tile flex-1 p-6">
                <Daily days={stats?.daily} note={campusOnly ? 'Last 14 days, whole campus' : 'Last 14 days'} />
              </div>
            </div>
          </div>
          <Ranked
            key={domain}
            active={complaints ? active : undefined}
            resolved={resolved}
            flash={flash}
            onOpen={(c) => {
              setPicked(c)
              setSheetOpen(true)
            }}
          />
        </div>
      )}

      <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)} label={picked ? `Complaint #${picked.id}` : 'Complaint'}>
        {picked && <PublicDetail complaint={everything?.find((c) => c.id === picked.id) ?? picked} />}
      </Sheet>
    </div>
  )
}

type KpiProps = { open?: number; escalated?: number; reported?: number; resolved?: number; campusOnly: boolean }

function Kpis({ open, escalated, reported, resolved, campusOnly }: KpiProps) {
  const items: { label: string; value?: number; icon: LucideIcon; tone: string; sub: string; campus?: boolean }[] = [
    { label: 'Open', value: open, icon: Inbox, tone: 'bg-ink text-white', sub: 'text-zinc-400' },
    { label: 'Reported this week', value: reported, icon: TrendingUp, tone: 'bg-white text-ink', sub: 'text-zinc-500', campus: campusOnly },
    { label: 'Resolved this week', value: resolved, icon: CircleCheck, tone: 'bg-white text-ink', sub: 'text-zinc-500', campus: campusOnly },
    { label: 'Escalated', value: escalated, icon: Flame, tone: 'bg-indigo-600 text-white', sub: 'text-indigo-200' },
  ]
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className={cx('tile flex min-h-36 flex-col justify-between p-5 sm:min-h-44 sm:p-6', item.tone)}>
          <dt className={cx('flex items-center justify-between gap-2 text-sm font-medium', item.sub)}>
            <span>
              {item.label}
              {item.campus && <span className="mt-1 block w-fit rounded-full bg-zinc-900/[0.06] px-2 py-0.5 text-[11px] whitespace-nowrap text-zinc-600">whole campus</span>}
            </span>
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
        <ol className="rise flex flex-col gap-4">
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

type RankedProps = { active?: Complaint[]; resolved: Complaint[]; flash: Set<number>; onOpen: (c: Complaint) => void }

function Ranked({ active, resolved, flash, onOpen }: RankedProps) {
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
        <ol className="rise divide-y divide-zinc-900/[0.07]">
          {active.map((c, index) => (
            <Row key={c.id} complaint={c} rank={index + 1} lit={flash.has(c.id)} onOpen={onOpen} />
          ))}
          {resolved.map((c) => (
            <Row key={c.id} complaint={c} lit={flash.has(c.id)} onOpen={onOpen} />
          ))}
        </ol>
      )}
    </section>
  )
}

type RowProps = { complaint: Complaint; rank?: number; lit: boolean; onOpen: (c: Complaint) => void }

function Row({ complaint: c, rank, lit, onOpen }: RowProps) {
  const podium = rank !== undefined && rank <= 3
  return (
    <motion.li id={`c-${c.id}`} layout="position" transition={SPRING} className={cx('relative', lit && 'flash')}>
      <button
        type="button"
        onClick={() => onOpen(c)}
        className="relative -mx-3 flex w-[calc(100%+1.5rem)] flex-col gap-2 rounded-2xl px-3 py-4 text-left transition-colors duration-150 hover:bg-zinc-900/[0.035] sm:flex-row sm:items-center sm:gap-4"
      >
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
      </button>
    </motion.li>
  )
}

/** What anyone may see about a complaint. The students' own words and photos stay with the authority. */
function PublicDetail({ complaint: c }: { complaint: Complaint }) {
  const facts = [
    { label: 'Reports', value: String(c.report_count) },
    { label: 'Priority', value: String(c.priority) },
    { label: 'First reported', value: `${formatDate(c.first_reported_at)}, ${formatTime(c.first_reported_at)}` },
    { label: 'Last reported', value: `${formatDate(c.last_reported_at)}, ${formatTime(c.last_reported_at)}` },
    { label: 'Handled by', value: c.authority },
    { label: 'Where', value: place(c) || 'Not specified' },
  ]
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="font-display text-3xl leading-[1.05] font-bold tracking-tight text-ink">{c.summary}</h2>
        <p className="mt-2 text-sm text-zinc-500">{[c.domain, c.category].join(' · ')}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
          <StatusPill status={c.status} />
          <SeverityTag severity={c.severity} />
          {c.escalated && c.status !== 'resolved' && (
            <span className="inline-flex h-6 items-center gap-1 rounded-full bg-ink px-2 text-xs font-semibold text-white">
              <Flame className="size-3.5" aria-hidden="true" />
              Escalated
            </span>
          )}
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 border-y border-zinc-900/10 py-5 text-sm">
        {facts.map((fact) => (
          <div key={fact.label}>
            <dt className="text-xs font-medium text-zinc-500">{fact.label}</dt>
            <dd className="mt-0.5 text-ink tabular-nums">{fact.value}</dd>
          </div>
        ))}
      </dl>
      {c.resolution_note && (
        <div>
          <p className="text-xs font-medium text-zinc-500">Note from {c.authority}</p>
          <p className="mt-1 text-base text-ink">{c.resolution_note}</p>
        </div>
      )}
      <p className="text-xs text-zinc-500">What students wrote and any photos are visible only to {c.authority}.</p>
    </div>
  )
}
