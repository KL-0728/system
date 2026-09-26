import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from './api/auth';
import Navigation, { type PageName } from './components/Navigation';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import OperationsPage from './pages/OperationsPage';
import SettingsPage from './pages/SettingsPage';
import ReviewPage from './pages/ReviewPage';
import type { CurrentUser } from './types/auth';

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<PageName>(() => window.location.hash === '#reviews' ? 'reviews' : 'home');
  const [loggingOut, setLoggingOut] = useState(false);
  useEffect(() => { getCurrentUser().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  useEffect(() => {
    const onHashChange = () => { if (window.location.hash === '#reviews') setPage('reviews'); else setPage((current) => current === 'reviews' ? 'home' : current); };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  function handleNavigate(next: PageName) {
    if (next === 'reviews') window.location.hash = 'reviews';
    else if (window.location.hash === '#reviews') window.history.replaceState(null, '', window.location.pathname + window.location.search);
    setPage(next);
  }
  async function handleLogout() { setLoggingOut(true); try { await logout(); setUser(null); handleNavigate('home'); } finally { setLoggingOut(false); } }
  if (loading) return <main><p role="status">正在確認登入狀態…</p></main>;
  if (!user) return <LoginPage onLogin={setUser} />;
  return <><Navigation user={user} page={page} onNavigate={handleNavigate} onLogout={handleLogout} busy={loggingOut} />
    {page === 'home' && <HomePage user={user} />}
    {page === 'operations' && <OperationsPage role={user.role} />}
    {page === 'settings' && user.role === 'ADMIN' && <SettingsPage />}
    {page === 'reviews' && (user.role === 'ADMIN' ? <ReviewPage /> : <main className="app-shell"><h1>權限不足</h1><p>管理者審核頁僅供管理者使用。</p></main>)}
  </>;
}
