// Optional real-browser smoke test. Start the demo server on port 8000 first.
// Requires the playwright Node package and a Chromium installation.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
    args: ['--no-sandbox'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('http://127.0.0.1:8000');
    await page.getByText('● MODALITÀ DEMO', { exact: false }).waitFor();
    assert(await page.locator('#topic').isDisabled());
    const initial = Number(await page.locator('#total').textContent());
    await page.getByRole('button', { name: /Genera curiosità/ }).click();
    await page.getByText('3 bozze create.', { exact: false }).waitFor();
    assert.equal(Number(await page.locator('#total').textContent()), initial + 3);
    await page.getByRole('button', { name: /I polpi hanno davvero/ }).first().click();
    assert.match(await page.locator('#detail h3').textContent(), /polpi/);
    assert.equal(await page.locator('#detail .slide').count(), 5);
    assert.equal(await page.locator('#detail .sources a').count(), 1);
    await page.getByRole('button', { name: /Carosello PNG/ }).click();
    await page.locator('#detail .download').waitFor();
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#detail .download').click();
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), 'carosello.zip');
    assert.equal(await download.failure(), null);
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Horizontal overflow at ${width}px`);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `/tmp/ma-davvero-${width}.png`, fullPage: true });
    }
    await page.reload();
    await page.waitForFunction((expected) => Number(document.querySelector('#total').textContent) === expected, initial + 3);
    assert.deepEqual(errors, []);
    console.log('PASS: generation, selection, 5 slides, sources, ZIP download, persistence, 320/390/1440px layout; no JS errors.');
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
