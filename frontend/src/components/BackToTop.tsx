import { useEffect, useState } from 'react';
import { smoothScrollTo } from '../utils/smoothScroll';

export default function BackToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const updateVisibility = () => setVisible(window.scrollY > 500);
    updateVisibility();
    window.addEventListener('scroll', updateVisibility, { passive: true });
    return () => window.removeEventListener('scroll', updateVisibility);
  }, []);

  if (!visible) return null;
  return <button type="button" className="back-to-top" aria-label="回到頁面頂部" title="回到頁面頂部"
    onClick={() => smoothScrollTo(document.body)}>↑<span>頂部</span></button>;
}
