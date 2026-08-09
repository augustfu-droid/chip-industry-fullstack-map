#!/usr/bin/env node

import { createRequire } from 'node:module';
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);

let marked;
try {
  ({ marked } = require('marked'));
} catch {
  console.error('缺少 marked。请先运行 npm install，或设置 NODE_PATH 指向已安装 marked 的目录。');
  process.exit(1);
}

const ROOT = dirname(fileURLToPath(import.meta.url));
const DEFAULT_SOURCE = join(ROOT, '芯片产业链全栈技术图谱_公开版.md');
const DEFAULT_CANONICAL = join(ROOT, '芯片产业链全栈技术图谱_公开版.pdf');
const DEFAULT_HTML = join(ROOT, 'tmp', 'pdfs', '芯片产业链全栈技术图谱_公开版.html');

function optionValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : resolve(process.argv[index + 1]);
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function extractFrontMatter(markdown) {
  const lines = markdown.split(/\r?\n/);
  const separatorIndex = lines.findIndex(
    (line, index) => index > 1 && line.trim() === '---',
  );
  if (separatorIndex === -1) {
    throw new Error('文档开头缺少用于分隔封面与正文的 ---。');
  }

  const title = lines[0].replace(/^#\s+/, '').trim();
  const subtitle = lines[1].replace(/^##\s+/, '').trim();
  const metadata = lines
    .slice(2, separatorIndex)
    .map((line) => line.replace(/^>\s?/, '').trim())
    .filter(Boolean);
  const version = metadata[0]?.match(/版本\s+([^·]+)/)?.[1]?.trim() ?? '公开版';
  const maintained = metadata[0]?.match(/维护\s+(\d{4}-\d{2}-\d{2})/)?.[1] ?? '';

  return {
    title,
    subtitle,
    metadata,
    version,
    maintained,
    body: lines.slice(separatorIndex + 1).join('\n'),
  };
}

function decorateHtml(html) {
  return html
    .replace(
      /<p><img src="([^"]+)" alt="([^"]*)"(?: title="([^"]*)")?><\/p>/g,
      (_match, src, alt, title = '') => (
        `<figure><img src="${src}" alt="${alt}"${title ? ` title="${title}"` : ''}>` +
        `<figcaption>${alt}</figcaption></figure>`
      ),
    )
    .replace('<h2>目录</h2>\n<ul>', '<h2>目录</h2>\n<ul class="toc">')
    .replace(/<h2>(卷[^<]+)<\/h2>/g, '<h2 class="volume-title">$1</h2>')
    .replace(/<h3>(第\s*\d+\s*章[^<]*)<\/h3>/g, '<h3 class="chapter-title">$1</h3>')
    .replace(/<h3>(附录\s+[A-H][^<]*)<\/h3>/g, '<h3 class="appendix-title">$1</h3>')
    .replace(
      /(?:<p>)?<a id="([^"]+)"><\/a>(?:<\/p>)?\s*<h2([^>]*)>/g,
      '<h2$2 id="$1">',
    )
    .replace(
      /<hr>\s*(<h[23](?: class="(?:chapter-title|appendix-title|volume-title)")?[^>]*>)/g,
      '$1',
    )
    .replace(
      /<h4>(第\s*\d+\s*章参考文献)<\/h4>([\s\S]*?)(?=<h[23][^>]*>)/g,
      '<section class="chapter-references"><h4>$1</h4>$2</section>',
    )
    .replace(
      /<hr>\s*<p><em>(本文档为公开版调研报告[^<]+)<\/em><\/p>\s*$/,
      '',
    );
}

