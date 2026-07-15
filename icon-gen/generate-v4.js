const sharp = require('sharp');
const path = require('path');

const SVG_PATH = path.join(__dirname, 'icon-v4.svg');

function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

async function main() {
  const bufs = {};
  for (const s of [512, 256, 128, 64, 48, 36, 32, 24, 16]) {
    bufs[s] = await sharp(SVG_PATH).resize(s, s).png().toBuffer();
  }

  // Save standalone
  await sharp(bufs[512]).toFile(path.join(__dirname, 'icon-v4-512.png'));
  await sharp(bufs[32]).toFile(path.join(__dirname, 'icon-v4-32.png'));
  console.log('Icon files saved');

  // ========== Composite preview ==========
  const W = 900, H = 1550;
  const bg = await sharp({ create: { width: W, height: H, channels: 4, background: { r: 30, g: 22, b: 18, alpha: 1 } } }).png().toBuffer();

  const layers = [{ input: bg, top: 0, left: 0 }];
  const e = [];

  function t(x, y, txt, size, color, align, bold) {
    const a = align === 'center' ? 'middle' : align === 'right' ? 'end' : 'start';
    return `<text x="${x}" y="${y}" font-size="${size||14}" fill="${color||'#ccc'}" font-family="Arial,sans-serif" text-anchor="${a}" font-weight="${bold?'bold':'normal'}">${esc(txt)}</text>`;
  }
  function r(x, y, w, h, fill, rx) {
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx||0}" fill="${fill}"/>`;
  }
  function c(cx, cy, r2, fill) {
    return `<circle cx="${cx}" cy="${cy}" r="${r2}" fill="${fill}"/>`;
  }

  // Title
  e.push(t(450, 45, '游戏全能脚本', 28, '#f0d080', 'center', true));
  e.push(t(450, 72, '桌面应用图标设计 v4 — 油画风格', 14, '#998070', 'center'));

  // Hero
  e.push(r(50, 95, 800, 340, '#1a1410', 16));
  e.push(r(50, 95, 800, 340, 'none', 16));
  layers.push({ input: bufs[256], top: 125, left: 100 });
  e.push(t(430, 170, '游戏全能脚本', 22, '#f0d080', 'left', true));
  e.push(t(430, 195, 'Game All-in-One Script', 13, '#d4a828'));
  e.push(t(430, 225, '油画风格 · 侧视花朵 · 真实结构', 13, '#c0a070', 'left', true));
  e.push(t(430, 250, '暗色暖底画布，金色层叠花瓣，侧视角度面向右侧。', 12, '#a09080'));
  e.push(t(430, 270, '14 层渐变花瓣叠加，营造油画笔触般的丰富质感。', 12, '#a09080'));
  e.push(t(430, 290, '花蕊带柔光发光效果，花茎自然弯曲，绿叶配叶脉。', 12, '#a09080'));
  e.push(t(430, 315, '尺寸: 512' + String.fromCharCode(215) + '512 | 风格: 油画写实 | 深色暖底', 11, '#807060'));

  // Size variations
  e.push(r(50, 460, 220, 2, '#4a3520'));
  e.push(t(60, 482, '尺寸预览 / Size Variations', 16, '#d0b080', 'left', true));
  const vs = [
    [128, '128' + String.fromCharCode(215) + '128', '桌面快捷方式', 60, 505],
    [64, '64' + String.fromCharCode(215) + '64', '开始菜单', 260, 540],
    [48, '48' + String.fromCharCode(215) + '48', '任务栏', 400, 558],
    [32, '32' + String.fromCharCode(215) + '32', '标题栏', 520, 574],
    [16, '16' + String.fromCharCode(215) + '16', '系统托盘', 630, 590],
  ];
  for (const [sz, label, sub, vx, vy] of vs) {
    e.push(r(vx - 10, vy - 10, sz + 50, sz + 58, '#1a1410', 10));
    e.push(t(vx + sz/2 + 15, vy + sz + 25, label, 12, '#a09080', 'center'));
    e.push(t(vx + sz/2 + 15, vy + sz + 42, sub, 10, '#706050', 'center'));
    layers.push({ input: bufs[sz], top: vy, left: vx + 10 });
  }

  // Use cases
  const y1 = 685;
  e.push(r(50, y1, 220, 2, '#4a3520'));
  e.push(t(60, y1 + 22, '使用场景 / Use Case Mockups', 16, '#d0b080', 'left', true));

  // Desktop
  e.push(r(50, y1 + 40, 400, 240, '#1a1410', 14));
  e.push(t(70, y1 + 62, '桌面快捷方式 / Desktop', 13, '#c0a070', 'left', true));
  e.push(r(70, y1 + 75, 360, 175, '#1a1410', 10));
  e.push(r(70, y1 + 75, 360, 175, '#2a2218', 10));
  layers.push({ input: bufs[64], top: y1 + 105, left: 120 });
  e.push(t(175, y1 + 185, '游戏全能脚本', 11, '#d0b080', 'center'));
  e.push(r(260, y1 + 108, 56, 56, '#2a2218', 8));
  e.push(t(288, y1 + 180, '游戏工具', 11, '#706050', 'center'));
  e.push(r(350, y1 + 108, 56, 56, '#2a2218', 8));
  e.push(t(378, y1 + 180, '配置文件', 11, '#706050', 'center'));

  // Taskbar
  e.push(r(470, y1 + 40, 380, 240, '#1a1410', 14));
  e.push(t(490, y1 + 62, '任务栏 / Taskbar', 13, '#c0a070', 'left', true));
  e.push(r(490, y1 + 75, 340, 48, '#222222', 8));
  e.push(r(498, y1 + 83, 36, 36, '#333333', 6));
  e.push(r(540, y1 + 83, 36, 36, '#1a1410', 6));
  e.push(r(582, y1 + 83, 36, 36, '#333333', 6));
  e.push(r(624, y1 + 83, 36, 36, '#333333', 6));
  e.push(t(810, y1 + 105, '14:30', 11, '#605040', 'right'));
  layers.push({ input: bufs[24], top: y1 + 89, left: 546 });

  // Title bar
  e.push(r(50, y1 + 300, 380, 180, '#1a1410', 14));
  e.push(t(70, y1 + 322, '窗口标题栏 / Title Bar', 13, '#c0a070', 'left', true));
  e.push(r(70, y1 + 335, 340, 32, '#222222', 8));
  e.push(c(84, y1 + 351, 5, '#5f3a3a'));
  e.push(c(98, y1 + 351, 5, '#5a4a20'));
  e.push(c(112, y1 + 351, 5, '#2a4a2a'));
  e.push(t(135, y1 + 356, '游戏全能脚本', 12, '#c0a070'));
  e.push(r(70, y1 + 367, 340, 70, '#1a1410', 0));
  e.push(t(240, y1 + 400, '窗口内容区域', 12, '#504030', 'center'));
  layers.push({ input: bufs[16], top: y1 + 342, left: 135 });

  // Start menu
  e.push(r(470, y1 + 300, 380, 180, '#1a1410', 14));
  e.push(t(490, y1 + 322, '开始菜单 / Start Menu', 13, '#c0a070', 'left', true));
  e.push(r(490, y1 + 335, 340, 110, '#1e1a14', 10));
  e.push(r(502, y1 + 345, 316, 48, '#2a2218', 8));
  e.push(t(555, y1 + 365, '游戏全能脚本', 13, '#f0d080'));
  e.push(t(555, y1 + 382, 'Game All-in-One Script', 10, '#706050'));
  e.push(r(508, y1 + 405, 32, 32, '#2a2218', 6));
  e.push(t(555, y1 + 425, '最近添加', 12, '#605040'));
  layers.push({ input: bufs[36], top: y1 + 347, left: 508 });

  // Color palette
  const y2 = 1210;
  e.push(r(50, y2, 220, 2, '#4a3520'));
  e.push(t(60, y2 + 22, '色彩体系 / Color Palette', 16, '#d0b080', 'left', true));

  const palette = [
    ['画布背景', '#20140e', 60, '#20140e'],
    ['花瓣亮金', '#f5d850', 170, '#f5d850'],
    ['花瓣深金', '#b8881e', 280, '#b8881e'],
    ['花蕊橙色', '#dd5500', 390, '#dd5500'],
    ['茎叶绿色', '#5a7a36', 500, '#5a7a36'],
    ['外框金色', '#8a7050', 610, '#8a7050'],
  ];
  for (const [name, fill, px, hex] of palette) {
    e.push(r(px, y2 + 35, 44, 44, '#1a1410', 8));
    e.push(r(px + 2, y2 + 37, 40, 40, fill, 7));
    e.push(t(px + 22, y2 + 90, name, 10, '#a09080', 'center'));
    e.push(t(px + 22, y2 + 103, hex, 8, '#706050', 'center'));
  }

  // Design notes
  e.push(r(660, y2 + 10, 190, 130, '#1a1410', 12));
  e.push(t(755, y2 + 32, '设计说明', 13, '#d4a828', 'center', true));
  e.push(t(755, y2 + 55, '油画风格 · 侧视花朵', 11, '#a09080', 'center'));
  e.push(t(755, y2 + 73, '14层渐变花瓣叠加', 11, '#a09080', 'center'));
  e.push(t(755, y2 + 91, '柔光花蕊+真实叶脉', 11, '#a09080', 'center'));
  e.push(t(755, y2 + 109, '暗色暖底适配深色桌面', 11, '#a09080', 'center'));

  const svgContent = '<svg width="' + W + '" height="' + H + '" xmlns="http://www.w3.org/2000/svg">' + e.join('\n') + '</svg>';
  const svgPng = await sharp(Buffer.from(svgContent)).resize(W, H).png().toBuffer();
  layers.push({ input: svgPng, top: 0, left: 0 });

  await sharp(layers[0].input).composite(layers.slice(1)).png().toFile(path.join(__dirname, 'icon-v4-preview.png'));
  console.log('Preview image saved');
}

main().catch(err => { console.error(err); process.exit(1); });
