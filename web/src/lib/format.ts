import type { Complaint } from '../types'

const IST = 'Asia/Kolkata'
const partsFmt = new Intl.DateTimeFormat('en-US', { day: '2-digit', month: 'short', year: 'numeric', timeZone: IST })
const timeFmt = new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: IST })

// Assembled by hand so the month is always three letters ("Sep", never "Sept").
function dateParts(iso: string) {
  const parts = Object.fromEntries(partsFmt.formatToParts(new Date(iso)).map((part) => [part.type, part.value]))
  return { day: parts.day, month: parts.month, year: parts.year }
}

/** 10 Oct 2026 */
export function formatDate(iso: string | null) {
  if (!iso) return ''
  const { day, month, year } = dateParts(iso)
  return `${day} ${month} ${year}`
}
/** 10 Oct */
export function formatShortDate(iso: string) {
  const { day, month } = dateParts(iso)
  return `${Number(day)} ${month}`
}
/** 1:02 pm */
export const formatTime = (iso: string | null) => (iso ? timeFmt.format(new Date(iso)).toLowerCase() : '')

/** "2 h ago", falling back to a date once it is more than a week old. */
export function timeAgo(iso: string | null, now = Date.now()) {
  if (!iso) return ''
  const minutes = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60000))
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days} d ago`
  return formatDate(iso)
}

/** "BH2 (Gopad) · E207". Spot and meal are often null; a Mess complaint has no spot. */
export function place(c: Pick<Complaint, 'building' | 'spot' | 'meal'>) {
  return [c.building, c.spot, c.meal].filter(Boolean).join(' · ')
}

export function ordinal(n: number) {
  const tens = n % 100
  if (tens >= 11 && tens <= 13) return `${n}th`
  return `${n}${['th', 'st', 'nd', 'rd'][n % 10] ?? 'th'}`
}

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

/** Every word of the query must appear somewhere in the complaint: summary, place, category, "#48", status. */
export function matches(c: Complaint, query: string) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return true
  const haystack = [`#${c.id}`, c.summary, c.domain, c.category, c.authority, c.building, c.spot, c.meal, c.severity, c.status.replace('_', ' ')]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return words.every((word) => haystack.includes(word))
}
