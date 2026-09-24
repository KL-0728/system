import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from './api/auth';
import Navigation, { type PageName } from './components/Navigation';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import OperationsPage from './pages/OperationsPage';
import SettingsPage from './pages/SettingsPage';
import type { CurrentUser } from './types/auth';

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<PageName>('home');
  const [loggingOut, setLoggingOut] = useState(false);
  useEffect(() => { getCurrentUser().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  async function handleLogout() { setLoggingOut(true); try { await logout(); setUser(null); setPage('home'); } finally { setLoggingOut(false); } }
  if (loading) return <main><p role="status">正在確認登入狀態…</p></main>;
  if (!user) return <LoginPage onLogin={setUser} />;
  return <><Navigation user={user} page={page} onNavigate={setPage} onLogout={handleLogout} busy={loggingOut} />
    {page === 'home' && <HomePage user={user} />}
    {page === 'operations' && <OperationsPage />}
    {page === 'settings' && user.role === 'ADMIN' && <SettingsPage />}
  </>;
}
