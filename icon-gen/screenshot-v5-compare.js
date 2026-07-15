const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const edgePath = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  const svg5 = fs.readFileSync(path.join(__dirname, 'icon-v5.svg'), 'utf8');
  const svg4 = fs.readFileSync(path.join(__dirname, 'icon-v4.svg'), 'utf8');

  const html = '<!DOCTYPE html><html><head><style>' +
    '*{margin:0;padding:0;box-sizing:border-box;}' +
    'body{background:#e8dcc8;display:flex;flex-direction:column;align-items:center;padding:40px;gap:30px;}' +
    '.row{display:flex;gap:30px;flex-wrap:wrap;justify-content:center;}' +
    '.card{text-align:center;}' +
    '.card h3{color:#6a5a45;font-family:Arial;font-size:14px;margin-bottom:10px;}' +
    '.card p{color:#8a7a60;font-family:Arial;font-size:11px;margin-top:6px;}' +
    '.icon256{width:256px;height:256px;border-radius:48px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.12);display:inline-block;}' +
    '.icon128{width:128px;height:128px;border-radius:24px;overflow:hidden;box-shadow:0 3px 12px rgba(0,0,0,0.1);display:inline-block;}' +
    '.icon64{width:64px;height:64px;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);display:inline-block;}' +
    '.icon48{width:48px;height:48px;border-radius:9px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.08);display:inline-block;}' +
    '.header{text-align:center;margin-bottom:10px;}' +
    '.header h1{color:#6a5a45;font-family:Arial;font-size:24px;}' +
    '.header p{color:#b8a890;font-family:Arial;font-size:13px;margin-top:6px;}' +
    '</style></head><body>' +
    '<div class="header"><h1>游戏全能脚本 — v5 设计预览</h1><p>浓密花朵 · 极浅暖色背景 · 15°倾斜 · 居中</p></div>' +
    '<div style="display:flex;gap:50px;align-items:center;">' +
      '<div style="text-align:center;"><h3 style="color:#b8a890;font-family:Arial;font-size:14px;margin-bottom:12px;">v4.1（之前）</h3>' +
        '<div class="icon128">' + svg4.replace('<svg', '<svg id="svg4"') + '</div></div>' +
      '<div style="text-align:center;"><h3 style="color:#6a5a45;font-family:Arial;font-size:16px;font-weight:bold;margin-bottom:12px;">v5（现在）</h3>' +
        '<div class="icon256">' + svg5.replace('<svg', '<svg id="svg5"') + '</div></div>' +
    '</div>' +
    '<div class="row">' +
      '<div class="card"><div class="icon128">' + svg5 + '</div><p>128×128</p></div>' +
      '<div class="card"><div class="icon64">' + svg5 + '</div><p>64×64</p></div>' +
      '<div class="card"><div class="icon48">' + svg5 + '</div><p>48×48</p></div>' +
    '</div>' +
    '<div style="background:#faf6ee;border-radius:12px;padding:24px;max-width:700px;margin-top:10px;border:1px solid #e0d4c0;">' +
    '<h3 style="font-family:Arial;color:#6a5a45;font-size:14px;margin-bottom:12px;">v5 改动说明</h3>' +
    '<ul style="font-family:Arial;font-size:13px;color:#8a7a60;line-height:2;list-style-type:circle;padding-left:20px;">' +
    '<li>背景极浅暖色 <code>#fffcf5 → #f5dfbd</code>，更清淡温暖</li>' +
    '<li>花瓣从 16 片增加到 26 片，更浓密有层次</li>' +
    '<li>花朵整体顺时针旋转 15°，倾斜度加大</li>' +
    '<li>花心移至 (256, 232)，画面居中更好</li>' +
    '</ul></div>' +
    '</body></html>';

  fs.writeFileSync(path.join(__dirname, 'icon-v5-compare.html'), html);
  const htmlPath = path.resolve(__dirname, 'icon-v5-compare.html').replace(/\\/g, '/');

  const browser = await puppeteer.launch({ executablePath: edgePath, headless: true, args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({width: 900, height: 900});
  await page.goto('file:///' + htmlPath, {waitUntil: 'networkidle0'});
  await page.screenshot({path: path.join(__dirname, 'icon-v5-compare-screenshot.png'), fullPage: true});
  await browser.close();
  const s = fs.statSync(path.join(__dirname, 'icon-v5-compare-screenshot.png'));
  console.log('Comparison screenshot saved: ' + s.size + ' bytes');
})();
