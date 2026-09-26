import type { Product } from '../types/masterData';

// iOS WebKit includes native option text when calculating the page width.
export function productOptionLabel(product: Product): string {
  const name = Array.from(product.name);
  const shortName = name.length > 8 ? `${name.slice(0, 8).join('')}…` : product.name;
  return `${shortName}／#${product.id}${product.is_active ? '' : '／停用'}`;
}
