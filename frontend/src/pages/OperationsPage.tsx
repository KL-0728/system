import { useState } from 'react';
import InboundPage from './InboundPage';
import InventoryPage from './InventoryPage';
import OutboundPage from './OutboundPage';
import TransferPage from './TransferPage';
import AdjustmentPage from './AdjustmentPage';

export default function OperationsPage({ role }: { role: 'ADMIN' | 'WORKER' }) {
  const [outboundRefresh, setOutboundRefresh] = useState(0);
  const [transferRefresh, setTransferRefresh] = useState(0);
  const [adjustmentRefresh, setAdjustmentRefresh] = useState(0);
  return <main className="app-shell">
    <p className="eyebrow">庫存與倉管操作</p><h1>選擇工作</h1>
    <InventoryPage />
    {role === 'WORKER' ? <>
      <InboundPage onStockChanged={() => { setOutboundRefresh((value) => value + 1); setTransferRefresh((value) => value + 1); setAdjustmentRefresh((value) => value + 1); }} />
      <OutboundPage refreshKey={outboundRefresh} onStockChanged={() => { setTransferRefresh((value) => value + 1); setAdjustmentRefresh((value) => value + 1); }} />
      <TransferPage refreshKey={transferRefresh} onStockChanged={() => { setOutboundRefresh((value) => value + 1); setAdjustmentRefresh((value) => value + 1); }} />
      <AdjustmentPage refreshKey={adjustmentRefresh} onRequestCreated={() => { setOutboundRefresh((value) => value + 1); setTransferRefresh((value) => value + 1); }} />
    </> : <p className="notice">入庫、出庫、移位與盤點申請請使用倉管帳號登入操作；審核請點上方「審核申請」。</p>}
  </main>;
}
