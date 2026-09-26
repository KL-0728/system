import { useEffect, useState } from 'react';
import BackToTop from '../components/BackToTop';
import QuickJump from '../components/QuickJump';
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
    <p className="hint">數量依各品項的單位顯示，不把籠、箱或公斤相加。「距離目標還差」＝目標量減目前庫存，不足時顯示差額，已達標時為 0；這只是人工設定的參考目標，不是自動採購量。</p>
    <button type="button" className="secondary" disabled={loading} onClick={() => void refresh()}>更新報表</button>
    {loading && <p role="status">正在讀取最新報表…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {report && <>
      <p className="hint">資料時間：{timeText(report.as_of_utc)}（臺灣時間）；近 30 日依伺服器 UTC 時間計算。</p>
      <QuickJump items={[{ id: 'report-summary', label: '統計' }, { id: 'report-low-stock', label: '低庫存' }, { id: 'report-products', label: '品項與出庫' }, { id: 'report-shortages', label: '缺貨需求' }, { id: 'report-aged-lots', label: '庫齡' }, { id: 'report-adjustments', label: '盤差與報廢' }]} />
      <section id="report-summary" className="card jump-target" aria-labelledby="report-summary-title"><h2 id="report-summary-title">首頁統計</h2>
        <div className="report-summary">
          <article><strong>{report.summary.in_stock_product_count}</strong><span>目前有庫存品項</span></article>
          <article><strong>{report.summary.low_stock_product_count}</strong><span>低於最低量品項</span></article>
          <article><strong>{report.summary.pending_adjustment_count}</strong><span>待審申請</span></article>
          <article><strong>{report.summary.shortage_demand_count}</strong><span>缺貨詢問筆數</span></article>
          <article><strong>{report.summary.active_product_count}</strong><span>啟用品項</span></article>
        </div>
      </section>
      <section id="report-low-stock" className="card jump-target" aria-labelledby="low-stock-title"><h2 id="low-stock-title">低庫存與目標量差距</h2>
        {lowProducts.length === 0 && <p>目前沒有低於最低量的品項。</p>}
        <div className="report-list">{lowProducts.map((product) => <article key={product.product_id}>
          <strong>{product.product_name}</strong>
          <span>目前 {product.current_qty} {product.unit}／最低 {product.min_qty} {product.unit}／目標 {product.target_qty} {product.unit}</span>
          <span>距離目標量：{product.replenishment_gap} {product.unit}</span>
        </article>)}</div>
      </section>
      <section id="report-products" className="card jump-target" aria-labelledby="all-products-title"><h2 id="all-products-title">啟用品項與近 30 日出庫</h2>
        {report.products.length === 0 && <p>目前沒有啟用品項。</p>}
        <div className="report-list">{report.products.map((product) => <article key={product.product_id}>
          <strong>{product.product_name}{product.is_low ? '（低庫存）' : ''}</strong>
          <span>目前 {product.current_qty} {product.unit}；近 30 日實際出庫 {product.outbound_30d} {product.unit}</span>
          <span>累計缺貨詢問 {product.shortage_demand_qty} {product.unit}（未成交，不算出庫）</span>
          <span>最低 {product.min_qty} {product.unit}；目標 {product.target_qty} {product.unit}；距離目標還差 {product.replenishment_gap} {product.unit}</span>
        </article>)}</div>
      </section>
      <section id="report-shortages" className="card jump-target" aria-labelledby="shortage-report-title"><h2 id="shortage-report-title">缺貨需求紀錄</h2>
        <p className="hint">最近 100 筆詢問；只代表想買但未成交的需求，不扣庫存，也不計入實際出庫。</p>
        {report.shortage_demands.length === 0 && <p>目前沒有缺貨需求紀錄。</p>}
        <div className="report-list">{report.shortage_demands.map((item) => <article key={item.id}>
          <strong>#{item.id} {item.product_name}：詢問 {item.qty} {item.unit}</strong>
          <span>{timeText(item.created_at)}（臺灣時間）／{item.actor_name}</span>
          {item.note && <span>備註：{item.note}</span>}
        </article>)}</div>
      </section>
      <section id="report-aged-lots" className="card jump-target" aria-labelledby="aged-lots-title"><h2 id="aged-lots-title">現有批次庫齡</h2>
        {report.aged_lots.length === 0 && <p>目前沒有正餘量批次。</p>}
        <div className="report-list">{report.aged_lots.map((lot) => <article key={lot.lot_id}>
          <strong>{lot.product_name}／{lot.lot_code}</strong>
          <span>入庫日 {lot.received_date}；庫齡 {lot.age_days} 天；現有 {lot.total_qty} {lot.unit}</span>
        </article>)}</div>
      </section>
      <section id="report-adjustments" className="card jump-target" aria-labelledby="adjustment-report-title"><h2 id="adjustment-report-title">盤差與報廢</h2>
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
    <BackToTop />
  </main>;
}
