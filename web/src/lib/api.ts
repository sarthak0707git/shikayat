import type { Category, Complaint, ComplaintDetail, ReportResult, Stats, Status } from '../types'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError('Cannot reach the server. Check that the API is running.', 0)
  }
  if (!response.ok) {
    let message = response.status >= 500 ? 'Gemma is busy. Please try again.' : 'That did not work.'
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') message = body.detail
    } catch {
      /* not JSON: keep the plain message */
    }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

function query(params: Record<string, string | undefined | null>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value) search.set(key, value)
  const text = search.toString()
  return text ? `?${text}` : ''
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  sendReport(text: string, photo?: Blob | null) {
    const form = new FormData()
    form.set('text', text)
    if (photo) form.set('photo', photo, 'photo.jpg')
    return request<ReportResult>('/api/report', { method: 'POST', body: form })
  },
  sendAnswer(threadId: string, answer: string) {
    return request<ReportResult>(`/api/report/${threadId}/answer`, json('POST', { answer }))
  },
  complaints(params: { domain?: string; authority?: string; status?: string; sort?: 'priority' | 'recent' } = {}) {
    return request<Complaint[]>(`/api/complaints${query(params)}`)
  },
  complaint(id: number) {
    return request<ComplaintDetail>(`/api/complaints/${id}`)
  },
  setStatus(id: number, status: Status, note?: string) {
    return request<Complaint>(`/api/complaints/${id}`, json('PATCH', { status, note: note || null }))
  },
  stats(domain?: string) {
    return request<Stats>(`/api/stats${query({ domain })}`)
  },
  categories() {
    return request<Category[]>('/api/categories')
  },
  createCategory(body: Omit<Category, 'id'>) {
    return request<Category>('/api/categories', json('POST', body))
  },
}