function coverHtml(front) {
  const metadata = front.metadata.map((line) => `<p>${escapeHtml(line)}</p>`).join('\n');
  return `
    <section class="cover">
      <div class="cover-grid" aria-hidden="true"></div>
      <div class="cover-kicker">SEMICONDUCTOR FULL-STACK MAP</div>
      <h1>${escapeHtml(front.title)}</h1>
      <p class="cover-subtitle">${escapeHtml(front.subtitle)}</p>
      <div class="cover-rule"></div>
      <p class="cover-deck">从底层物理、材料与制造工艺，到先进封装、异构计算、软件栈与财务验证</p>
      <div class="cover-topics" aria-label="报告覆盖范围">
        <span>材料</span><span>EDA / IP</span><span>设备</span><span>晶圆制造</span>
        <span>先进封装</span><span>HBM / CPO</span><span>异构计算</span><span>财务与估值</span>
      </div>
      <div class="cover-meta">${metadata}</div>
      <div class="cover-brand">大队长出品 · fqsx@mail.ustc.edu.cn</div>
    </section>`;
}

const sourcePath = optionValue('--source', DEFAULT_SOURCE);
const canonicalPath = optionValue('--canonical', DEFAULT_CANONICAL);
const htmlPath = optionValue('--html', DEFAULT_HTML);
const skipCanonical = process.argv.includes('--no-canonical');

for (const path of [sourcePath, join(ROOT, 'pdf', 'report.css')]) {
  if (!existsSync(path)) {
    throw new Error(`缺少构建输入：${path}`);
  }
}

const front = extractFrontMatter(readFileSync(sourcePath, 'utf8'));
if (!/^[A-Za-z0-9._-]+$/.test(front.version)) {
  throw new Error(`版本号包含不安全字符：${front.version}`);
}
const outputPath = optionValue(
  '--output',
  join(ROOT, 'output', 'pdf', `芯片产业链全栈技术图谱_公开版_${front.version}.pdf`),
);
marked.setOptions({ gfm: true, breaks: false });
const bodyHtml = decorateHtml(marked.parse(front.body));
const css = readFileSync(join(ROOT, 'pdf', 'report.css'), 'utf8')
  .replaceAll('__REPORT_VERSION__', front.version);
const documentHtml = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="author" content="付强">
  <meta name="description" content="芯片产业链全栈技术、产业格局与财务验证公开研究报告">
  <meta name="keywords" content="半导体,芯片产业链,HBM,High-NA EUV,先进封装,资本开支">
  <meta name="version" content="${escapeHtml(front.version)}">
  <meta name="maintained" content="${escapeHtml(front.maintained)}">
  <title>${escapeHtml(front.title)}</title>
  <style>${css}</style>
</head>
<body>
  ${coverHtml(front)}
  <div class="watermark" aria-hidden="true">大队长出品</div>
  <main>${bodyHtml}</main>
</body>
</html>`;

mkdirSync(dirname(htmlPath), { recursive: true });
mkdirSync(dirname(outputPath), { recursive: true });
mkdirSync(join(ROOT, 'tmp', 'pdfs', 'font-cache'), { recursive: true });
mkdirSync(join(ROOT, 'tmp', 'pdfs', 'weasy-cache'), { recursive: true });
writeFileSync(htmlPath, documentHtml, 'utf8');

const weasyprint = process.env.WEASYPRINT_BIN || 'weasyprint';
const result = spawnSync(
  weasyprint,
  [
    '--pdf-version', '1.7',
    '--pdf-tags',
    '--custom-metadata',
    '--optimize-images',
    '--base-url', ROOT,
    '--cache-folder', join(ROOT, 'tmp', 'pdfs', 'weasy-cache'),
    htmlPath,
    outputPath,
  ],
  {
    cwd: ROOT,
    encoding: 'utf8',
    env: {
      ...process.env,
      XDG_CACHE_HOME: join(ROOT, 'tmp', 'pdfs', 'font-cache'),
    },
  },
);

if (result.status !== 0) {
  process.stderr.write(result.stdout || '');
  process.stderr.write(result.stderr || '');
  process.exit(result.status ?? 1);
}

if (result.stderr?.trim()) {
  process.stderr.write(result.stderr);
}

if (!skipCanonical) {
  copyFileSync(outputPath, canonicalPath);
}

console.log(`HTML：${htmlPath}`);
console.log(`PDF：${outputPath}`);
if (!skipCanonical) {
  console.log(`兼容入口：${canonicalPath}`);
}
console.log(`文件：${basename(outputPath)}`);
