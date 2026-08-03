// 暗色气泡复现驱动 — 跑完即删。
const fs = require('fs');
const { chromium } = require('@playwright/test');

(async () => {
  const css = fs.readFileSync('/tmp/dark-bubble-harness.css', 'utf8');
  const js = fs.readFileSync('/tmp/dark-bubble-harness.js', 'utf8');
  const browser = await chromium.launch();

  for (const scenario of ['system-dark-no-attr', 'attr-dark', 'light']) {
    const page = await browser.newPage();
    if (scenario === 'system-dark-no-attr') {
      await page.emulateMedia({ colorScheme: 'dark' });
    }
    const html = `<!doctype html><html${scenario === 'attr-dark' ? ' data-theme="dark"' : ''}${scenario === 'light' ? ' data-theme="light"' : ''}><head><meta charset="utf-8"><style>${css}</style></head><body><div id="root"></div><script>${js.replace(/<\/script/g, '<\\/script')}<\/script></body></html>`;
    await page.setContent(html, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    const sample = await page.evaluate(() => {
      const bubble = document.querySelector('#root > div > div');
      if (!bubble) return null;
      const rect = bubble.getBoundingClientRect();
      const canvas = document.createElement('canvas');
      return { bg: getComputedStyle(bubble).backgroundColor, rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height }, canvas };
    });
    console.log(scenario, 'bubble computed bg:', sample && sample.bg);
    await page.screenshot({ path: `/tmp/dark-bubble-${scenario}.png` });
    await page.close();
  }
  await browser.close();
})().catch((err) => { console.error(err); process.exit(1); });
