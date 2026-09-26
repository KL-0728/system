import { useEffect, useState } from 'react';
import { getDecisionReport, type DecisionReport } from '../api/reports';

const timeText = (value: string) => new Date(value).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });
const kindLabel = { COUNT_GAIN: '盤盈', COUNT_LOSS: '盤虧', SCRAP: '報廢' };

export default function ReportsPage() {
  const [report, setReport] = useState<DecisionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true);
    try { setReport(await getDecisionReport()); setError(''); }
    catch { setError('無法讀取報表，請確認連線後再更新。'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, []);
  const lowProducts = report?.products.filter((product) => product.is_low) ?? [];
  const changedProducts = report?.products.filter((product) => product.count_gain_qty || product.count_loss_qty || product.scrap_qty) ?? [];

  return <main className="app-shell reports-page">
    <p className="eyebrow">管理者決策報表</p><h1>庫存與損耗</h1>
    <p className="hint">數量依各品項的單位顯示，不把籠、箱或公斤相加。最低量與目標量為管理者設定的參考門檻，補貨缺口不是自動採購建議。</p>
    <button type="button" className="secondary" disabled={loading} onClick={() => void refresh()}>更新報表</button>
    {loading && <p role="status">正在讀取最新報表…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {report && <>
      <p className="hint">資料時間：{timeText(report.as_of_utc)}（臺灣時間）；近 30 日依伺服器 UTC 時間計算。</p>
      <section className="card" aria-labelledby="report-summary-title"><h2 id="report-summary-title">首頁統計</h2>
        <div className="report-summary">
          <article><strong>{report.summary.in_stock_product_count}</strong><span>目前有庫存品項</span></article>
          <article><strong>{report.summary.low_stock_product_count}</strong><span>低於最低量品項</span></article>
          <article><strong>{report.summary.pending_adjustment_count}</strong><span>待審申請</span></article>
          <article><strong>{report.summary.active_product_count}</strong><span>啟用品項</span></article>
        </div>
      </section>
      <section className="card" aria-labelledby="low-stock-title"><h2 id="low-stock-title">低庫存與參考補貨缺口</h2>
        {lowProducts.length === 0 && <p>目前沒有低於最低量的品項。</p>}
        <div className="report-list">{lowProducts.map((product) => <article key={product.product_id}>
          <strong>{product.product_name}</strong>
          <span>目前 {product.current_qty} {product.unit}／最低 {product.min_qty} {product.unit}／目標 {product.target_qty} {product.unit}</span>
          <span>距離目標量：{product.replenishment_gap} {product.unit}</span>
        </article>)}</div>
      </section>
      <section className="card" aria-labelledby="all-products-title"><h2 id="all-products-title">啟用品項與近 30 日出庫</h2>
        {report.products.length === 0 && <p>目前沒有啟用品項。</p>}
        <div className="report-list">{report.products.map((product) => <article key={product.product_id}>
          <strong>{product.product_name}{product.is_low ? '（低庫存）' : ''}</strong>
          <span>目前 {product.current_qty} {product.unit}；近 30 日出庫 {product.outbound_30d} {product.unit}</span>
          <span>最低 {product.min_qty} {product.unit}；目標 {product.target_qty} {product.unit}；參考缺口 {product.replenishment_gap} {product.unit}</span>
        </article>)}</div>
      </section>
      <section className="card" aria-labelledby="aged-lots-title"><h2 id="aged-lots-title">現有批次庫齡</h2>
        {report.aged_lots.length === 0 && <p>目前沒有正餘量批次。</p>}
        <div className="report-list">{report.aged_lots.map((lot) => <article key={lot.lot_id}>
          <strong>{lot.product_name}／{lot.lot_code}</strong>
          <span>入庫日 {lot.received_date}；庫齡 {lot.age_days} 天；現有 {lot.total_qty} {lot.unit}</span>
        </article>)}</div>
      </section>
      <section className="card" aria-labelledby="adjustment-report-title"><h2 id="adjustment-report-title">盤差與報廢</h2>
        <p className="hint">下列數量是各品項歷來已核准的異動；盤盈、盤虧和報廢分開列示。</p>
        {changedProducts.length === 0 && <p>目前沒有已核准的盤差或報廢異動。</p>}
        <div className="report-list">{changedProducts.map((product) => <article key={product.product_id}>
          <strong>{product.product_name}</strong>
          <span>盤盈 {product.count_gain_qty} {product.unit}；盤虧 {product.count_loss_qty} {product.unit}；報廢 {product.scrap_qty} {product.unit}</span>
        </article>)}</div>
        {report.adjustments.length > 0 && <><h3>已核准異動明細</h3><div className="report-list">{report.adjustments.map((item) => <article key={item.movement_id}>
          <strong>#{item.movement_id} {kindLabel[item.kind]} {item.qty} {item.unit}</strong>
          <span>{item.product_name}／{item.lot_code}／{item.location_code}；申請 #{item.adjustment_request_id}</span>
          <span>{timeText(item.created_at)}（臺灣時間）／{item.actor_name}</span>
          <span>原因：{item.reason}</span>
        </article>)}</div></>}
      </section>
    </>}
  </main>;
}
