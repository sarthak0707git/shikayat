import { NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import { cx } from './components/ui'
import Authority from './pages/Authority'
import Board from './pages/Board'
import Report from './pages/Report'

const TABS = [
  { to: '/', label: 'Report' },
  { to: '/board', label: 'Board' },
  { to: '/authority', label: 'Authority' },
]

function Shell() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <NavLink to="/" className="text-[15px] font-semibold tracking-tight text-zinc-900">
            Shikayat
          </NavLink>
          <nav aria-label="Main" className="flex h-full items-stretch gap-1">
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.to === '/'}
                className={({ isActive }) =>
                  cx(
                    'relative flex min-w-11 items-center px-3 text-sm font-medium transition-colors duration-150',
                    isActive ? 'text-zinc-900' : 'text-zinc-500 hover:text-zinc-900',
                    isActive && 'after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:bg-indigo-600',
                  )
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Report />} />
          <Route path="board" element={<Board />} />
          <Route path="authority" element={<Authority />} />
        </Route>
      </Routes>
      <Toaster position="top-center" theme="light" toastOptions={{ style: { borderRadius: 12 } }} />
    </>
  )
}
