import { MotionConfig, motion } from 'motion/react'
import { NavLink, Outlet, Route, Routes, useLocation } from 'react-router-dom'
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
  const { pathname } = useLocation()
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pointer-events-none sticky top-0 z-30 px-3 pt-3">
        <div className="glass pointer-events-auto mx-auto flex h-14 max-w-3xl items-center justify-between gap-2 rounded-full py-1.5 pr-1.5 pl-5">
          <NavLink to="/" className="font-display text-xl font-bold tracking-tight text-ink">
            shikayat<span className="text-indigo-600">.</span>
          </NavLink>
          <nav aria-label="Main" className="flex h-full items-stretch">
            {TABS.map((tab) => {
              const active = tab.to === '/' ? pathname === '/' : pathname.startsWith(tab.to)
              return (
                <NavLink
                  key={tab.to}
                  to={tab.to}
                  end={tab.to === '/'}
                  className={cx(
                    'relative flex min-w-11 items-center rounded-full px-3.5 text-sm font-medium transition-colors duration-200 sm:px-5',
                    active ? 'text-white' : 'text-zinc-600 hover:text-ink',
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-full bg-ink"
                      transition={{ type: 'spring', duration: 0.45, bounce: 0.18 }}
                    />
                  )}
                  <span className="relative">{tab.label}</span>
                </NavLink>
              )
            })}
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
    <MotionConfig reducedMotion="user">
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Report />} />
          <Route path="board" element={<Board />} />
          <Route path="authority" element={<Authority />} />
        </Route>
      </Routes>
      <Toaster position="top-center" theme="light" offset={84} toastOptions={{ style: { borderRadius: 16 } }} />
    </MotionConfig>
  )
}
