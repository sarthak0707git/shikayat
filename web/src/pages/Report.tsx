import { ArrowRight, Ban, Check, CircleCheck, ImagePlus, SendHorizontal, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ThinkingOrb } from 'thinking-orbs'
import { Button, CountBadge, SeverityTag, StatusPill } from '../components/ui'
import { api } from '../lib/api'
import { place, plural } from '../lib/format'
import type { ReportResult } from '../types'

const EXAMPLES = ['dal mein keeda tha aaj lunch mein', 'AC se paani tapak raha hai', 'the moon is too bright']

type Turn =
  | { kind: 'student'; text: string; photo?: string }
  | { kind: 'steps'; labels: string[] }
  | { kind: 'question'; text: string }
  | { kind: 'result'; result: ReportResult }

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
  const [busy, setBusy] = useState<null | 'waiting' | 'revealing'>(null)
  const [threadId, setThreadId] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')

  const textRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const last = turns[turns.length - 1]
  const started = turns.length > 0
  const asking = !busy && last?.kind === 'question'
  const finished = !busy && last?.kind === 'result'

  useEffect(() => {
    if (started) endRef.current?.scrollIntoView({ block: 'end', behavior: reducedMotion() ? 'auto' : 'smooth' })
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
        await sleep(reducedMotion() ? 0 : 420)
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
      await play(await api.sendReport(message, photo?.blob))
      setText('')
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

  function reset() {
    removePhoto()
    setTurns([])
    setThreadId(null)
    setText('')
    setAnswer('')
    requestAnimationFrame(() => textRef.current?.focus())
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void submit()
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6 sm:py-12">
      <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Report a campus problem</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Write it the way you would tell a friend. Gemma sorts it, checks whether it is already reported, and asks
        if something is missing.
      </p>

      {!started && (
        <form onSubmit={submit} className="mt-6">
          <label htmlFor="problem" className="text-sm font-medium text-zinc-900">
            Kya problem hai?
          </label>
          <div className="mt-2 rounded-xl border border-zinc-300 bg-white transition-colors duration-150 focus-within:border-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600/15">
            <textarea
              id="problem"
              ref={textRef}
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={onKeyDown}
              rows={4}
              autoFocus
              placeholder="English ya Hinglish, dono chalega"
              className="block min-h-32 w-full resize-none rounded-xl bg-transparent p-4 text-base text-zinc-900 outline-none placeholder:text-zinc-400"
            />
            <div className="flex items-center justify-between gap-3 border-t border-zinc-100 p-2">
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
                <div className="flex min-w-0 items-center gap-2">
                  <img src={photo.url} alt="Attached photo" className="size-11 rounded-lg border border-zinc-200 object-cover" />
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
              <Button type="submit" variant="primary" size="lg" disabled={!text.trim()}>
                Send
                <SendHorizontal className="size-4" aria-hidden="true" />
              </Button>
            </div>
          </div>

          <p className="mt-6 text-xs font-medium text-zinc-500">Or try an example</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => {
                  setText(example)
                  textRef.current?.focus()
                }}
                className="press h-11 rounded-full border border-zinc-200 px-4 text-left text-sm text-zinc-700 transition-colors duration-150 hover:bg-zinc-50 sm:h-9 sm:px-3"
              >
                {example}
              </button>
            ))}
          </div>
        </form>
      )}

      {started && (
        <div className="mt-6 flex flex-col gap-4" aria-live="polite">
          {turns.map((turn, index) => (
            <TurnView key={index} turn={turn} />
          ))}

          {busy === 'waiting' && (
            <div role="status" className="rise flex items-center gap-2 text-sm text-zinc-600">
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
                className="h-11 min-w-0 flex-1 rounded-[10px] border border-zinc-300 px-3 text-base text-zinc-900 outline-none transition-colors duration-150 placeholder:text-zinc-400 focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/15"
              />
              <Button type="submit" variant="primary" size="lg" disabled={!answer.trim()}>
                Reply
              </Button>
            </form>
          )}

          {finished && (
            <div className="rise flex flex-wrap gap-2 pt-2">
              <Button size="lg" onClick={reset}>
                Report another
              </Button>
              <Link
                to="/board"
                className="press inline-flex h-11 items-center gap-2 rounded-[10px] px-4 text-sm font-medium text-indigo-700 transition-colors duration-150 hover:bg-indigo-50"
              >
                See the board
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </div>
          )}
          <div ref={endRef} className="h-px scroll-mb-8" />
        </div>
      )}
    </div>
  )
}

