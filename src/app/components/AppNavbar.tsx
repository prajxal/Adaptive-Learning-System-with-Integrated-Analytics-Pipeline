import React from 'react';
import { GraduationCap, Menu } from 'lucide-react';
import { UserButton } from '@clerk/clerk-react';

interface AppNavbarProps {
  onMenuClick?: () => void;
  showMenuButton?: boolean;
}

export function AppNavbar({ onMenuClick, showMenuButton = false }: AppNavbarProps) {
  return (
    <nav className="border-b border-[#1e1e2e] bg-[#0a0a0f] sticky top-0 z-40 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            {showMenuButton && (
              <button
                onClick={onMenuClick}
                className="lg:hidden text-[#f1f5f9] hover:text-[#6366f1] transition-colors"
              >
                <Menu className="w-6 h-6" />
              </button>
            )}
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-[6px] flex items-center justify-center shadow-sm">
                <GraduationCap className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="font-semibold text-[#f1f5f9]">LearnPath</span>
                <span className="text-[#6366f1] font-semibold">AI</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[#f1f5f9] hidden sm:block">
              Engineering Learning Platform
            </span>
            <UserButton />
          </div>
        </div>
      </div>
    </nav>
  );
}
