import { useEffect, useState } from 'react';
import { getLocations, getProducts } from '../api/masterData';
import type { CurrentUser } from '../types/auth';
import type { Location, Product } from '../types/masterData';

export default function HomePage({ user }: { user: CurrentUser }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [message, setMessage] = useState('正在讀取基本資料…');
  useEffect(() => {
    let active = true;
    Promise.all([getProducts(), getLocations()]).then(([productRows, locationRows]) => {
      if (active) { setProducts(productRows); setLocations(locationRows); setMessage(''); }
    }).catch((error) => { if (active) setMessage(error instanceof Error ? error.message : '讀取失敗'); });
    return () => { active = false; };
  }, []);
  return <main className="app-shell">
    <p className="eyebrow">首頁</p><h1>你好，{user.display_name}</h1><p>{user.role === 'ADMIN' ? '管理者' : '倉管人員'}工作區</p>
    {user.role === 'ADMIN' && <section className="card stats-placeholder" aria-label="管理統計預留區"><h2>管理統計</h2><p>D3 合併後顯示有庫存品項、低庫存與待審申請。</p></section>}
    {message && <p role="status">{message}</p>}
    <section className="card" aria-labelledby="products-title"><h2 id="products-title">品項</h2><div className="item-grid">{products.map((product) => <article key={product.id}><strong>{product.name}</strong><span>{product.unit} · 最低 {product.min_qty} · 目標 {product.target_qty}</span>{!product.is_active && <span className="inactive">已停用</span>}</article>)}</div></section>
    <section className="card" aria-labelledby="locations-title"><h2 id="locations-title">儲位</h2><div className="item-grid">{locations.map((location) => <article key={location.id}><strong>{location.code}</strong><span>{location.warehouse_name}</span>{!location.is_active && <span className="inactive">已停用</span>}</article>)}</div></section>
  </main>;
}
