import { useState } from 'react';
import BackToTop from '../components/BackToTop';
import SectionTabs from '../components/SectionTabs';
import InboundPage from './InboundPage';
import InventoryPage from './InventoryPage';
import OutboundPage from './OutboundPage';
import TransferPage from './TransferPage';
import AdjustmentPage from './AdjustmentPage';
import LocationMapPage from './LocationMapPage';
import ShortagePage from './ShortagePage';
import WarehouseCountPage from './WarehouseCountPage';

export default function OperationsPage({ role }: { role: 'ADMIN' | 'WORKER' }) {
  const [refreshAllKey, setRefreshAllKey] = useState(0);
  const [activeSection, setActiveSection] = useState('operation-inventory');
  const [inventoryRefresh, setInventoryRefresh] = useState(0);
  const [outboundRefresh, setOutboundRefresh] = useState(0);
  const [transferRefresh, setTransferRefresh] = useState(0);
  const [adjustmentRefresh, setAdjustmentRefresh] = useState(0);
  const [mapRefresh, setMapRefresh] = useState(0);
  function refreshStock(source: 'inbound' | 'outbound' | 'transfer') {
    setInventoryRefresh((value) => value + 1);
    if (source !== 'outbound') setOutboundRefresh((value) => value + 1);
    if (source !== 'transfer') setTransferRefresh((value) => value + 1);
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
      { id: 'operation-warehouse-count', label: '整庫盤點' },
      { id: 'operation-adjustment', label: '盤點／損耗' },
      { id: 'operation-shortage', label: '缺貨需求' },
    ] : []),
  ];
  return <main className="app-shell">
    <p className="eyebrow">庫存與倉管操作</p><h1>選擇工作</h1>
    <div className="operations-refresh">
      <button type="button" className="secondary" onClick={() => setRefreshAllKey((value) => value + 1)}>一鍵更新本頁資料</button>
      <p className="hint">重新讀取本頁查詢、簡圖與操作紀錄；不會再次送出交易。</p>
    </div>
    <SectionTabs items={sections} active={activeSection} onChange={setActiveSection} />
    <div id="operation-inventory" role="tabpanel" aria-labelledby="operation-inventory-tab" hidden={activeSection !== 'operation-inventory'} className="operation-anchor"><InventoryPage refreshKey={inventoryRefresh + refreshAllKey} role={role} /></div>
    <div id="operation-map" role="tabpanel" aria-labelledby="operation-map-tab" hidden={activeSection !== 'operation-map'} className="operation-anchor"><LocationMapPage refreshKey={mapRefresh + refreshAllKey} /></div>
    {role === 'WORKER' ? <>
      <div id="operation-inbound" role="tabpanel" aria-labelledby="operation-inbound-tab" hidden={activeSection !== 'operation-inbound'} className="operation-anchor"><InboundPage refreshKey={refreshAllKey} onStockChanged={() => refreshStock('inbound')} /></div>
      <div id="operation-outbound" role="tabpanel" aria-labelledby="operation-outbound-tab" hidden={activeSection !== 'operation-outbound'} className="operation-anchor"><OutboundPage refreshKey={outboundRefresh + refreshAllKey} onStockChanged={() => refreshStock('outbound')} /></div>
      <div id="operation-transfer" role="tabpanel" aria-labelledby="operation-transfer-tab" hidden={activeSection !== 'operation-transfer'} className="operation-anchor"><TransferPage refreshKey={transferRefresh + refreshAllKey} onStockChanged={() => refreshStock('transfer')} /></div>
      <div id="operation-warehouse-count" role="tabpanel" aria-labelledby="operation-warehouse-count-tab" hidden={activeSection !== 'operation-warehouse-count'} className="operation-anchor"><WarehouseCountPage refreshKey={refreshAllKey} onRequestCreated={() => { setOutboundRefresh((value) => value + 1); setTransferRefresh((value) => value + 1); }} /></div>
      <div id="operation-adjustment" role="tabpanel" aria-labelledby="operation-adjustment-tab" hidden={activeSection !== 'operation-adjustment'} className="operation-anchor"><AdjustmentPage refreshKey={adjustmentRefresh + refreshAllKey} onRequestCreated={() => { setOutboundRefresh((value) => value + 1); setTransferRefresh((value) => value + 1); }} /></div>
      <div id="operation-shortage" role="tabpanel" aria-labelledby="operation-shortage-tab" hidden={activeSection !== 'operation-shortage'} className="operation-anchor"><ShortagePage refreshKey={refreshAllKey} /></div>
    </> : <p className="notice">入庫、出庫、移位與盤點申請請使用倉管帳號登入操作；審核請點上方「審核申請」。</p>}
    <BackToTop />
  </main>;
}
