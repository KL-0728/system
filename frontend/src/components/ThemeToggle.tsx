export type ThemePreference = 'system' | 'light' | 'dark';
export type EffectiveTheme = 'light' | 'dark';

export default function ThemeToggle({ value, effectiveTheme, onChange }: {
  value: ThemePreference;
  effectiveTheme: EffectiveTheme;
  onChange: (value: ThemePreference) => void;
}) {
  const nextTheme = effectiveTheme === 'dark' ? 'light' : 'dark';
  const currentLabel = value === 'system' ? `跟隨系統（目前${effectiveTheme === 'dark' ? '深色' : '淺色'}）` : effectiveTheme === 'dark' ? '深色' : '淺色';
  return <div className="theme-control">
    <button type="button" className="secondary theme-switch"
      aria-label={`${currentLabel}；切換為${nextTheme === 'dark' ? '深色' : '淺色'}`}
      title={`切換為${nextTheme === 'dark' ? '深色' : '淺色'}`}
      onClick={() => onChange(nextTheme)}>
      {nextTheme === 'dark'
        ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.1A8.5 8.5 0 0 1 9.9 3.5 8.5 8.5 0 1 0 20.5 14.1Z" /></svg>
        : <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>}
    </button>
  </div>;
}
