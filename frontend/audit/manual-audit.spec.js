
import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const audit = resolve('../build/manual-audit');
const finding = (page, code) => page.getByRole('rowheader', { name: code, exact: true });

test.afterEach(async ({ page, browser }, testInfo) => {
  await testInfo.attach('environment', {
    body: JSON.stringify({ chromium: browser.version(), viewport: page.viewportSize() }),
    contentType: 'application/json',
  });
  await page.screenshot({ path: resolve(audit, 'browser', testInfo.title.slice(0, 3) + '.png') });
});

async function ready(page) {
  await page.goto('/');
  await expect(page.getByText('8 mesh objects', { exact: true })).toBeVisible();
  return page.locator('canvas');
}

async function imageDifference(page, first, second) {
  return page.evaluate(async ([a, b]) => {
    async function pixels(source) {
      const image = await createImageBitmap(await (await fetch('data:image/png;base64,' + source)).blob());
      const canvas = new OffscreenCanvas(image.width, image.height);
      const context = canvas.getContext('2d');
      context.drawImage(image, 0, 0);
      return context.getImageData(0, 0, image.width, image.height).data;
    }
    const [left, right] = await Promise.all([pixels(a), pixels(b)]);
    if (left.length !== right.length) return 1;
    let changed = 0;
    for (let i = 0; i < left.length; i += 4) {
      if ([0, 1, 2].some(offset => Math.abs(left[i + offset] - right[i + offset]) > 16)) changed++;
    }
    return changed / (left.length / 4);
  }, [first.toString('base64'), second.toString('base64')]);
}

async function readLink(page, name) {
  const href = await page.getByRole('link', { name, exact: true }).getAttribute('href');
  const response = await page.request.get(new URL(href, page.url()).toString());
  expect(response.ok()).toBe(true);
  return response;
}

test('M11 faulty drawing visibly retains the P-01 6 mm annotation', async ({ page }) => {
  await page.goto('/data/faults/stale_drawing/drawing.svg');
  await expect(page.locator('text[data-component="P-01"]')).toContainText('t=6 mm');
});

test('M15 pointer rotation, repeated zoom, reset, and keyboard camera controls', async ({ page }, testInfo) => {
  const canvas = await ready(page);
  const bounds = await canvas.boundingBox();
  const initial = await canvas.screenshot();
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width / 2 + 85, bounds.y + bounds.height / 2 - 30, { steps: 6 });
  await page.mouse.up();
  expect((await canvas.screenshot()).equals(initial)).toBe(false);
  const rotated = await canvas.screenshot();
  for (let i = 0; i < 2; i++) await page.getByRole('button', { name: 'Zoom in' }).click();
  expect((await canvas.screenshot()).equals(rotated)).toBe(false);
  await page.getByRole('button', { name: 'Reset view' }).click();
  await page.evaluate(() => document.activeElement.blur());
  const buttonReset = await imageDifference(page, initial, await canvas.screenshot());
  expect(buttonReset).toBeLessThan(.01);
  await canvas.press('ArrowRight');
  const keyboard = await canvas.screenshot();
  await canvas.press('+');
  expect((await canvas.screenshot()).equals(keyboard)).toBe(false);
  await canvas.press('-');
  await canvas.press('Home');
  await page.evaluate(() => document.activeElement.blur());
  const keyboardReset = await imageDifference(page, initial, await canvas.screenshot());
  expect(keyboardReset).toBeLessThan(.01);
  await testInfo.attach('camera comparison', {
    body: JSON.stringify({ buttonReset, keyboardReset, maxDifference: .01, channelThreshold: 16 }),
    contentType: 'application/json',
  });
  await expect(page.getByText('8 mesh objects', { exact: true })).toBeVisible();
});

test('M16 inspector and table select matching components and canvas picking updates both', async ({ page }) => {
  const canvas = await ready(page);
  const selector = page.getByLabel('Component', { exact: true });
  await selector.selectOption('S-03');
  await expect(page.locator('#part-detail')).toContainText('892 × 8 × 68 mm');
  await expect(page.locator('tr.selected')).toHaveAttribute('data-row', 'S-03');
  await page.getByRole('button', { name: 'B-01', exact: true }).click();
  await expect(selector).toHaveValue('B-01');
  const before = await canvas.screenshot();
  const bounds = await canvas.boundingBox();
  await canvas.click({ position: { x: bounds.width * .62, y: bounds.height * .62 } });
  await expect(selector).not.toHaveValue('B-01');
  const picked = await selector.inputValue();
  await expect(page.locator('tr.selected')).toHaveAttribute('data-row', picked);
  await expect(page.locator('#part-detail')).toContainText(picked);
  expect((await canvas.screenshot()).equals(before)).toBe(false);
});

