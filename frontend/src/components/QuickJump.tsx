export interface JumpItem {
  id: string;
  label: string;
}

export default function QuickJump({ items }: { items: JumpItem[] }) {
  return <nav className="section-jump" aria-label="快速前往功能">
    {items.map(({ id, label }) => <button key={id} type="button" className="secondary"
      onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>{label}</button>)}
  </nav>;
}
