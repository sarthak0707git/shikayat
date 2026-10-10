import { Flag } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Sheet } from '../components/Sheet'
import { Button, CountBadge, cx, EmptyState, PageHeader, SeverityTag, Skeleton, StatusPill } from '../components/ui'
import { api } from '../lib/api'
import { formatDate, formatTime, place, plural, timeAgo } from '../lib/format'
import { usePolling } from '../lib/usePolling'
import { AUTHORITIES, type Complaint, type ComplaintDetail, type Status } from '../types'

const COLUMNS = 'sm:grid sm:grid-cols-[minmax(0,1fr)_5.5rem_4.5rem_4.5rem_6.5rem] sm:items-center sm:gap-4'

const DONE: Record<Status, string> = {
  in_progress: 'Marked in progress',
  resolved: 'Marked resolved',
  open: 'Moved back to open',
}

export default function Authority() {
  const [authority, setAuthority] = useState<string>(AUTHORITIES[0])
  const [selected, setSelected] = useState<Complaint | null>(null)
  const [open, setOpen] = useState(false)

  const queue = usePolling(() => api.complaints({ authority }), authority)
  const suggestions = usePolling(() => api.stats().then((stats) => stats.other_suggestions), 'suggestions', 30000)

  useEffect(() => {
    if (queue.error && queue.data) toast.error(queue.error, { id: 'queue' })
  }, [queue.error, queue.data])

  const all = queue.data
  const active = all?.filter((c) => c.status !== 'resolved') ?? []
  const resolved = all?.filter((c) => c.status === 'resolved') ?? []

  function show(complaint: Complaint) {
    setSelected(complaint)
    setOpen(true)
  }

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <PageHeader title="Your queue, nobody else's." description="Each office sees only its own complaints, escalated ones first. A demo role picker stands in for institute SSO.">
        <div className="flex flex-col gap-2">
          <label htmlFor="viewing-as" className="text-xs font-medium text-zinc-500">
            Viewing as
          </label>
          <select
            id="viewing-as"
            value={authority}
            onChange={(event) => {
              setAuthority(event.target.value)
              setOpen(false)
            }}
            className="h-11 min-w-52 rounded-full bg-white px-4 text-base font-medium text-ink ring-1 ring-zinc-900/10"
          >
            {AUTHORITIES.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </div>
      </PageHeader>

      {authority === 'Admin' && suggestions.data && suggestions.data.length > 0 && (
        <section className="tile mb-3 p-6" aria-labelledby="suggested">
          <h2 id="suggested" className="font-display text-xl font-semibold tracking-tight text-ink">
            Suggested new categories
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">Gemma filed these under Other and proposed a name. Promote the ones that keep coming up.</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {suggestions.data.map((item) => (
              <li key={item.name} className="inline-flex h-9 items-center gap-2 rounded-full border border-zinc-200 pr-1.5 pl-3 text-sm text-zinc-900">
                {item.name}
                <CountBadge count={item.count} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="tile px-4 py-4 sm:px-6">
      <div className={cx('hidden border-b border-zinc-900/10 pb-3 text-xs font-medium text-zinc-500', COLUMNS)}>
        <span>Complaint</span>
        <span>Severity</span>
        <span className="text-right">Reports</span>
        <span className="text-right">Priority</span>
        <span className="text-right">Status</span>
      </div>

      {!all && queue.error ? (
        <div>
          <EmptyState title="The queue could not load" hint={queue.error} />
          <div className="flex justify-center">
            <Button onClick={queue.refresh}>Try again</Button>
          </div>
        </div>
      ) : !all ? (
        <div className="flex flex-col gap-3 pt-4">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : all.length === 0 ? (
        <EmptyState title={`Nothing in the ${authority} queue`} hint="New complaints for this office will appear here." />
      ) : (
        <ul className="divide-y divide-zinc-900/[0.07]">
          {[...active, ...resolved].map((c) => (
            <li key={c.id}>
              <QueueRow complaint={c} onOpen={() => show(c)} />
            </li>
          ))}
        </ul>
      )}

      </div>

      <Sheet open={open} onClose={() => setOpen(false)} label={selected ? `Complaint #${selected.id} · ${selected.authority}` : 'Complaint'}>
        {selected && (
          <Detail
            key={selected.id}
            summary={selected}
            onChanged={(next) => {
              setSelected(next)
              queue.refresh()
            }}
          />
        )}
      </Sheet>
    </div>
  )
}

function QueueRow({ complaint: c, onOpen }: { complaint: Complaint; onOpen: () => void }) {
  const dim = c.status === 'resolved'
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cx(
        'flex w-full flex-col gap-2 py-3.5 text-left transition-colors duration-150 hover:bg-zinc-50 sm:-mx-2 sm:w-[calc(100%+1rem)] sm:rounded-[10px] sm:px-2',
        COLUMNS,
      )}
    >
      <span className="min-w-0">
        <span className={cx('block text-sm font-medium', dim ? 'text-zinc-500' : 'text-zinc-900')}>{c.summary}</span>
        <span className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm text-zinc-500">
          {c.escalated && !dim && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-zinc-900">
              <Flag className="size-3.5" aria-hidden="true" />
              Escalated
            </span>
          )}
          <span>{[c.category, place(c)].filter(Boolean).join(' · ')}</span>
          <span className="text-zinc-400">{timeAgo(c.last_reported_at)}</span>
          {c.needs_details && <span className="text-xs font-medium text-zinc-700">Needs details</span>}
        </span>
      </span>
      <span className="flex items-center gap-3 sm:contents">
        <span>
          <SeverityTag severity={c.severity} />
        </span>
        <span className="sm:text-right">
          <CountBadge count={c.report_count} />
        </span>
        <span className="text-sm font-semibold text-zinc-900 tabular-nums sm:text-right">
          <span className="font-normal text-zinc-500 sm:hidden">Priority </span>
          {c.priority}
        </span>
        <span className="ml-auto flex sm:ml-0 sm:justify-end">
          <StatusPill status={c.status} />
        </span>
      </span>
    </button>
  )
}

