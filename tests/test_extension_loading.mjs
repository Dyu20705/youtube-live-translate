/** Load the packaged production extension on an intercepted YouTube page.
 * Run: NODE_PATH=<playwright install>/node_modules node tests/test_extension_loading.mjs
 * Requires Chromium and Playwright. No YouTube network requests are made.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const extension = path.join(root, 'dist/extension/youtube-live-translate');
const profile = await mkdtemp(path.join(tmpdir(), 'ylt-browser-'));
let context;
try {
  context = await chromium.launchPersistentContext(profile, {
    executablePath: process.env.CHROMIUM_BIN || '/usr/bin/chromium',
    headless: true,
    ignoreDefaultArgs: ['--disable-extensions'],
    args: ['--enable-unsafe-extension-debugging', '--no-sandbox', `--disable-extensions-except=${extension}`, `--load-extension=${extension}`]
  });
  const cdp = await context.browser().newBrowserCDPSession();
  await cdp.send('Extensions.loadUnpacked', {path: extension});
  const errors = [];
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
  const id = new URL(worker.url()).host;
  assert.match(id, /^[a-p]{32}$/);
  const page = await context.newPage();
  await page.route('https://www.youtube.com/**', route => route.fulfill({
    contentType: 'text/html',
    body: '<html><body><div id="movie_player" style="width:1280px;height:720px"><video></video></div></body></html>'
  }));
  await page.goto('https://www.youtube.com/watch?v=fixture');
  await page.waitForSelector('.ylt-viewport', { state: 'attached', timeout: 15000 });
  const telemetry = await worker.evaluate(async () => {
    const [tab] = await chrome.tabs.query({url: 'https://www.youtube.com/*'});
    await chrome.tabs.sendMessage(tab.id, {type:'SUBTITLE_EVENT', payload:{
      version:'1.0', type:'subtitle.update', segment_id:1, source_revision:1,
      committed_text:'Hello', provisional_text:'world', is_final:false
    }});
    return chrome.tabs.sendMessage(tab.id, {type:'GET_RENDERER_TELEMETRY'});
  });
  await page.waitForFunction(() => document.body.textContent.includes('Hello'));
  assert.equal(telemetry.success, true);
  assert.deepEqual(errors, []);
  console.log(`PASS: Production extension ${id} loaded, received a wire subtitle and rendered it in Chromium.`);
} finally {
  if (context) await context.close();
  await rm(profile, {recursive:true, force:true});
}
