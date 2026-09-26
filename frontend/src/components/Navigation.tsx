import type { CurrentUser } from '../types/auth';
import ThemeToggle, { type EffectiveTheme, type ThemePreference } from './ThemeToggle';

export type PageName = 'home' | 'operations' | 'settings' | 'reviews' | 'reports';

export default function Navigation({ user, page, onNavigate, onLogout, busy, themePreference, effectiveTheme, onThemeChange }: {
  user: CurrentUser;
  page: PageName;
  onNavigate: (page: PageName) => void;
  onLogout: () => void;
  busy: boolean;
  themePreference: ThemePreference;
  effectiveTheme: EffectiveTheme;
  onThemeChange: (value: ThemePreference) => void;
}) {
  return <nav className="top-nav" aria-label="主要導覽">
    <strong>竹南冷凍倉儲</strong>
    <div className="nav-links">
      <button className={page === 'home' ? 'active' : 'secondary'} onClick={() => onNavigate('home')}>首頁</button>
      <button className={page === 'operations' ? 'active' : 'secondary'} onClick={() => onNavigate('operations')}>倉管操作</button>
      {user.role === 'ADMIN' && <button className={page === 'reviews' ? 'active' : 'secondary'} onClick={() => onNavigate('reviews')}>審核申請</button>}
      {user.role === 'ADMIN' && <button className={page === 'reports' ? 'active' : 'secondary'} onClick={() => onNavigate('reports')}>決策報表</button>}
      {user.role === 'ADMIN' && <button className={page === 'settings' ? 'active' : 'secondary'} onClick={() => onNavigate('settings')}>基本資料</button>}
    </div>
    <div className="account"><span>{user.display_name}</span><ThemeToggle value={themePreference} effectiveTheme={effectiveTheme} onChange={onThemeChange} /><button className="secondary" disabled={busy} onClick={onLogout}>登出</button></div>
  </nav>;
}
