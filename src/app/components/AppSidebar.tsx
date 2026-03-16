import React from 'react';
import { Home, Map, User, GraduationCap, X, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useClerk } from '@clerk/clerk-react';

interface AppSidebarProps {
  currentPage: string;
  isOpen?: boolean;
  onClose?: () => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Home, path: '/dashboard' },
  { id: 'roadmap', label: 'Learning Path', icon: Map, path: '/roadmaps' },
  { id: 'progress', label: 'My Progress', icon: User, path: '/progress' },
];

export function AppSidebar({ currentPage, isOpen = true, onClose }: AppSidebarProps) {
  const navigate = useNavigate();
  const { signOut } = useClerk();

  const handleLogout = () => {
    signOut(() => navigate('/signin', { replace: true }));
  };

  return (
    <>
      <style>{`
        .app-sidebar-root {
          font-family: 'DM Sans', sans-serif;
        }
        .app-sidebar-logo {
          font-family: 'Sora', sans-serif;
        }
      `}</style>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          app-sidebar-root fixed lg:static top-0 left-0 h-screen bg-[#0a0a0f] border-r border-[#1e1e2e] z-50 flex-shrink-0
          transition-transform duration-200 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          w-[240px]
        `}
      >
        <div className="flex flex-col h-full">
          {/* Header - Mobile Only */}
          <div className="h-16 border-b border-[#1e1e2e] bg-[#0a0a0f] flex items-center justify-between px-4 lg:hidden">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-[#0a0a0f] border border-[#1e1e2e] rounded-[6px] flex items-center justify-center">
                <GraduationCap className="w-5 h-5 text-[#f1f5f9]" />
              </div>
              <span className="app-sidebar-logo text-[#f1f5f9] font-medium">LearnPath AI</span>
            </div>
            <button
              onClick={onClose}
              className="text-[#64748b] hover:text-[#f1f5f9] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Desktop Header */}
          <div className="hidden lg:block h-16 border-b border-[#1e1e2e] px-4">
            <div className="h-full flex items-center">
              <span className="text-[#64748b] font-medium tracking-[0.08em] uppercase text-[11px]">NAVIGATION</span>
            </div>
          </div>

          {/* Menu Items */}
          <nav className="flex-1 p-3 space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => {
                    navigate(item.path);
                    onClose?.();
                  }}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2.5 rounded-[6px] transition-all duration-200 ease-in-out border-l-[3px]
                    ${isActive
                      ? 'bg-[#16161f] text-[#f1f5f9] border-[#6366f1]'
                      : 'text-[#64748b] border-transparent hover:bg-[#111118] hover:text-[#f1f5f9]'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-[#1e1e2e] space-y-4">
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-[#64748b] hover:text-[#ef4444] rounded-md transition-colors font-medium border border-transparent"
            >
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </button>
            <div className="text-[11px] text-[#64748b] text-center">
              <p>© 2026 LearnPath AI</p>
              <p className="mt-1">Engineering Education</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
