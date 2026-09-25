import { useState } from 'react';
import OutboundPage from './OutboundPage';
import TransferPage from './TransferPage';

const operations = ['入庫', '盤點／損耗'];

export default function OperationsPage({ role }: { role: 'ADMIN' | 'WORKER' }) {
  const [outboundRefresh, setOutboundRefresh] = useState(0);
  const [transferRefresh, setTransferRefresh] = useState(0);
  return <main className="app-shell">
    <p className="eyebrow">倉管操作</p><h1>選擇工作</h1>
    {role === 'WORKER' ? <>
      <OutboundPage refreshKey={outboundRefresh} onStockChanged={() => setTransferRefresh((value) => value + 1)} />
      <TransferPage refreshKey={transferRefresh} onStockChanged={() => setOutboundRefresh((value) => value + 1)} />
    </> : <p className="notice">出庫與移位請使用倉管帳號登入操作。</p>}
    <div className="action-grid">{operations.map((name) => <section className="card" key={name}><h2>{name}</h2><p>功能片段待負責組員合併後串接。</p><button disabled>尚未開放</button></section>)}</div>
  </main>;
}
