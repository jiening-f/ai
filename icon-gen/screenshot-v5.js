const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const edgePath = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  const htmlPath = path.resolve(__dirname, 'icon-v5-view.html').replace(/\\/g, '/');
  const browser = await puppeteer.launch({ executablePath: edgePath, headless: true, args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({width: 900, height: 600});
  await page.goto('file:///' + htmlPath, {waitUntil: 'networkidle0'});
  await page.screenshot({path: path.join(__dirname, 'icon-v5-screenshot.png'), fullPage: true});
  await browser.close();
  const s = fs.statSync(path.join(__dirname, 'icon-v5-screenshot.png'));
  console.log('Screenshot saved: ' + s.size + ' bytes');
})();