test('M17 stiffener layout identifies add, remove, and Y-axis deltas', async ({ page }) => {
  await page.goto('/#revisions');
  await page.getByLabel('Compare to baseline').selectOption('stiffener_changed');
  for (const [id, outcome] of [['S-01', 'Modified'], ['S-04', 'Removed'], ['S-05', 'Added']]) {
    await expect(page.getByRole('row').filter({ hasText: id })).toContainText(outcome);
  }
  const comparison = await (await readLink(page, 'Open position and dimension deltas')).json();
  expect(comparison.modified[0].delta_position_mm).toEqual([0, 30, 0]);
  expect(comparison.modified[0].delta_dimensions_mm).toEqual([0, 2, 0]);
});

test('M18 QA dashboard counts and stale BOM reproduction are visible', async ({ page }) => {
  await page.goto('/#checks');
  for (const text of ['3 / 3', '6 / 6', 'Precomputed']) {
    await expect(page.getByText(text, { exact: true })).toBeVisible();
  }
  await page.getByRole('button', { name: 'Reproduce Stale BOM' }).click();
  await expect(finding(page, 'STALE_REVISION').first()).toBeVisible();
  await expect(page.locator('pre')).toContainText('python -m hullguard validate');
});

test('M19 wrong conversion and duplicate IDs show detectors and serve actual evidence', async ({ page }) => {
  await page.goto('/#faults');
  const chooser = page.getByLabel('Synthetic scenario');
  await chooser.selectOption('wrong_units');
  await expect(finding(page, 'MASS')).toBeVisible();
  await expect(page.locator('pre')).toContainText('hullguard validate');
  const csv = await (await readLink(page, 'Open faulty artifact')).text();
  expect(csv).toContain('B-01');
  expect((await (await readLink(page, 'Validation (JSON)')).json()).status).toBe('FAIL');
  await chooser.selectOption('duplicate_id');
  await expect(finding(page, 'INPUT_DUPLICATE_ID')).toBeVisible();
  await expect(page.getByText(/using precomputed validator results/)).toBeVisible();
  await expect(page.locator('pre')).toContainText('hullguard check');
  const model = await (await readLink(page, 'Open faulty artifact')).json();
  expect(model.components.filter(p => p.id === 'S-03')).toHaveLength(2);
  expect((await (await readLink(page, 'Validation (JSON)')).json()).findings[0].code).toBe('INPUT_DUPLICATE_ID');
});

test('M20 revised HTML report serves comparison, revised drawing, and BOM', async ({ page }) => {
  await page.goto('/#report');
  await page.getByLabel('Report revision').selectOption('thickness_changed');
  await expect(page.locator('.report-grid code, .report-grid .mono').first()).toContainText('c4da7d35208e');
  await page.getByRole('link', { name: 'Engineering report (HTML)', exact: true }).click();
  await expect(page.getByText('Assembly mass delta +31.400000 kg.')).toBeVisible();
  const comparison = await (await readLink(page, 'Revision comparison and affected artifacts')).json();
  expect(comparison.delta_mass_kg).toBeCloseTo(31.4, 9);
  const csv = await (await readLink(page, 'Bill of materials')).text();
  expect(csv.split('\n').find(line => line.includes(',P-01,'))).toContain(',125.6');
  const drawing = await (await readLink(page, 'Plan drawing')).text();
  expect(drawing).toContain('P-01    2000 × 1000 × 8 mm    t=8 mm');
});

test('M21 mobile header, independent scroll regions, and keyboard focus', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await expect(page.getByText('218.905 kg')).toBeVisible();
  const nav = page.locator('.navigation-inner');
  expect(await nav.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
  await nav.evaluate(el => { el.scrollLeft = el.scrollWidth; });
  expect(await nav.evaluate(el => el.scrollLeft)).toBeGreaterThan(0);
  await page.getByRole('link', { name: 'Engineering report', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Engineering report', exact: true })).toBeVisible();
  const table = page.locator('.table-scroll').first();
  expect(await table.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
  await table.evaluate(el => { el.scrollLeft = el.scrollWidth; });
  expect(await table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0);
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement.matches(':focus-visible') &&
    getComputedStyle(document.activeElement).outlineStyle !== 'none')).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
});

test('M22 disabled WebGL retains accessible selector and real OBJ download', async ({ page }) => {
  await page.addInitScript(() => {
    const get = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...args) {
      return type.startsWith('webgl') ? null : get.call(this, type, ...args);
    };
  });
  await page.goto('/');
  await expect(page.getByText(/3D preview unavailable/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Zoom in' })).toBeDisabled();
  await page.getByLabel('Component', { exact: true }).selectOption('S-01');
  await expect(page.locator('#part-detail')).toContainText('1,100 × 8 × 68 mm');
  const obj = await (await readLink(page, 'Open OBJ')).text();
  expect(obj.match(/^o /gm)).toHaveLength(8);
});

test('M23 SVG renders edited P-01 text while metadata retains 6 mm', async ({ page }) => {
  const svg = await readFile(resolve(audit, 'shell/M23/drawing.svg'), 'utf8');
  await page.setContent(svg);
  const label = page.locator('text[data-component="P-01"]');
  await expect(label).toContainText('t=8 mm');
  await expect(label).toHaveAttribute('data-thickness-mm', '6.0');
  await expect(label).toBeVisible();
});
