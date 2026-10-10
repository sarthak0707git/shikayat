import { ArrowRight, ArrowUp, Ban, Check, CircleCheck, Flame, ImagePlus, TriangleAlert } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ThinkingOrb } from 'thinking-orbs'
import { GrainGradient } from '../components/GrainGradient'
import { Button, SeverityTag, StatusPill, Ticker } from '../components/ui'
import { api } from '../lib/api'
import { place } from '../lib/format'
import { usePolling } from '../lib/usePolling'
import type { ReportResult } from '../types'

const EXAMPLES = ['dal mein keeda tha aaj lunch mein', 'AC se paani tapak raha hai', 'the moon is too bright']

type Turn =
  | { kind: 'student'; text: string; photo?: string }
  | { kind: 'steps'; labels: string[] }
  | { kind: 'question'; text: string }
  | { kind: 'result'; result: ReportResult }

type Busy = null | 'waiting' | 'revealing'

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Brief 6.2: shrink to at most 1280 px JPEG in the browser before upload. */
async function shrinkPhoto(file: File, max = 1280): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
    return blob ?? file
  } catch {
    return file
  }
}

export default function Report() {
  const [text, setText] = useState('')
  const [photo, setPhoto] = useState<{ blob: Blob; url: string } | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState<Busy>(null)
  const [threadId, setThreadId] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')

  // Wide: the dark field sits behind the composer on the right. Narrow: it drops below the text.
  const [wide, setWide] = useState(() => window.matchMedia('(min-width: 1024px)').matches)
  useEffect(() => {
    const query = window.matchMedia('(min-width: 1024px)')
    const onChange = () => setWide(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const textRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const last = turns[turns.length - 1]
  const started = turns.length > 0
  const asking = !busy && last?.kind === 'question'
  const finished = !busy && last?.kind === 'result'

  useEffect(() => {
    if (started) endRef.current?.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' })
  }, [turns, busy, started])

  /** The steps arrive with the response, so we replay them one by one before the outcome. */
  async function play(result: ReportResult) {
    const labels = result.steps
      .map((step) => step.label)
      .filter((label): label is string => Boolean(label))
      .slice(0, 6)
    setBusy('revealing')
    if (labels.length) {
      setTurns((prev) => [...prev, { kind: 'steps', labels: [] }])
      for (const label of labels) {
        setTurns((prev) => {
          const tail = prev[prev.length - 1]
          if (tail?.kind !== 'steps') return prev
          return [...prev.slice(0, -1), { kind: 'steps', labels: [...tail.labels, label] }]
        })
        await sleep(reducedMotion() ? 0 : 480)
      }
    }
    setThreadId(result.thread_id)
    setTurns((prev) => [
      ...prev,
      result.status === 'needs_input' && result.question
        ? { kind: 'question', text: result.question }
        : { kind: 'result', result },
    ])
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const message = text.trim()
    if (!message || busy) return
    setTurns([{ kind: 'student', text: message, photo: photo?.url }])
    setBusy('waiting')
    try {
      const result = await api.sendReport(message, photo?.blob)
      await play(result)
      if (result.status !== 'error') setText('') // keep the text so "Try again" has it
    } catch (error) {
      setTurns([]) // back to the composer, with the text still there
      toast.error(error instanceof Error ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(null)
    }
  }

  async function reply(event: FormEvent) {
    event.preventDefault()
    const message = answer.trim()
    if (!message || busy || !threadId) return
    setTurns((prev) => [...prev, { kind: 'student', text: message }])
    setAnswer('')
    setBusy('waiting')
    try {
      await play(await api.sendAnswer(threadId, message))
    } catch (error) {
      setTurns((prev) => prev.slice(0, -1))
      setAnswer(message)
      toast.error(error instanceof Error ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(null)
    }
  }

  async function attach(file: File | undefined) {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      toast.error('Please choose an image file.')
      return
    }
    const blob = await shrinkPhoto(file)
    setPhoto((old) => {
      if (old) URL.revokeObjectURL(old.url)
      return { blob, url: URL.createObjectURL(blob) }
    })
  }

  function removePhoto() {
    if (photo) URL.revokeObjectURL(photo.url)
    setPhoto(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  function reset(keepDraft = false) {
    if (!keepDraft) {
      removePhoto()
      setText('')
    }
    setTurns([])
    setThreadId(null)
    setAnswer('')
    requestAnimationFrame(() => textRef.current?.focus())
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void submit()
  }

  return (
    <div className="px-3 pt-3 pb-3">
      <section className="relative isolate overflow-hidden rounded-[2rem] lg:min-h-[calc(100dvh-6.5rem)]">
        <GrainGradient
          className="!absolute inset-0 -z-10"
          colorLight="#f4f2ec"
          colorMid="#a5b4fc"
          colorDark="#1e1b4b"
          angle={wide ? 0 : 90}
          position={wide ? 0.26 : 0.44}
          curve={wide ? 0.62 : 0.3}
          softness={0.2}
          grain={0.26}
          speed={0.8}
        />

        <div className="mx-auto grid max-w-6xl gap-10 px-5 py-10 sm:px-8 sm:py-14 lg:min-h-[calc(100dvh-6.5rem)] lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-14">
          <Pitch busy={busy} asking={asking} finished={finished} />

          <div className="min-w-0">
            {!started ? (
              <form onSubmit={submit}>
                <div className="glass rounded-[1.75rem] p-2 transition-shadow duration-200 focus-within:ring-4 focus-within:ring-white/50">
                  <label htmlFor="problem" className="block px-4 pt-3 font-display text-lg font-semibold tracking-tight text-ink">
                    Kya problem hai?
                  </label>
                  <textarea
                    id="problem"
                    ref={textRef}
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                    onKeyDown={onKeyDown}
                    rows={4}
                    autoFocus
                    placeholder="English ya Hinglish, dono chalega"
                    className="block min-h-36 w-full resize-none bg-transparent px-4 pt-2 pb-3 text-lg leading-relaxed text-ink outline-none placeholder:text-zinc-400"
                  />
                  <div className="flex items-center justify-between gap-3 p-1">
                    <input
                      ref={fileRef}
                      type="file"
                      accept="image/*"
                      className="sr-only"
                      tabIndex={-1}
                      aria-hidden="true"
                      onChange={(event) => void attach(event.target.files?.[0])}
                    />
                    {photo ? (
                      <div className="flex min-w-0 items-center gap-1 pl-1">
                        <img src={photo.url} alt="Attached photo" className="size-11 rounded-2xl object-cover ring-1 ring-zinc-900/10" />
                        <Button variant="ghost" size="lg" onClick={removePhoto}>
                          Remove
                        </Button>
                      </div>
                    ) : (
                      <Button variant="ghost" size="lg" onClick={() => fileRef.current?.click()}>
                        <ImagePlus className="size-4" aria-hidden="true" />
                        Add photo
                      </Button>
                    )}
                    <Button type="submit" variant="primary" size="lg" disabled={!text.trim()} className="pr-2 pl-5">
                      Send
                      <span className="flex size-7 items-center justify-center rounded-full bg-white/15">
                        <ArrowUp className="size-4" aria-hidden="true" />
                      </span>
                    </Button>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => {
                        setText(example)
                        textRef.current?.focus()
                      }}
                      className="glass press h-11 rounded-full px-4 text-left text-sm font-medium text-zinc-800 sm:h-10"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </form>
            ) : (
              <div className="glass rise flex flex-col gap-4 rounded-[1.75rem] p-4 sm:p-6" aria-live="polite">
                {turns.map((turn, index) => (
                  <TurnView key={index} turn={turn} />
                ))}

                {busy === 'waiting' && (
                  <div role="status" className="rise flex items-center gap-2.5 text-sm font-medium text-zinc-700">
                    <ThinkingOrb state="searching" size={20} theme="light" aria-hidden="true" />
                    <span>Gemma is reading your report</span>
                  </div>
                )}

                {asking && (
                  <form onSubmit={reply} className="rise flex gap-2">
                    <label htmlFor="answer" className="sr-only">
                      Your answer
                    </label>
                    <input
                      id="answer"
                      value={answer}
                      onChange={(event) => setAnswer(event.target.value)}
                      autoFocus
                      autoComplete="off"
                      placeholder="Type your answer"
                      className="h-12 min-w-0 flex-1 rounded-full bg-white px-5 text-base text-ink ring-1 ring-zinc-900/10 outline-none transition-shadow duration-150 placeholder:text-zinc-400 focus:ring-2 focus:ring-indigo-600"
                    />
                    <Button type="submit" variant="primary" size="lg" className="h-12" disabled={!answer.trim()}>
                      Reply
                    </Button>
                  </form>
                )}

                {finished && (
                  <div className="rise flex flex-wrap gap-2">
                    {last.result.status === 'error' ? (
                      <Button variant="primary" size="lg" onClick={() => reset(true)}>
                        Try again
                      </Button>
                    ) : (
                      <Button variant="primary" size="lg" onClick={() => reset()}>
                        Report another
                      </Button>
                    )}
                    <Link
                      to="/board"
                      className="press inline-flex h-11 items-center gap-2 rounded-full px-5 text-sm font-medium text-ink transition-colors duration-150 hover:bg-zinc-900/5"
                    >
                      See it on the board
                      <ArrowRight className="size-4" aria-hidden="true" />
                    </Link>
                  </div>
                )}
                <div ref={endRef} className="h-px" />
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

/** Words rise out of a blur, one after another. */
function Reveal({ text, delay = 0, className }: { text: string; delay?: number; className?: string }) {
  return (
    <span className={className}>
      {text.split(' ').map((word, index) => (
        <motion.span
          key={index}
          className="inline-block whitespace-pre"
          initial={{ opacity: 0, transform: 'translateY(0.35em)', filter: 'blur(12px)' }}
          animate={{ opacity: 1, transform: 'translateY(0em)', filter: 'blur(0px)' }}
          transition={{ duration: 0.7, delay: delay + index * 0.08, ease: [0.23, 1, 0.32, 1] }}
        >
          {word}{' '}
        </motion.span>
      ))}
    </span>
  )
}

function Pitch({ busy, asking, finished }: { busy: Busy; asking: boolean; finished: boolean }) {
  const stats = usePolling(() => api.stats(), 'pitch', 15000).data

  let orb: 'breathing' | 'searching' | 'composing' | 'listening' = 'breathing'
  let status = 'Ready when you are'
  if (busy === 'waiting') [orb, status] = ['searching', 'Reading it and checking for duplicates']
  else if (busy === 'revealing') [orb, status] = ['composing', 'Writing it up']
  else if (asking) [orb, status] = ['listening', 'Waiting for your answer']
  else if (finished) status = 'Done. Next one?'

  return (
    <div className="min-w-0">
      <p className="glass inline-flex h-9 items-center gap-2 rounded-full px-4 text-xs font-semibold tracking-wide text-ink">
        <span className="live-dot text-indigo-600" aria-hidden="true" />
        Campus complaints, triaged by Gemma 4
      </p>

      <h1 className="mt-6 font-display text-[clamp(3.25rem,9vw,6.5rem)] leading-[0.92] font-extrabold tracking-[-0.04em] text-ink">
        <Reveal text="Shikayat hai?" className="block" />
        <Reveal text="Bol do." delay={0.22} className="block text-indigo-700" />
      </h1>

      <p className="mt-6 max-w-[46ch] text-lg leading-relaxed text-zinc-800">
        No forms. Type it like a WhatsApp rant in English, Hinglish or Hindi, add a photo if you have one. Gemma files it,
        merges duplicates and asks back only when a detail is missing.
      </p>

      <div className="mt-8 flex items-center gap-4">
        <span className="glass flex size-[4.5rem] shrink-0 items-center justify-center rounded-full">
          <ThinkingOrb state={orb} size={64} theme="light" paused={finished} aria-hidden="true" style={{ width: 56, height: 56 }} />
        </span>
        <p role="status" className="min-w-0">
          <span className="block font-display text-lg font-semibold tracking-tight text-ink">Gemma 4</span>
          <span className="block text-sm text-zinc-700">{status}</span>
        </p>
      </div>

      <dl className="mt-8 flex flex-wrap gap-x-8 gap-y-4">
        {[
          { label: 'open issues', value: stats?.kpis.open },
          { label: 'reports this week', value: stats?.kpis.reported_7d },
          { label: 'escalated', value: stats?.kpis.escalated },
        ].map((item) => (
          <div key={item.label}>
            <dd className="font-display text-4xl leading-none font-bold tracking-tight text-ink">
              {item.value === undefined ? <span className="text-zinc-400">--</span> : <Ticker value={item.value} />}
            </dd>
            <dt className="mt-1 text-sm text-zinc-700">{item.label}</dt>
          </div>
        ))}
      </dl>
    </div>
  )
}

function TurnView({ turn }: { turn: Turn }) {
  if (turn.kind === 'student') {
    return (
      <div className="rise ml-auto flex max-w-[85%] flex-col items-end gap-2">
        {turn.photo && <img src={turn.photo} alt="Photo you attached" className="max-h-48 rounded-2xl object-cover ring-1 ring-zinc-900/10" />}
        <p className="rounded-3xl rounded-br-lg bg-ink px-5 py-3 text-base leading-relaxed break-words text-white">{turn.text}</p>
      </div>
    )
  }

  if (turn.kind === 'steps') {
    return (
      <ul className="flex flex-col gap-2">
        {turn.labels.map((label, index) => (
          <li key={index} className="rise flex items-start gap-2.5 text-sm text-zinc-700">
            <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white">
              <Check className="size-3" strokeWidth={3} aria-hidden="true" />
            </span>
            {label}
          </li>
        ))}
      </ul>
    )
  }

  if (turn.kind === 'question') {
    return (
      <div className="rise max-w-[90%] rounded-3xl rounded-bl-lg bg-indigo-600 px-5 py-4 text-white">
        <p className="text-xs font-semibold tracking-wide text-indigo-100">Gemma needs one detail</p>
        <p className="mt-1 font-display text-xl leading-snug font-semibold tracking-tight">{turn.text}</p>
      </div>
    )
  }

  return <ResultCard result={turn.result} />
}

function ResultCard({ result }: { result: ReportResult }) {
  const { status, complaint, message } = result

  let icon: ReactNode = <CircleCheck className="size-6 text-indigo-600" aria-hidden="true" />
  let title = 'Done'
  if (status === 'filed') title = complaint ? `Filed as #${complaint.id}` : 'Filed'
  if (status === 'merged') title = complaint ? `Added to #${complaint.id}` : 'Added to an existing complaint'
  if (status === 'rejected') {
    title = 'Not a campus issue'
    icon = <Ban className="size-6 text-zinc-500" aria-hidden="true" />
  }
  if (status === 'error') {
    title = 'That did not go through'
    icon = <TriangleAlert className="size-6 text-zinc-500" aria-hidden="true" />
  }

  return (
    <section className="rise overflow-hidden rounded-3xl bg-white ring-1 ring-zinc-900/10">
      <div className="flex items-start gap-3 p-5">
        <span className="mt-0.5 shrink-0">{icon}</span>
        <div className="min-w-0">
          <h2 className="font-display text-2xl leading-tight font-bold tracking-tight text-ink tabular-nums">{title}</h2>
          {message && <p className="mt-1 text-sm break-words text-zinc-600">{message}</p>}
        </div>
      </div>

      {complaint && (
        <div className="flex items-stretch gap-5 border-t border-zinc-900/10 p-5">
          <div className="flex shrink-0 flex-col justify-center border-r border-zinc-900/10 pr-5">
            <Ticker value={complaint.report_count} className="font-display text-6xl leading-none font-extrabold tracking-tight text-ink" />
            <span className="mt-1 text-xs font-medium text-zinc-600">
              {status === 'merged' ? 'students reported this' : complaint.report_count === 1 ? 'report so far' : 'reports so far'}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-ink">{complaint.summary}</p>
            <p className="mt-0.5 text-sm text-zinc-600">{[complaint.domain, complaint.category, place(complaint)].filter(Boolean).join(' · ')}</p>
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
              <StatusPill status={complaint.status} />
              <SeverityTag severity={complaint.severity} />
              {complaint.escalated && (
                <span className="inline-flex h-6 items-center gap-1 rounded-full bg-ink px-2 text-xs font-semibold text-white">
                  <Flame className="size-3.5" aria-hidden="true" />
                  Escalated
                </span>
              )}
            </div>
            <p className="mt-3 text-xs text-zinc-500">Goes to {complaint.authority}</p>
          </div>
        </div>
      )}
    </section>
  )
}
