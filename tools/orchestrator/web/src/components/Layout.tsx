import { Link, useLocation } from 'react-router-dom';
import { Activity, GitBranch } from 'lucide-react';
import { useMobile } from '@/hooks';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const isMobile = useMobile();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Activity },
    { path: '/pipelines', label: 'Pipelines', icon: GitBranch },
  ];

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-gray-900">
        {/* Mobile header */}
        <header className="mobile-header">
          <div className="flex items-center gap-2">
            <img src="/atopile-logo.svg" alt="atopile" className="w-5 h-5" />
            <span className="font-semibold">Orchestrator</span>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>

        {/* Bottom navigation */}
        <nav className="mobile-bottom-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`mobile-nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon className="w-6 h-6" />
                <span className="text-xs mt-1">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <aside className="sidebar">
        {/* Logo */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <img src="/atopile-logo.svg" alt="atopile" className="w-6 h-6" />
            <span className="text-lg font-semibold">Orchestrator</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700">
          <div className="text-xs text-gray-500">
            Agent Orchestrator v0.1.0
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}

export default Layout;
