import { useEffect, useState } from 'react';
import { getLocations, getProducts } from '../api/masterData';
import { getDecisionReport, type DecisionReport } from '../api/reports';
import type { CurrentUser } from '../types/auth';
import type { Location, Product } from '../types/masterData';

export default function HomePage({ user }: { user: CurrentUser }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [message, setMessage] = useState('正在讀取基本資料…');
  const [report, setReport] = useState<DecisionReport | null>(null);
  const [reportLoading, setReportLoading] = useState(user.role === 'ADMIN');
  const [reportError, setReportError] = useState('');
  async function refreshReport() {
    setReportLoading(true);
    try { setReport(await getDecisionReport()); setReportError(''); }
    catch { setReportError('無法讀取管理統計，請確認連線後再更新。'); }
    finally { setReportLoading(false); }
  }
  useEffect(() => {
    let active = true;
    Promise.all([getProducts(), getLocations()]).then(([productRows, locationRows]) => {
      if (active) { setProducts(productRows); setLocations(locationRows); setMessage(''); }
    }).catch((error) => { if (active) setMessage(error instanceof Error ? error.message : '讀取失敗'); });
    return () => { active = false; };
  }, []);
  useEffect(() => { if (user.role === 'ADMIN') void refreshReport(); }, [user.role]);
  return <main className="app-shell">
    <p className="eyebrow">首頁</p><h1>你好，{user.display_name}</h1><p>{user.role === 'ADMIN' ? '管理者' : '倉管人員'}工作區</p>
    {user.role === 'ADMIN' && <section className="card home-stats" aria-label="管理統計"><h2>管理統計</h2>
      <p className="hint">數字來自目前資料庫；各品項數量不跨單位相加。</p>
      <button type="button" className="secondary" disabled={reportLoading} onClick={() => void refreshReport()}>更新統計</button>
      {reportLoading && <p role="status">正在更新管理統計…</p>}
      {reportError && <p role="alert" className="error">{reportError}</p>}
      {report && <><div className="report-summary">
        <article><strong>{report.summary.in_stock_product_count}</strong><span>目前有庫存品項</span></article>
        <article><strong>{report.summary.low_stock_product_count}</strong><span>低於最低量品項</span></article>
        <article><strong>{report.summary.pending_adjustment_count}</strong><span>待審申請</span></article>
      </div><p className="hint">資料時間：{new Date(report.as_of_utc).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）</p></>}
    </section>}
    {message && <p role="status">{message}</p>}
    <section className="card" aria-labelledby="products-title"><h2 id="products-title">品項</h2><div className="item-grid">{products.map((product) => <article key={product.id}><strong>{product.name}</strong><span>{product.unit} · 最低 {product.min_qty} · 目標 {product.target_qty}</span>{!product.is_active && <span className="inactive">已停用</span>}</article>)}</div></section>
    <section className="card" aria-labelledby="locations-title"><h2 id="locations-title">儲位</h2><div className="item-grid">{locations.map((location) => <article key={location.id}><strong>{location.code}</strong><span>{location.warehouse_name}</span>{!location.is_active && <span className="inactive">已停用</span>}</article>)}</div></section>
  </main>;
}
