import type { CSSProperties } from 'react'
import type { Complaint } from '../types'
import { cx, EmptyState, Skeleton } from './ui'

// One step of the ink-to-indigo ramp per domain, darkest for the busiest.
const RAMP = [
  { fill: '#0d0c14', text: 'text-white', sub: 'text-zinc-400' },
  { fill: '#312e81', text: 'text-white', sub: 'text-indigo-200' },
  { fill: '#4f46e5', text: 'text-white', sub: 'text-indigo-100' },
  { fill: '#818cf8', text: 'text-ink', sub: 'text-indigo-950' },
  { fill: '#c7d2fe', text: 'text-ink', sub: 'text-indigo-900' },
  { fill: '#e7e5e4', text: 'text-ink', sub: 'text-zinc-600' },
]

/**
 * A mosaic of where the reports are. A domain's block grows with its share of all open
 * reports; inside it, each kind of problem grows with its share of that domain.
 */
type ProblemMapProps = { complaints?: Complaint[]; selected?: string; onPick?: (domain: string) => void }

export function ProblemMap({ complaints, selected, onPick }: ProblemMapProps) {
  const domains = new Map<string, Map<string, number>>()
  for (const c of complaints ?? []) {
    if (c.status === 'resolved') continue
    const categories = domains.get(c.domain) ?? new Map<string, number>()
    categories.set(c.category, (categories.get(c.category) ?? 0) + c.report_count)
    domains.set(c.domain, categories)
  }
  const blocks = [...domains]
    .map(([domain, categories]) => {
      const cells = [...categories].map(([category, reports]) => ({ category, reports })).sort((a, b) => b.reports - a.reports)
      return { domain, cells, total: cells.reduce((sum, cell) => sum + cell.reports, 0) }
    })
    .sort((a, b) => b.total - a.total)
  const grand = blocks.reduce((sum, block) => sum + block.total, 0)
  let order = 0

  return (
    <section className="tile p-6" aria-labelledby="problem-map">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pb-5">
        <div>
          <h2 id="problem-map" className="font-display text-xl font-semibold tracking-tight text-ink">
            Where it hurts
          </h2>
          <p className="mt-0.5 text-xs text-zinc-500">
            Every open report, by domain and kind of problem. Bigger block, more students affected. Click a domain to {selected ? 'clear the filter' : 'filter the board'}.
          </p>
        </div>
        {complaints && grand > 0 && (
          <p className="font-display text-3xl leading-none font-extrabold tracking-tight text-ink tabular-nums">
            {grand} <span className="font-sans text-xs font-medium text-zinc-500">open reports</span>
          </p>
        )}
      </div>

      {!complaints ? (
        <Skeleton className="h-80" />
      ) : grand === 0 ? (
        <EmptyState title="Nothing open here" hint="No open reports in this domain right now." />
      ) : (
        <div className="flex h-[34rem] flex-col gap-1.5 sm:h-[22rem] sm:flex-row">
          {blocks.map((block, index) => {
            const tone = RAMP[Math.min(index, RAMP.length - 1)]
            return (
              <div
                key={block.domain}
                role="button"
                tabIndex={0}
                aria-label={`${block.domain}: ${block.total} open reports. ${selected === block.domain ? 'Clear the filter' : 'Filter the board to this domain'}`}
                onClick={() => onPick?.(block.domain)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onPick?.(block.domain)
                  }
                }}
                className="press flex min-h-0 min-w-0 basis-0 cursor-pointer flex-col gap-1.5 rounded-xl"
                style={{ flexGrow: block.total }}
              >
                <p className="flex items-baseline justify-between gap-2 text-xs font-semibold text-ink">
                  <span className="truncate">{block.domain}</span>
                  <span className="text-zinc-500 tabular-nums">{Math.round((block.total / grand) * 100)}%</span>
                </p>
                <div className="flex min-h-0 flex-1 gap-1.5 sm:flex-col">
                  {block.cells.map((cell) => {
                    const share = cell.reports / block.total
                    // Rough cell height on desktop, where cells stack: tall ones get two lines, short ones one.
                    const tall = share * 320 >= 64
                    const labelled = share * 320 >= 30
                    return (
                      <div
                        key={cell.category}
                        title={`${block.domain} · ${cell.category}: ${cell.reports} reports`}
                        className={cx(
                          'cell flex min-h-7 min-w-7 basis-0 flex-col justify-between gap-1 overflow-hidden rounded-xl p-2.5',
                          !tall && 'sm:flex-row sm:items-center sm:py-0',
                          tone.text,
                        )}
                        style={{ flexGrow: cell.reports, background: tone.fill, '--i': order++ } as CSSProperties}
                      >
                        <span className={cx('min-w-0 truncate text-xs font-medium', tone.sub, share >= 0.2 ? 'block' : 'hidden', labelled ? 'sm:block' : 'sm:hidden')}>
                          {cell.category}
                        </span>
                        <span
                          className={cx(
                            'font-display leading-none font-extrabold tracking-tight tabular-nums',
                            tall ? 'text-2xl' : 'text-2xl sm:text-lg',
                            share >= 0.1 ? 'block' : 'hidden',
                            labelled ? 'sm:block' : 'sm:hidden',
                          )}
                        >
                          {cell.reports}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
