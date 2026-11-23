import { expect, test } from '@playwright/test';
import { resolve } from 'node:path';

const reports = resolve('../reports');

async function ready(page) {
  await expect(page.getByRole('status').filter({ hasText: '8 mesh objects' })).toBeVisible();
  await expect(page.locator('canvas')).toBeVisible();
}

test('generated OBJ renders and pointer/keyboard selection hydrates the manifest', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const objRequest = page.waitForResponse(response => response.url().endsWith('/baseline/model.obj'));
  await page.goto('/');
  expect((await objRequest).ok()).toBe(true);
  await ready(page);
  await expect(page.getByRole('heading', { name: 'Structure explorer' })).toBeVisible();
  await expect(page.getByText('218.905 kg')).toBeVisible();
  await expect(page.locator('#part-detail')).toContainText('94.20 kg');
  const canvas = page.locator('canvas');
  await page.getByLabel('Component', { exact: true }).selectOption('S-03');
  await expect(page.locator('#part-detail')).toContainText('892 × 8 × 68 mm');
  await page.getByRole('button', { name: 'P-02', exact: true }).click();
  await expect(page.getByLabel('Component', { exact: true })).toHaveValue('P-02');
  await page.getByRole('button', { name: 'Reset view' }).click();
  const bounds = await canvas.boundingBox();
  await canvas.click({ position: { x: bounds.width / 2, y: bounds.height / 2 } });
  await expect(page.getByLabel('Component', { exact: true })).not.toHaveValue('P-02');
  const picked = await page.getByLabel('Component', { exact: true }).inputValue();
  await expect(page.locator('#part-detail')).toContainText(picked);
  await page.getByLabel('Component', { exact: true }).selectOption('P-01');
  await canvas.focus();
  const before = await canvas.screenshot();
  await canvas.press('ArrowRight');
  await page.getByRole('button', { name: 'Zoom in' }).click();
  expect((await canvas.screenshot()).equals(before)).toBe(false);
  await page.getByRole('button', { name: 'Reset view' }).click();
  await page.mouse.move(1, 1);
  await page.evaluate(() => document.activeElement?.blur());
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: resolve(reports, 'structure-explorer.png') });
  expect(errors).toEqual([]);
});

test('revision view renders thickness, mass, and changed component identities', async ({ page }) => {
  await page.goto('/#revisions');
  await ready(page);
  await expect(page.getByText('+31.40 kg').first()).toBeVisible();
  const bottom = page.getByRole('row').filter({ hasText: 'P-01' });
  await expect(bottom).toContainText('6 → 8');
  await expect(bottom).toContainText('94.20 → 125.60');
  await page.getByLabel('Compare to baseline').selectOption('stiffener_changed');
  await ready(page);
  await expect(page.getByRole('row').filter({ hasText: 'S-04' })).toContainText('Removed');
  await expect(page.getByRole('row').filter({ hasText: 'S-05' })).toContainText('Added');
  const evidence = await page.getByRole('link', { name: 'Open position and dimension deltas' }).getAttribute('href');
  const result = await (await page.request.get(evidence)).json();
  expect(result.modified[0].delta_position_mm).toEqual([0, 30, 0]);
});

test('dashboard leads to repeatable faults and serves the exact evidence', async ({ page }) => {
  await page.goto('/#checks');
  await expect(page.getByText('Precomputed', { exact: true })).toBeVisible();
  await expect(page.getByRole('row')).toHaveCount(10);
  await page.getByRole('button', { name: 'Reproduce Stale BOM' }).click();
  await expect(page.getByRole('heading', { name: 'Fault injection' })).toBeVisible();
  await expect(page.locator('pre')).toContainText('python -m hullguard validate');
  await expect(page.getByRole('rowheader', { name: 'MASS', exact: true })).toBeVisible();
  await page.getByLabel('Synthetic scenario').selectOption('stale_drawing');
  await expect(page.getByRole('rowheader', { name: 'DRAWING_THICKNESS', exact: true })).toBeVisible();
  const evidence = await page.getByRole('link', { name: 'Validation (JSON)' }).getAttribute('href');
  const result = await (await page.request.get(evidence)).json();
  expect(result.status).toBe('FAIL');
  expect(result.findings.some(f => f.artifact === 'drawing.svg')).toBe(true);
  await page.getByLabel('Synthetic scenario').selectOption('duplicate_id');
  await expect(page.locator('pre')).toContainText('python -m hullguard check');
  await expect(page.getByRole('rowheader', { name: 'INPUT_DUPLICATE_ID' })).toBeVisible();
  await page.getByLabel('Synthetic scenario').selectOption('stale_bom');
  await page.evaluate(() => document.activeElement?.blur());
  await page.screenshot({ path: resolve(reports, 'fault-injection.png') });
});

test('engineering report and every revision export are served', async ({ page }) => {
  await page.goto('/#report');
  await page.getByLabel('Report revision').selectOption('thickness_changed');
  await expect(page.getByText('1 modified, 0 added and 0 removed since baseline.')).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'XYZ dimensions (mm)' })).toBeVisible();
  for (const link of await page.locator('.link-list a').all()) {
    const href = await link.getAttribute('href');
    expect((await page.request.get(href)).ok(), href).toBe(true);
  }
  await page.getByRole('link', { name: 'Engineering report (HTML)' }).click();
  await expect(page.getByRole('heading', { name: 'Change impact' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Plan drawing' })).toBeVisible();
});

test('compact viewport retains navigation and component inspection', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await ready(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await page.screenshot({ path: resolve(reports, 'structure-mobile.png') });
  await page.getByLabel('Component', { exact: true }).selectOption('B-01');
  await expect(page.locator('#part-detail')).toContainText('Transverse bulkhead');
  await page.getByRole('link', { name: 'Engineering report', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Engineering report' })).toBeVisible();
});

test('unavailable WebGL leaves readable geometry evidence', async ({ page }) => {
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (name, ...args) {
      return name.startsWith('webgl') ? null : getContext.call(this, name, ...args);
    };
  });
  await page.goto('/');
  await expect(page.getByText('3D preview unavailable.', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Zoom in' })).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Open OBJ' })).toBeVisible();
  await page.getByLabel('Component', { exact: true }).selectOption('S-01');
  await expect(page.locator('#part-detail')).toContainText('Longitudinal stiffener');
});
