import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard, Upload, AlertTriangle, Share2, Clock,
  ShieldCheck, LogOut, Users, ChevronRight,
} from 'lucide-react'

const NAV = [
  { to: '/overview', icon: LayoutDashboard, label: 'Overview' },
  { to: '/audit',    icon: Upload,          label: 'New Audit' },
  { to: '/findings', icon: AlertTriangle,   label: 'Findings' },
  { to: '/graph',    icon: Share2,          label: 'Knowledge Graph' },
  { to: '/history',  icon: Clock,           label: 'History' },
]

export default function Sidebar() {
  const { username, role, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-[220px] shrink-0 flex flex-col bg-[#0c0c18] border-r border-[#1a1a2e] h-screen">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-[#1a1a2e]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-bold text-white leading-tight">Safety Auditor</p>
            <p className="text-[10px] text-gray-600 leading-tight truncate">ICS Pre-Synthesis</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'nav-item-active' : 'nav-item-default'}`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}

        {role === 'admin' && (
          <>
            <div className="pt-3 pb-1 px-3">
              <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Admin</p>
            </div>
            <NavLink
              to="/users"
              className={({ isActive }) =>
                `nav-item ${isActive ? 'nav-item-active' : 'nav-item-default'}`
              }
            >
              <Users className="w-4 h-4 shrink-0" />
              <span className="truncate">Users</span>
            </NavLink>
          </>
        )}
      </nav>

      {/* User footer */}
      <div className="px-3 py-3 border-t border-[#1a1a2e] space-y-2">
        <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-xl bg-white/3">
          <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center text-xs font-bold text-white shrink-0">
            {(username ?? 'U')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-medium text-gray-200 truncate">{username}</p>
            <p className="text-[10px] text-gray-500 capitalize">{role}</p>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-gray-600 shrink-0" />
        </div>
        <button
          onClick={handleLogout}
          className="btn-ghost w-full justify-start text-xs"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
