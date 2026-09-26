import { useState } from 'react';
import BackToTop from '../components/BackToTop';
import QuickJump from '../components/QuickJump';
import InboundPage from './InboundPage';
import InventoryPage from './InventoryPage';
import OutboundPage from './OutboundPage';
import TransferPage from './TransferPage';
import AdjustmentPage from './AdjustmentPage';
import LocationMapPage from './LocationMapPage';
import ShortagePage from './ShortagePage';

export default function OperationsPage({ role }: { role: 'ADMIN' | 'WORKER' }) {
  const [inventoryRefresh, setInventoryRefresh] = useState(0);
  const [outboundRefresh, setOutboundRefresh] = useState(0);
  const [transferRefresh, setTransferRefresh] = useState(0);
  const [adjustmentRefresh, setAdjustmentRefresh] = useState(0);
  const [mapRefresh, setMapRefresh] = useState(0);
  function refreshStock() {
    setInventoryRefresh((value) => value + 1);
    setOutboundRefresh((value) => value + 1);
    setTransferRefresh((value) => value + 1);
    setAdjustmentRefresh((value) => value + 1);
    setMapRefresh((value) => value + 1);
  }
  const sections = [
    { id: 'operation-inventory', label: '庫存查詢' },
    { id: 'operation-map', label: '儲位簡圖' },
    ...(role === 'WORKER' ? [
      { id: 'operation-inbound', label: '入庫' },
      { id: 'operation-outbound', label: '出庫' },
      { id: 'operation-transfer', label: '移位' },
      { id: 'operation-adjustment', label: '盤點／損耗' },
      { id: 'operation-shortage', label: '缺貨需求' },
    ] : []),
  ];
  return <main className="app-shell">
    <p className="eyebrow">庫存與倉管操作</p><h1>選擇工作</h1>
    {sections.length > 1 && <QuickJump items={sections} />}
    <div id="operation-inventory" className="operation-anchor"><InventoryPage refreshKey={inventoryRefresh} role={role} /></div>
    <div id="operation-map" className="operation-anchor"><LocationMapPage refreshKey={mapRefresh} /></div>
    {role === 'WORKER' ? <>
      <div id="operation-inbound" className="operation-anchor"><InboundPage onStockChanged={refreshStock} /></div>
      <div id="operation-outbound" className="operation-anchor"><OutboundPage refreshKey={outboundRefresh} onStockChanged={refreshStock} /></div>
      <div id="operation-transfer" className="operation-anchor"><TransferPage refreshKey={transferRefresh} onStockChanged={refreshStock} /></div>
      <div id="operation-adjustment" className="operation-anchor"><AdjustmentPage refreshKey={adjustmentRefresh} onRequestCreated={() => { setOutboundRefresh((value) => value + 1); setTransferRefresh((value) => value + 1); }} /></div>
      <div id="operation-shortage" className="operation-anchor"><ShortagePage /></div>
    </> : <p className="notice">入庫、出庫、移位與盤點申請請使用倉管帳號登入操作；審核請點上方「審核申請」。</p>}
    <BackToTop />
  </main>;
}
