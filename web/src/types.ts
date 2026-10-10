// Mirrors section 6 of docs/BRIEF.md. If the API changes, change this file first.

export type Severity = 'urgent' | 'high' | 'medium' | 'low'
export type Status = 'open' | 'in_progress' | 'resolved'
export type ReportStatus = 'filed' | 'merged' | 'needs_input' | 'rejected' | 'error'

export interface Complaint {
  id: number
  domain: string
  category: string
  authority: string
  building: string | null
  spot: string | null
  meal: string | null
  summary: string
  severity: Severity
  status: Status
  escalated: boolean
  needs_details: boolean
  report_count: number
  priority: number
  photo_count: number
  first_reported_at: string | null
  last_reported_at: string | null
  resolution_note: string | null
  suggested_category: string | null
}

export interface Followup {
  q: string
  a: string
}

export interface Report {
  id: number
  raw_text: string
  photo_url: string | null
  created_at: string
  merge_reason: string | null
  followups: Followup[]
}

export interface ComplaintDetail extends Complaint {
  reports: Report[]
}

export interface Step {
  kind: string
  label?: string
  text?: string
}

export interface ReportResult {
  thread_id: string
  status: ReportStatus
  message: string
  question: string | null
  complaint: Complaint | null
  steps: Step[]
}

export interface Stats {
  kpis: { open: number; reported_7d: number; resolved_7d: number; escalated: number }
  by_domain: { domain: string; open: number; in_progress: number; resolved: number }[]
  top_issues: Pick<
    Complaint,
    'id' | 'summary' | 'domain' | 'priority' | 'report_count' | 'severity' | 'status'
  >[]
  daily: { date: string; reports: number }[]
  other_suggestions: { name: string; count: number }[]
}

export interface Category {
  id: number
  name: string
  domain: string
  authority: string
  required_fields: string[]
}

export const DOMAINS = ['Hostel', 'Mess', 'IT', 'Academic', 'Campus', 'Other'] as const

export const AUTHORITIES = [
  'Hostel Office',
  'Mess Committee',
  'IT Cell',
  'Academic Office',
  'Estate Office',
  'Transport Cell',
  'Admin',
] as const
