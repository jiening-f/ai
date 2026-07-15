const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const edgePath = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  const svg5 = fs.readFileSync(path.join(__dirname, 'icon-v5.svg'), 'utf8');

  const html = '<!DOCTYPE html><html><head><style>' +
    '*{margin:0;padding:0;box-sizing:border-box;}' +
    'body{background:#e8dcc8;display:flex;flex-direction:column;align-items:center;padding:40px;gap:30px;}' +
    '.header{text-align:center;margin-bottom:10px;}' +
    '.header h1{color:#6a5a45;font-family:Arial;font-size:24px;}' +
    '.header p{color:#b8a890;font-family:Arial;font-size:13px;margin-top:6px;}' +
    '.icon512{width:512px;height:512px;border-radius:96px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.12);display:inline-block;}' +
    '.icon128{width:128px;height:128px;border-radius:24px;overflow:hidden;box-shadow:0 3px 12px rgba(0,0,0,0.1);display:inline-block;}' +
    '.row{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;}' +
    '.card{text-align:center;}' +
    '.card p{color:#8a7a60;font-family:Arial;font-size:12px;margin-top:6px;}' +
    '</style></head><body>' +
    '<div class="header"><h1>游戏全能脚本 — v5</h1><p>浓密花朵 · 极浅暖色背景 · 15°倾斜 · 居中</p></div>' +
    '<div class="icon512">' + svg5 + '</div>' +
    '<div class="row">' +
      '<div class="card"><div class="icon128">' + svg5 + '</div><p>128×128</p></div>' +
      '<div class="card"><div style="width:64px;height:64px;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);display:inline-block;">' + svg5 + '</div><p>64×64</p></div>' +
      '<div class="card"><div style="width:48px;height:48px;border-radius:9px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.08);display:inline-block;">' + svg5 + '</div><p>48×48</p></div>' +
    '</div>' +
    '</body></html>';

  fs.writeFileSync(path.join(__dirname, 'icon-v5-preview.html'), html);
  const htmlPath = path.resolve(__dirname, 'icon-v5-preview.html').replace(/\\/g, '/');

  const browser = await puppeteer.launch({ executablePath: edgePath, headless: true, args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({width: 700, height: 900});
  await page.goto('file:///' + htmlPath, {waitUntil: 'networkidle0'});
  await page.screenshot({path: path.join(__dirname, 'icon-v5-preview-screenshot.png'), fullPage: true});
  await browser.close();
  const s = fs.statSync(path.join(__dirname, 'icon-v5-preview-screenshot.png'));
  console.log('Preview screenshot saved: ' + s.size + ' bytes');
})();
