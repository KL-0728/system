import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from './api/auth';
import Navigation, { type PageName } from './components/Navigation';
import type { EffectiveTheme, ThemePreference } from './components/ThemeToggle';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import OperationsPage from './pages/OperationsPage';
import SettingsPage from './pages/SettingsPage';
import ReviewPage from './pages/ReviewPage';
import ReportsPage from './pages/ReportsPage';
import type { CurrentUser } from './types/auth';
import { ApiError, UNAUTHORIZED_EVENT } from './api/client';

const themeStorageKey = 'zhunan-theme';

function storedTheme(): ThemePreference {
  try {
    const value = window.localStorage.getItem(themeStorageKey);
    return value === 'light' || value === 'dark' ? value : 'system';
  } catch { return 'system'; }
}

function resolveTheme(preference: ThemePreference): EffectiveTheme {
  return preference === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : preference;
}

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<PageName>(() => window.location.hash === '#reviews' ? 'reviews' : window.location.hash === '#reports' ? 'reports' : 'home');
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  const [themePreference, setThemePreference] = useState<ThemePreference>(storedTheme);
  const [effectiveTheme, setEffectiveTheme] = useState<EffectiveTheme>(() => resolveTheme(themePreference));
  useEffect(() => {
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
    const applyTheme = () => {
      const nextTheme = themePreference === 'system' ? (systemTheme.matches ? 'dark' : 'light') : themePreference;
      document.documentElement.dataset.theme = nextTheme;
      setEffectiveTheme(nextTheme);
    };
    applyTheme();
    if (typeof systemTheme.addEventListener === 'function') {
      systemTheme.addEventListener('change', applyTheme);
      return () => systemTheme.removeEventListener('change', applyTheme);
    }
    systemTheme.addListener(applyTheme);
    return () => systemTheme.removeListener(applyTheme);
  }, [themePreference]);
  function changeTheme(value: ThemePreference) {
    setThemePreference(value);
    try { window.localStorage.setItem(themeStorageKey, value); } catch { /* Private browsing can deny storage. */ }
  }
  useEffect(() => { getCurrentUser().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  useEffect(() => {
    const onUnauthorized = () => { setUser(null); setPage('home'); setLogoutError(''); };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);
  useEffect(() => {
    const onHashChange = () => {
      if (window.location.hash === '#reviews') setPage('reviews');
      else if (window.location.hash === '#reports') setPage('reports');
      else setPage((current) => current === 'reviews' || current === 'reports' ? 'home' : current);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  function handleNavigate(next: PageName) {
    if (next === 'reviews' || next === 'reports') window.location.hash = next;
    else if (window.location.hash === '#reviews' || window.location.hash === '#reports') window.history.replaceState(null, '', window.location.pathname + window.location.search);
    setPage(next);
  }
  async function handleLogout() {
    setLoggingOut(true); setLogoutError('');
    try { await logout(); setUser(null); handleNavigate('home'); }
    catch (error) {
      if (error instanceof ApiError && error.status === 401) setUser(null);
      else setLogoutError('登出未完成，請確認連線後再按一次登出。');
    } finally { setLoggingOut(false); }
  }
  if (loading) return <main><p role="status">正在確認登入狀態…</p></main>;
  if (!user) return <LoginPage onLogin={setUser} themePreference={themePreference} effectiveTheme={effectiveTheme} onThemeChange={changeTheme} />;
  return <><Navigation user={user} page={page} onNavigate={handleNavigate} onLogout={handleLogout} busy={loggingOut}
    themePreference={themePreference} effectiveTheme={effectiveTheme} onThemeChange={changeTheme} />
    {logoutError && <p role="alert" className="app-shell error">{logoutError}</p>}
    {page === 'home' && <HomePage user={user} />}
    {page === 'operations' && <OperationsPage role={user.role} />}
    {page === 'settings' && user.role === 'ADMIN' && <SettingsPage />}
    {page === 'reviews' && (user.role === 'ADMIN' ? <ReviewPage /> : <main className="app-shell"><h1>權限不足</h1><p>管理者審核頁僅供管理者使用。</p></main>)}
    {page === 'reports' && (user.role === 'ADMIN' ? <ReportsPage /> : <main className="app-shell"><h1>權限不足</h1><p>管理者報表僅供管理者使用。</p></main>)}
  </>;
}
