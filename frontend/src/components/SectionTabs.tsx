export interface SectionTab {
  id: string;
  label: string;
}

export default function SectionTabs({ items, active, onChange }: {
  items: SectionTab[];
  active: string;
  onChange: (id: string) => void;
}) {
  return <nav className="section-tabs" role="tablist" aria-label="選擇功能">
    {items.map(({ id, label }, index) => <button key={id} type="button" role="tab"
      id={`${id}-tab`} aria-controls={id} aria-selected={active === id}
      className={active === id ? 'active' : 'secondary'} onClick={() => onChange(id)}
      onKeyDown={(event) => {
        const next = event.key === 'ArrowRight' ? (index + 1) % items.length
          : event.key === 'ArrowLeft' ? (index - 1 + items.length) % items.length
            : event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : -1;
        if (next < 0) return;
        event.preventDefault();
        onChange(items[next].id);
        document.getElementById(`${items[next].id}-tab`)?.focus();
      }}>{label}</button>)}
  </nav>;
}
