import { useEffect, useState } from 'react';
import { getHealth } from '../api/health';

export default function HomePage() {
  const [status, setStatus] = useState('正在確認後端連線…');
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    let active = true;
    getHealth(controller.signal)
      .then(() => { if (active) setStatus('後端服務正常'); })
      .catch(() => {
        if (active) setStatus('無法連線後端，請確認服務已啟動後重新整理。');
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, []);
  return (
    <main>
      <p className="phase">第一階段 · 基礎骨架</p>
      <h1>竹南冷凍倉儲<br />庫存管理系統</h1>
      <p>歡迎使用。此頁為暫時首頁，供團隊確認系統啟動與連線。</p>
      <section aria-labelledby="service-title">
        <h2 id="service-title">服務狀態</h2>
        <p role="status">{status}</p>
      </section>
      <p className="note">登入、品項與儲位管理，以及入庫、出庫、移位、盤點和報表功能尚未開放。</p>
    </main>
  );
}