function Detail({ summary, onChanged }: { summary: Complaint; onChanged: (next: Complaint) => void }) {
  const [detail, setDetail] = useState<ComplaintDetail | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [note, setNote] = useState(summary.resolution_note ?? '')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let alive = true
    api
      .complaint(summary.id)
      .then((next) => alive && setDetail(next))
      .catch((error) => alive && setFailed(error instanceof Error ? error.message : 'Could not load the reports.'))
    return () => {
      alive = false
    }
  }, [summary.id])

  async function move(status: Status) {
    setSaving(true)
    try {
      const next = await api.setStatus(summary.id, status, note.trim())
      toast.success(`${DONE[status]} · #${summary.id}`)
      onChanged(next)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not update the status.')
    } finally {
      setSaving(false)
    }
  }

  const c = summary
  const reports = detail?.reports
  const quiet = reports && !reports.some((r) => r.photo_url || r.followups.length)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl leading-tight font-bold tracking-tight text-ink">{c.summary}</h2>
        <p className="mt-1 text-sm text-zinc-500">{[c.domain, c.category, place(c)].filter(Boolean).join(' · ')}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <StatusPill status={c.status} />
          <SeverityTag severity={c.severity} />
          <span className="inline-flex items-center gap-2 text-sm text-zinc-700">
            <CountBadge count={c.report_count} />
            {c.report_count === 1 ? 'report' : 'reports'}
          </span>
          {c.escalated && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-zinc-900">
              <Flag className="size-3.5" aria-hidden="true" />
              Escalated
            </span>
          )}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-y border-zinc-200 py-4 text-sm">
        <Fact label="First reported" value={`${formatDate(c.first_reported_at)}, ${formatTime(c.first_reported_at)}`} />
        <Fact label="Last reported" value={`${formatDate(c.last_reported_at)}, ${formatTime(c.last_reported_at)}`} />
        <Fact label="Priority" value={String(c.priority)} />
        <Fact label="Photos" value={c.photo_count ? plural(c.photo_count, 'photo') : 'None'} />
      </dl>

      <div className="flex flex-col gap-2">
        <label htmlFor="note" className="text-sm font-medium text-zinc-900">
          Note for students
        </label>
        <textarea
          id="note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={2}
          placeholder="Plumber booked for tomorrow morning"
          className="block w-full resize-none rounded-2xl border border-zinc-300 p-3 text-base text-zinc-900 outline-none transition-colors duration-150 placeholder:text-zinc-400 focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/15 sm:text-sm"
        />
        <p className="text-xs text-zinc-500">Optional. Saved with the status change.</p>
        <div className="flex flex-wrap gap-2 pt-1">
          {c.status === 'open' && (
            <Button variant="primary" size="lg" disabled={saving} onClick={() => move('in_progress')}>
              Start work
            </Button>
          )}
          {c.status !== 'resolved' && (
            <Button variant={c.status === 'in_progress' ? 'primary' : 'secondary'} size="lg" disabled={saving} onClick={() => move('resolved')}>
              Mark resolved
            </Button>
          )}
          {c.status !== 'open' && (
            <Button variant="ghost" size="lg" disabled={saving} onClick={() => move('open')}>
              {c.status === 'resolved' ? 'Reopen' : 'Move back to open'}
            </Button>
          )}
        </div>
      </div>

      <section aria-labelledby="reports">
        <h3 id="reports" className="border-b border-zinc-200 pb-2 text-sm font-semibold text-zinc-900">
          What students wrote
        </h3>
        {failed ? (
          <EmptyState title="The reports could not load" hint={failed} />
        ) : !reports ? (
          <div className="flex flex-col gap-3 pt-4">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : reports.length === 0 ? (
          <EmptyState title="No reports attached" />
        ) : (
          <>
            {quiet && <p className="pt-3 text-xs text-zinc-500">No photos or follow-up answers on these reports yet.</p>}
            <ol className="divide-y divide-zinc-200">
              {reports.map((report) => (
                <li key={report.id} className="py-4">
                  <p className="text-[15px] leading-relaxed break-words text-zinc-900">{report.raw_text}</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {formatDate(report.created_at)}, {formatTime(report.created_at)}
                    {report.merge_reason && ` · Merged: ${report.merge_reason}`}
                  </p>
                  {report.photo_url && (
                    <a href={report.photo_url} target="_blank" rel="noreferrer" className="mt-3 block w-fit">
                      <img
                        src={report.photo_url}
                        alt="Photo attached to this report"
                        loading="lazy"
                        className="max-h-56 rounded-xl border border-zinc-200 object-cover"
                      />
                    </a>
                  )}
                  {report.followups.length > 0 && (
                    <dl className="mt-3 flex flex-col gap-2 border-l-2 border-zinc-200 pl-3 text-sm">
                      {report.followups.map((item, index) => (
                        <div key={index}>
                          <dt className="text-zinc-500">{item.q}</dt>
                          <dd className="text-zinc-900">{item.a}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </li>
              ))}
            </ol>
          </>
        )}
      </section>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-zinc-500">{label}</dt>
      <dd className="mt-0.5 text-zinc-900 tabular-nums">{value}</dd>
    </div>
  )
}
