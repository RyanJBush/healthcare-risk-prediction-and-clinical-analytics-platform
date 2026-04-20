import { Link, NavLink } from 'react-router-dom'

const linkClass = ({ isActive }) =>
  `rounded px-3 py-2 text-sm ${isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-200'}`

export default function Layout({ children, onLogout }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/dashboard" className="text-lg font-semibold text-slate-900">
            Nova AI
          </Link>
          <nav className="flex gap-2">
            <NavLink to="/dashboard" className={linkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/patients" className={linkClass}>
              Patients
            </NavLink>
            <NavLink to="/risk-analysis" className={linkClass}>
              Risk Analysis
            </NavLink>
          </nav>
          <button
            type="button"
            onClick={onLogout}
            className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  )
}
