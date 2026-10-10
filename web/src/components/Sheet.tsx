import { X } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { cx } from './ui'

type SheetProps = {
  open: boolean
  onClose: () => void
  label: string
  children: ReactNode
  footer?: ReactNode
}

/** A right-hand side sheet. Stays mounted so it can slide out; Escape and the backdrop close it. */
export function Sheet({ open, onClose, label, children, footer }: SheetProps) {
  const closeButton = useRef<HTMLButtonElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    closeButton.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current()
    }
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      opener?.focus()
    }
  }, [open])

  return (
    <div className={cx('fixed inset-0 z-40', !open && 'pointer-events-none')} inert={!open}>
      <div
        onClick={onClose}
        className={cx('absolute inset-0 bg-ink/40 backdrop-blur-sm transition-opacity duration-200', open ? 'opacity-100' : 'opacity-0')}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className={cx(
          'sheet absolute inset-y-2 right-2 left-2 flex flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-zinc-900/10 sm:left-auto sm:w-full sm:max-w-lg',
          'transition-transform duration-[280ms] ease-drawer',
          open ? 'translate-x-0' : 'translate-x-[calc(100%+1rem)]',
        )}
      >
        <div className="flex items-center justify-between gap-4 border-b border-zinc-200 py-2 pr-2 pl-5">
          <p className="truncate text-sm font-medium text-zinc-500">{label}</p>
          <button
            ref={closeButton}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="press flex size-11 shrink-0 items-center justify-center rounded-full text-zinc-500 transition-colors duration-150 hover:bg-zinc-100 hover:text-zinc-900"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain px-5 py-5">{children}</div>
        {footer && (
          <div className="border-t border-zinc-200 px-5 pt-4 pb-[max(1rem,env(safe-area-inset-bottom))]">{footer}</div>
        )}
      </aside>
    </div>
  )
}
