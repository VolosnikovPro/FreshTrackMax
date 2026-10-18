import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const requireRuntime = createRequire('C:/Users/aleksey/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const { chromium } = requireRuntime('playwright');

const outputDir = path.resolve('docs/admin-manual-assets');
const today = new Date().toISOString().slice(0, 10);
const user = {
  id: 1, site_id: 1, username: 'glavniy-admin', display_name: 'Анна Петрова',
  role: 'superadmin', is_active: true, max_user_id: 100001,
};
const sites = [
  { id: 1, name: 'Объект N 1', code: 'OBJ-01', description: 'Демонстрационный объект', is_active: true, created_at: `${today}T09:00:00` },
  { id: 2, name: 'Объект N 2', code: 'OBJ-02', description: 'Второй демонстрационный объект', is_active: true, created_at: `${today}T09:00:00` },
];
const products = [
  { id: 11, site_id: 1, name: 'Молоко пастеризованное', sku: 'MLK-001', unit: 'л', category: 'Молочная продукция', description: null, is_active: true },
  { id: 12, site_id: 1, name: 'Крупа гречневая', sku: 'GR-112', unit: 'кг', category: 'Крупы', description: null, is_active: true },
  { id: 13, site_id: 1, name: 'Яблоки свежие', sku: 'APL-015', unit: 'кг', category: 'Фрукты', description: null, is_active: true },
];
const batches = [
  { id: 21, site_id: 1, product_id: 11, product_name: products[0].name, batch_number: 'UPD-1042', upd_number: 'UPD-1042', quantity: 36, unit: 'л', expiry_date: '2026-09-08', received_date: '2026-08-29', days_until_expiry: 8, notes: null, status: 'active', created_at: `${today}T09:00:00`, updated_at: `${today}T09:00:00` },
  { id: 22, site_id: 1, product_id: 12, product_name: products[1].name, batch_number: 'UPD-1043', upd_number: 'UPD-1043', quantity: 18, unit: 'кг', expiry_date: '2026-09-24', received_date: '2026-08-29', days_until_expiry: 24, notes: null, status: 'active', created_at: `${today}T09:00:00`, updated_at: `${today}T09:00:00` },
  { id: 23, site_id: 1, product_id: 13, product_name: products[2].name, batch_number: 'UPD-1044', upd_number: 'UPD-1044', quantity: 12, unit: 'кг', expiry_date: '2026-10-12', received_date: '2026-08-30', days_until_expiry: 42, notes: null, status: 'active', created_at: `${today}T09:00:00`, updated_at: `${today}T09:00:00` },
];

function reply(url) {
  const pathname = url.pathname;
  if (pathname === '/api/admin/me') return user;
  if (pathname === '/api/sites/') return sites;
  if (pathname === '/api/admin/summary') return { total_products: 3, total_batches: 3, expiring_soon_urgent: 1, expiring_soon_planned: 2, total_products_with_cost: 3, today_headcount: 156, today_consumption_entries: 2 };
  if (pathname === '/api/products/') return products;
  if (pathname === '/api/batches/expiring/urgent') return [batches[0]];
  if (pathname === '/api/batches/expiring/planned') return [batches[1], batches[2]];
  if (pathname === '/api/batches/') return batches;
  if (pathname === '/api/costs/financial') return { rows: [{ date: today, invoice_amount_net: 24180, headcount: 156, daily_cost: 155 }], average: 155 };
  if (pathname === '/api/notifications/config') return { urgent_threshold_days: 15, planned_threshold_days: 45, notification_time: '09:00', base_day: 'sunday' };
  if (pathname === '/api/notifications/logs') return [];
  if (pathname === '/api/sheets/import/history') return [{ id: 25, import_type: 'risk_report', status: 'success', created_at: `${today}T09:00:00` }];
  if (pathname === '/api/admin/users') return [user, { id: 2, site_id: 1, username: 'kladovshik-1', display_name: 'Мария Соколова', role: 'storekeeper', is_active: true, max_user_id: 100002 }, { id: 3, site_id: 2, username: 'upp-2', display_name: 'Иван Орлов', role: 'manager', is_active: true, max_user_id: 100003 }];
  return [];
}

await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
});
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
const page = await context.newPage();
await page.route('https://partner-sklad.ru:3000/api/**', async route => {
  const url = new URL(route.request().url());
  await route.fulfill({ contentType: 'application/json', body: JSON.stringify(reply(url)) });
});

await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'domcontentloaded' });
await page.evaluate((savedUser) => {
  localStorage.setItem('ft_user', JSON.stringify(savedUser));
  localStorage.setItem('ft_token', 'demo-token');
  localStorage.setItem('ft_site_id', '1');
}, user);

for (const [slug, route] of [
  ['01-dashboard', '/'], ['02-import', '/import'], ['03-products', '/products'],
  ['04-batches', '/batches'], ['05-notifications', '/notifications'], ['06-admin-users', '/admin'],
]) {
  await page.goto(`http://127.0.0.1:5173${route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(outputDir, `${slug}.png`), fullPage: true });
}

await browser.close();
