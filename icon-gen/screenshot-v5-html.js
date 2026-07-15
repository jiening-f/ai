const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const edgePath = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  const htmlPath = path.resolve(__dirname, '../ui-design/page-mockups/app-icon-v5-preview.html').replace(/\\/g, '/');
  const browser = await puppeteer.launch({ executablePath: edgePath, headless: true, args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({width: 1200, height: 2000});
  await page.goto('file:///' + htmlPath, {waitUntil: 'networkidle0'});
  await page.screenshot({path: path.join(__dirname, 'preview-v5-full.png'), fullPage: true});
  await browser.close();
  const s = fs.statSync(path.join(__dirname, 'preview-v5-full.png'));
  console.log('Full preview screenshot saved: ' + s.size + ' bytes');
})();