function TurnView({ turn }: { turn: Turn }) {
  if (turn.kind === 'student') {
    return (
      <div className="rise ml-auto flex max-w-[85%] flex-col items-end gap-2">
        {turn.photo && (
          <img src={turn.photo} alt="Photo you attached" className="max-h-48 rounded-xl border border-zinc-200 object-cover" />
        )}
        <p className="rounded-xl bg-zinc-100 px-4 py-2.5 text-[15px] leading-relaxed break-words text-zinc-900">{turn.text}</p>
      </div>
    )
  }

  if (turn.kind === 'steps') {
    return (
      <ul className="flex flex-col gap-1.5">
        {turn.labels.map((label, index) => (
          <li key={index} className="rise flex items-start gap-2 text-sm text-zinc-600">
            <Check className="mt-0.5 size-4 shrink-0 text-zinc-400" aria-hidden="true" />
            {label}
          </li>
        ))}
      </ul>
    )
  }

  if (turn.kind === 'question') {
    return (
      <div className="rise max-w-[85%] rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3">
        <p className="text-xs font-medium text-indigo-700">Gemma needs one detail</p>
        <p className="mt-1 text-[15px] leading-relaxed text-zinc-900">{turn.text}</p>
      </div>
    )
  }

  return <ResultCard result={turn.result} />
}

function ResultCard({ result }: { result: ReportResult }) {
  const { status, complaint, message } = result

  let icon: ReactNode = <CircleCheck className="size-5 text-indigo-600" aria-hidden="true" />
  let title = 'Done'
  if (status === 'filed') title = complaint ? `Filed as #${complaint.id}` : 'Filed'
  if (status === 'merged') title = complaint ? `Added to #${complaint.id}` : 'Added to an existing complaint'
  if (status === 'rejected') {
    title = 'Not a campus issue'
    icon = <Ban className="size-5 text-zinc-500" aria-hidden="true" />
  }
  if (status === 'error') {
    title = 'That did not go through'
    icon = <TriangleAlert className="size-5 text-zinc-500" aria-hidden="true" />
  }

  return (
    <section className="rise rounded-xl border border-zinc-200 bg-white">
      <div className="flex items-start gap-3 p-4">
        <span className="mt-0.5 shrink-0">{icon}</span>
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold text-zinc-900 tabular-nums">{title}</h2>
          {message && <p className="mt-0.5 text-sm text-zinc-600">{message}</p>}
        </div>
      </div>

      {complaint && (
        <div className="border-t border-zinc-200 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-zinc-900">{complaint.summary}</p>
              <p className="mt-0.5 text-sm text-zinc-500">
                {[complaint.domain, complaint.category, place(complaint)].filter(Boolean).join(' · ')}
              </p>
            </div>
            <StatusPill status={complaint.status} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className="inline-flex items-center gap-2 text-sm text-zinc-700">
              <CountBadge count={complaint.report_count} bumpOnMount={status === 'merged'} />
              {status === 'merged'
                ? `${plural(complaint.report_count, 'student')} reported this`
                : plural(complaint.report_count, 'report')}
            </span>
            <SeverityTag severity={complaint.severity} />
            {complaint.escalated && <span className="text-xs font-medium text-zinc-900">Escalated</span>}
            <span className="text-xs text-zinc-500">Goes to {complaint.authority}</span>
          </div>
        </div>
      )}
    </section>
  )
}
