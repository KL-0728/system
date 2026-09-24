import type { CurrentUser } from '../types/auth';

export type PageName = 'home' | 'operations' | 'settings';

export default function Navigation({ user, page, onNavigate, onLogout, busy }: {
  user: CurrentUser;
  page: PageName;
  onNavigate: (page: PageName) => void;
  onLogout: () => void;
  busy: boolean;
}) {
  return <nav className="top-nav" aria-label="主要導覽">
    <strong>竹南冷凍倉儲</strong>
    <div className="nav-links">
      <button className={page === 'home' ? 'active' : 'secondary'} onClick={() => onNavigate('home')}>首頁</button>
      <button className={page === 'operations' ? 'active' : 'secondary'} onClick={() => onNavigate('operations')}>倉管操作</button>
      {user.role === 'ADMIN' && <button className={page === 'settings' ? 'active' : 'secondary'} onClick={() => onNavigate('settings')}>基本資料</button>}
    </div>
    <div className="account"><span>{user.display_name}</span><button className="secondary" disabled={busy} onClick={onLogout}>登出</button></div>
  </nav>;
}
