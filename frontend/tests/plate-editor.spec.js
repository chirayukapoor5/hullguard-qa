import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const address = '/#editor';

test('live 8 mm edit agrees with independently generated Python reference and downloads model', async ({ page }) => {
  await page.goto(address);
  await expect(page.getByText('Live calculation', { exact: true })).toBeVisible();
  const input = page.getByLabel('Proposed thickness (mm)');
  await input.fill('8');
  await page.getByRole('button', { name: 'Calculate' }).click();
  await expect(page.getByText('+31.40 kg', { exact: true })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: 'Plate mass (kg)' })).toContainText('125.60');
  await expect(page.getByRole('row').filter({ hasText: 'Assembly mass (kg)' })).toContainText('250.3052256');
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download revised model' }).click();
  const downloaded = JSON.parse(await readFile(await (await pending).path(), 'utf8'));
  const reference = await (await page.request.get('/data/revisions/thickness_changed/model.json')).json();
  expect(downloaded).toEqual(reference);
  await page.screenshot({ path: resolve('../reports/plate-editor.png') });
});

test('valid nonfixture edits and no-op are calculated from the loaded model', async ({ page }) => {
  await page.goto(address);
  const input = page.getByLabel('Proposed thickness (mm)');
  await input.fill('6.125');
  await input.press('Enter');
  await expect(page.getByText('+1.9625 kg')).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: 'Bottom Z (mm)' })).toContainText('-6.125');
  await input.fill('0.001');
  await input.press('Enter');
  await expect(page.getByText('−94.1843 kg')).toBeVisible();
  await input.fill('6');
  await input.press('Enter');
  await expect(page.getByText('0.00 kg', { exact: true })).toBeVisible();
});

test('invalid input clears previous results and reports actionable guidance', async ({ page }) => {
  await page.goto(address);
  const input = page.getByLabel('Proposed thickness (mm)');
  await input.fill('8');
  await input.press('Enter');
  await expect(page.getByRole('button', { name: 'Download revised model' })).toBeEnabled();
  for (const [value, message] of [
    ['0', /0.001 to 1,000,000/],
    ['-1', /positive decimal/],
    ['1e2', /positive decimal/],
    ['7.0001', /three decimal places/],
    ['1000001', /0.001 to 1,000,000/],
  ]) {
    await input.fill(value);
    await input.press('Enter');
    await expect(page.getByRole('alert')).toHaveText(message);
    await expect(input).toBeFocused();
    await expect(input).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByRole('button', { name: 'Download revised model' })).toBeDisabled();
    await expect(page.getByText('+31.40 kg')).toHaveCount(0);
  }
  await page.screenshot({ path: resolve('../reports/plate-editor-invalid.png') });
  await input.fill('7');
  await input.press('Enter');
  await expect(page.getByText('+15.70 kg')).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
