import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from './api/auth';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import type { CurrentUser } from './types/auth';

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { getCurrentUser().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  async function handleLogout() { await logout(); setUser(null); }
  if (loading) return <main><p role="status">正在確認登入狀態…</p></main>;
  if (!user) return <LoginPage onLogin={setUser} />;
  return <HomePage user={user} onLogout={handleLogout} />;
}
