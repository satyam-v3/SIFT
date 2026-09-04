import React from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  CheckSquare,
  Sparkles,
  Network,
  ShieldAlert,
  ListTodo,
  Building2,
  Settings,
  LogOut,
  Shield,
  UserCheck,
  ClipboardCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useReportsContext } from '../../context/ReportsContext';

export function Sidebar({ isOpen, onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentUser, logout, availableUsers, switchUser } = useAuth();
  const { reports, actions } = useReportsContext();

  const pendingReviewsCount = reports.filter((r) => r.reviewStatus === 'PENDING').length;
  const openActionsCount = actions.filter((a) => a.status === 'Open' || a.status === 'In Progress').length;

  const navSections = [
    {
      label: 'Overview',
      items: [
        { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, exact: true },
      ],
    },
    {
      label: 'Reports',
      items: [
        { name: 'All Reports', path: '/reports', icon: FileText, count: reports.length },
        { name: 'Review Queue', path: '/review', icon: CheckSquare, count: pendingReviewsCount, highlight: pendingReviewsCount > 0 },
        { name: 'Analyze Report', path: '/analyze', icon: Sparkles, badge: 'AI' },
      ],
    },
    {
      label: 'Intelligence',
      items: [
        { name: 'Safety Intelligence', path: '/intelligence', icon: Network },
        { name: 'Life-Saving Rules', path: '/life-saving-rules', icon: ShieldAlert },
      ],
    },
    {
      label: 'Operations',
      items: [
        { name: 'Annotation Workbench', path: '/annotations', icon: ClipboardCheck },
        { name: 'Actions', path: '/actions', icon: ListTodo, count: openActionsCount },
        { name: 'Facilities', path: '/facilities', icon: Building2 },
      ],
    },
    {
      label: 'System',
      items: [
        { name: 'Settings', path: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-stone-950/30 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-72 bg-[#FAF7F2]/95 backdrop-blur-md border-r border-surface-border/80 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 sm:p-6 border-b border-surface-border/60 flex items-center justify-between">
          <NavLink to="/dashboard" className="flex items-center gap-3 group" onClick={() => onClose && onClose()}>
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-b from-[#058867] to-[#046B4F] flex items-center justify-center text-white shadow-btn-emerald border border-[#045D44] group-hover:scale-105 transition-transform">
              <Shield className="w-5 h-5 text-emerald-100" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-black text-lg text-ink-primary tracking-tight font-sans">SIFT</span>
                <span className="text-[10px] uppercase font-extrabold tracking-widest px-2 py-0.2 rounded-full bg-amber-100 text-amber-950 border border-amber-200/80">
                  OIL
                </span>
              </div>
              <p className="text-[10px] text-ink-muted leading-tight font-medium">Safety Intelligence & Fatality-risk</p>
            </div>
          </NavLink>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
          {navSections.map((section) => (
            <div key={section.label}>
              <div className="px-3.5 mb-2 text-[10px] font-extrabold uppercase tracking-widest text-ink-muted">
                {section.label}
              </div>
              <div className="space-y-1">
                {section.items.map((item) => {
                  const isActive =
                    item.exact || item.path === '/dashboard'
                      ? location.pathname === item.path || location.pathname === '/'
                      : location.pathname.startsWith(item.path);

                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => onClose && onClose()}
                      className={`flex items-center justify-between px-4 py-2.5 rounded-2xl text-xs font-bold transition-all duration-150 group ${
                        isActive
                          ? 'bg-gradient-to-b from-[#058867] to-[#046B4F] text-white shadow-btn-emerald border border-[#045D44]'
                          : 'text-ink-secondary hover:text-ink-primary hover:bg-[#EFEAE1]/70'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <item.icon
                          className={`w-4 h-4 ${
                            isActive ? 'text-emerald-100' : 'text-ink-muted group-hover:text-ink-primary'
                          }`}
                        />
                        <span>{item.name}</span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {item.badge && (
                          <span
                            className={`text-[10px] font-extrabold px-2 py-0.2 rounded-full ${
                              isActive
                                ? 'bg-white/20 text-white'
                                : 'bg-emerald-50 text-emerald-900 border border-emerald-200/80'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}

                        {item.count !== undefined && (
                          <span
                            className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full font-mono ${
                              isActive
                                ? 'bg-white/20 text-white'
                                : item.highlight
                                ? 'bg-amber-100 text-amber-950 font-extrabold border border-amber-300'
                                : 'bg-[#EAE3D6] text-ink-secondary'
                            }`}
                          >
                            {item.count}
                          </span>
                        )}
                      </div>
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Profile Card */}
        <div className="p-3.5 border-t border-surface-border/60 bg-[#FAF7F2]/90">
          <div className="p-3 rounded-2.5xl bg-white border border-surface-border/80 shadow-spatial-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 overflow-hidden">
                <img
                  src={currentUser?.avatar}
                  alt={currentUser?.name}
                  className="w-9 h-9 rounded-2xl object-cover border border-surface-border/80 shrink-0"
                />
                <div className="overflow-hidden">
                  <h4 className="text-xs font-bold text-ink-primary truncate">{currentUser?.name}</h4>
                  <p className="text-[10px] text-emerald-800 font-bold truncate">{currentUser?.role}</p>
                </div>
              </div>

              <button
                onClick={logout}
                title="Sign out"
                className="p-1.5 text-ink-muted hover:text-red-700 hover:bg-red-50 rounded-xl transition-colors shrink-0 cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Role Switcher Selector */}
            <div className="mt-2.5 pt-2 border-t border-surface-border/50">
              <div className="flex items-center justify-between text-[10px] text-ink-muted mb-1 font-bold">
                <span>Active Persona</span>
                <span className="text-emerald-800 font-extrabold">Demo Role</span>
              </div>
              <select
                value={currentUser?.userId}
                onChange={(e) => switchUser(e.target.value)}
                className="w-full text-xs font-bold text-ink-primary bg-[#FAF7F2] border border-surface-border/80 rounded-xl px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-700 cursor-pointer"
              >
                {availableUsers.map((u) => (
                  <option key={u.userId} value={u.userId}>
                    {u.name} ({u.role})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
