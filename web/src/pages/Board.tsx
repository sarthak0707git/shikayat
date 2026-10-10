import { EmptyState } from '../components/ui'

export default function Board() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <EmptyState title="Board" hint="This page is being built." />
    </div>
  )
}
