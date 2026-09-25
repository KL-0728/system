import OutboundPage from './OutboundPage';

const operations = ['入庫', '移位', '盤點／損耗'];

export default function OperationsPage({ role }: { role: 'ADMIN' | 'WORKER' }) {
  return <main className="app-shell">
    <p className="eyebrow">倉管操作</p><h1>選擇工作</h1>
    {role === 'WORKER' ? <OutboundPage /> : <p className="notice">出庫請使用倉管帳號登入操作。</p>}
    <div className="action-grid">{operations.map((name) => <section className="card" key={name}><h2>{name}</h2><p>功能片段待負責組員合併後串接。</p><button disabled>尚未開放</button></section>)}</div>
  </main>;
}
