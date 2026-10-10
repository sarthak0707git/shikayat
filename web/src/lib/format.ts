import type { Complaint } from '../types'

const IST = 'Asia/Kolkata'
const dateFmt = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: IST })
const shortDateFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: IST })
const timeFmt = new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: IST })

/** 10 Oct 2026 */
export const formatDate = (iso: string | null) => (iso ? dateFmt.format(new Date(iso)) : '')
/** 10 Oct */
export const formatShortDate = (iso: string) => shortDateFmt.format(new Date(iso))
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
