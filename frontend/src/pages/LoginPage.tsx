import { FormEvent, useState } from 'react';
import { login } from '../api/auth';
import ThemeToggle, { type EffectiveTheme, type ThemePreference } from '../components/ThemeToggle';
import type { CurrentUser } from '../types/auth';

export default function LoginPage({ onLogin, themePreference, effectiveTheme, onThemeChange }: {
  onLogin: (user: CurrentUser) => void;
  themePreference: ThemePreference;
  effectiveTheme: EffectiveTheme;
  onThemeChange: (value: ThemePreference) => void;
}) {
  const [username, setUsername] = useState('worker');
  const [password, setPassword] = useState('worker1234');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setMessage('');
    try { onLogin(await login(username, password)); }
    catch (error) { setMessage(error instanceof Error ? error.message : '登入失敗'); }
    finally { setSubmitting(false); }
  }
  return <main className="login-shell"><section className="card login-card" aria-labelledby="login-title">
    <div className="login-head"><p className="eyebrow">竹南冷凍倉儲</p><ThemeToggle value={themePreference} effectiveTheme={effectiveTheme} onChange={onThemeChange} /></div>
    <h1 id="login-title">登入庫存系統</h1>
    <form onSubmit={handleSubmit}>
      <label>帳號<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
      <label>密碼<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
      <button type="submit" disabled={submitting}>{submitting ? '登入中…' : '登入'}</button>
    </form>
    {message && <p className="error" role="alert">{message}</p>}
    <p className="hint">示範帳號：admin／admin1234、worker／worker1234</p>
  </section></main>;
}
