const sharp = require('sharp');
const path = require('path');

const SVG_PATH = path.join(__dirname, 'icon-v5.svg');

function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

async function main() {
  const bufs = {};
  for (const s of [512, 256, 128, 64, 48, 36, 32, 24, 16]) {
    bufs[s] = await sharp(SVG_PATH).resize(s, s).png().toBuffer();
  }

  // Save standalone
  await sharp(bufs[512]).toFile(path.join(__dirname, 'icon-v5-512.png'));
  await sharp(bufs[32]).toFile(path.join(__dirname, 'icon-v5-32.png'));
  console.log('Icon files saved');

  // ========== Composite preview ==========
  const W = 900, H = 1550;
  const bg = await sharp({ create: { width: W, height: H, channels: 4, background: { r: 232, g: 220, b: 206, alpha: 1 } } }).png().toBuffer();

  const layers = [{ input: bg, top: 0, left: 0 }];
  const e = [];

  function t(x, y, txt, size, color, align, bold) {
    const a = align === 'center' ? 'middle' : align === 'right' ? 'end' : 'start';
    return `<text x="${x}" y="${y}" font-size="${size||14}" fill="${color||'#ccc'}" font-family="Arial,sans-serif" text-anchor="${a}" font-weight="${bold?'bold':'normal'}">${esc(txt)}</text>`;
  }
  function r(x, y, w, h, fill, rx) {
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx||0}" fill="${fill}"/>`;
  }

  // Title
  e.push(t(450, 45, '游戏全能脚本', 28, '#5a4a38', 'center', true));
  e.push(t(450, 72, '桌面应用图标设计 v5 — 浓密花朵 · 极浅暖色 · 15°倾斜 · 居中', 13, '#8a7a68', 'center'));

  // Hero
  e.push(r(50, 95, 800, 340, '#f8f2e6', 16));
  layers.push({ input: bufs[256], top: 125, left: 100 });
  e.push(t(430, 170, '游戏全能脚本', 22, '#5a4a38', 'left', true));
  e.push(t(430, 195, 'Game All-in-One Script', 13, '#b88820'));
  e.push(t(430, 225, '浓密油画 · 15°倾斜 · 居中布局', 13, '#7a6a58', 'left', true));
  e.push(t(430, 250, '花瓣从 16 片增加到 26 片，更浓密饱满。', 12, '#8a7a68'));
  e.push(t(430, 270, '极浅暖色画布背景，整体向右倾斜 15°。', 12, '#8a7a68'));
  e.push(t(430, 290, '花心移至 (256, 232)，画面居中更平衡。', 12, '#8a7a68'));
  e.push(t(430, 315, '尺寸: 512' + String.fromCharCode(215) + '512 | 风格: 油画写实 | 极浅暖底', 11, '#a89880'));

  // Size variations
  e.push(r(50, 460, 220, 2, '#c8bcac'));
  e.push(t(60, 482, '尺寸预览 / Size Variations', 16, '#5a4a38', 'left', true));
  const vs = [
    [128, '128' + String.fromCharCode(215) + '128', '桌面快捷方式', 60, 505],
    [64, '64' + String.fromCharCode(215) + '64', '开始菜单', 260, 540],
    [48, '48' + String.fromCharCode(215) + '48', '任务栏', 400, 558],
    [32, '32' + String.fromCharCode(215) + '32', '标题栏', 520, 574],
    [16, '16' + String.fromCharCode(215) + '16', '系统托盘', 630, 590],
  ];
  for (const [sz, label, sub, vx, vy] of vs) {
    e.push(r(vx - 10, vy - 10, sz + 50, sz + 58, '#f8f2e6', 10));
    e.push(t(vx + sz/2 + 15, vy + sz + 25, label, 12, '#7a6a58', 'center'));
    e.push(t(vx + sz/2 + 15, vy + sz + 42, sub, 10, '#a89880', 'center'));
    layers.push({ input: bufs[sz], top: vy, left: vx + 10 });
  }

  // Use cases
  const y1 = 685;
  e.push(r(50, y1, 220, 2, '#c8bcac'));
  e.push(t(60, y1 + 22, '使用场景 / Use Case Mockups', 16, '#5a4a38', 'left', true));

  // Desktop
  e.push(r(50, y1 + 40, 400, 240, '#f8f2e6', 14));
  e.push(t(70, y1 + 62, '桌面快捷方式 / Desktop', 13, '#7a6a58', 'left', true));
  e.push(r(70, y1 + 75, 360, 175, '#ece2d4', 10));
  layers.push({ input: bufs[64], top: y1 + 105, left: 120 });
  e.push(t(175, y1 + 185, '游戏全能脚本', 11, '#5a4a38', 'center'));
  e.push(r(260, y1 + 108, 56, 56, '#e0d4c4', 8));
  e.push(t(288, y1 + 180, '游戏工具', 11, '#a89880', 'center'));
  e.push(r(350, y1 + 108, 56, 56, '#e0d4c4', 8));
  e.push(t(378, y1 + 180, '配置文件', 11, '#a89880', 'center'));

  // Taskbar
  e.push(r(470, y1 + 40, 380, 240, '#f8f2e6', 14));
  e.push(t(490, y1 + 62, '任务栏 / Taskbar', 13, '#7a6a58', 'left', true));
  e.push(r(490, y1 + 75, 340, 48, '#d0c4b4', 8));
  e.push(r(498, y1 + 83, 36, 36, '#c0b4a4', 6));
  e.push(r(540, y1 + 83, 36, 36, '#f8f2e6', 6));
  e.push(r(582, y1 + 83, 36, 36, '#c0b4a4', 6));
  e.push(r(624, y1 + 83, 36, 36, '#c0b4a4', 6));
  e.push(t(810, y1 + 105, '14:30', 11, '#8a7a68', 'right'));
  layers.push({ input: bufs[24], top: y1 + 89, left: 546 });

  // Title bar
  e.push(r(50, y1 + 300, 380, 180, '#f8f2e6', 14));
  e.push(t(70, y1 + 322, '窗口标题栏 / Title Bar', 13, '#7a6a58', 'left', true));
  e.push(r(70, y1 + 335, 340, 32, '#d0c4b4', 8));
  e.push(r(70, y1 + 367, 340, 70, '#e8dcce', 0));
  e.push(t(240, y1 + 400, '窗口内容区域', 12, '#b8ac9c', 'center'));
  layers.push({ input: bufs[16], top: y1 + 342, left: 120 });

  // Start menu
  e.push(r(470, y1 + 300, 380, 180, '#f8f2e6', 14));
  e.push(t(490, y1 + 322, '开始菜单 / Start Menu', 13, '#7a6a58', 'left', true));
  e.push(r(490, y1 + 335, 340, 110, '#ece2d4', 10));
  e.push(r(502, y1 + 345, 316, 48, '#f8f2e6', 8));
  e.push(t(555, y1 + 365, '游戏全能脚本', 13, '#5a4a38'));
  e.push(t(555, y1 + 382, 'Game All-in-One Script', 10, '#a89880'));
  layers.push({ input: bufs[36], top: y1 + 347, left: 508 });

  // Color palette
  const y2 = 1210;
  e.push(r(50, y2, 220, 2, '#c8bcac'));
  e.push(t(60, y2 + 22, '色彩体系 / Color Palette', 16, '#5a4a38', 'left', true));

  const palette = [
    ['画布高光', '#fffcf5', 60],
    ['画布暗部', '#f5dfbd', 170],
    ['花瓣亮金', '#f5d850', 280],
    ['花瓣深金', '#b8881e', 390],
    ['茎叶绿色', '#5a7a36', 500],
    ['外框金色', '#c8b090', 610],
  ];
  for (const [name, fill, px] of palette) {
    e.push(r(px + 1, y2 + 36, 42, 42, '#d8ccbc', 8));
    e.push(r(px + 2, y2 + 37, 40, 40, fill, 7));
    e.push(t(px + 22, y2 + 90, name, 10, '#7a6a58', 'center'));
    e.push(t(px + 22, y2 + 103, fill, 8, '#a89880', 'center'));
  }

  // Design notes
  e.push(r(660, y2 + 10, 190, 130, '#f8f2e6', 12));
  e.push(t(755, y2 + 32, 'v5 设计要点', 13, '#b88820', 'center', true));
  e.push(t(755, y2 + 55, '26 片浓密花瓣', 11, '#7a6a58', 'center'));
  e.push(t(755, y2 + 73, '极浅暖色画布', 11, '#7a6a58', 'center'));
  e.push(t(755, y2 + 91, '15° 向右倾斜', 11, '#7a6a58', 'center'));
  e.push(t(755, y2 + 109, '花心居中布局', 11, '#7a6a58', 'center'));

  const svgContent = '<svg width="' + W + '" height="' + H + '" xmlns="http://www.w3.org/2000/svg">' + e.join('\n') + '</svg>';
  const svgPng = await sharp(Buffer.from(svgContent)).resize(W, H).png().toBuffer();
  layers.push({ input: svgPng, top: 0, left: 0 });

  await sharp(layers[0].input).composite(layers.slice(1)).png().toFile(path.join(__dirname, 'icon-v5-preview.png'));
  console.log('Preview image saved');
}

main().catch(err => { console.error(err); process.exit(1); });
