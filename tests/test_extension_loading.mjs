/** Load the packaged production extension on an intercepted YouTube page.
 * Run: NODE_PATH=<playwright install>/node_modules node tests/test_extension_loading.mjs
 * Requires Chromium and Playwright. No YouTube network requests are made.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdtemp, rm, readFile, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = process.env.YLT_DIST_DIR || path.join(root, 'dist');
const extension = path.join(dist, 'extension/youtube-live-translate');
const exec = promisify(execFile);
const report = {status:'FAILED', extension_id:null, tab_messaging:false, native_messaging:false};
const sandbox = await mkdtemp(path.join(tmpdir(), 'ylt-browser-'));
const config = path.join(sandbox, 'config');
const profile = path.join(config, 'chromium');
await mkdir(profile, {recursive:true});
let context;
try {
  context = await chromium.launchPersistentContext(profile, {
    executablePath: process.env.CHROMIUM_BIN || '/usr/bin/chromium',
    headless: true,
    env: {...process.env, XDG_CONFIG_HOME:config},
    ignoreDefaultArgs: ['--disable-extensions'],
    args: ['--enable-unsafe-extension-debugging', '--no-sandbox', `--disable-extensions-except=${extension}`, `--load-extension=${extension}`]
  });
  report.browser_version = context.browser().version();
  const cdp = await context.browser().newBrowserCDPSession();
  await cdp.send('Extensions.loadUnpacked', {path: extension});
  const errors = [];
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
  const id = new URL(worker.url()).host;
  report.extension_id = id;
  report.browser_version = context.browser().version();
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
  report.tab_messaging = true;

  const release = JSON.parse(await readFile(path.join(dist, 'release_manifest.json'), 'utf8'));
  const extracted = path.join(sandbox, 'package');
  await mkdir(extracted);
  await exec('tar', ['-xzf', path.join(dist, release.artifacts.runtime_tarball.path), '-C', extracted]);
  const packagedRuntime = path.join(extracted, 'youtube-live-translate-runtime-linux-x86_64-v1.0.0');
  await exec('bash', [path.join(packagedRuntime,'install.sh'), '--extension-id', id,
    '--target-dir', path.join(sandbox,'runtime'), '--browser-config-dir',config], {timeout:600000, maxBuffer:10*1024*1024});
  // Installation can outlast the MV3 worker lifetime. An extension page gives
  // the native-port assertion a fresh, live extension execution context.
  const nativePage = await context.newPage();
  await nativePage.goto(`chrome-extension://${id}/popup/popup.html`);
  const states = await nativePage.evaluate(() => new Promise((resolve,reject) => {
    const port = chrome.runtime.connectNative('com.duy.youtube_live_translate');
    const states = [];
    let finished = false;
    const timer = setTimeout(() => {port.disconnect(); reject(new Error('Native Messaging timed out'));}, 60000);
    port.onDisconnect.addListener(() => {
      const error = chrome.runtime.lastError;
      if (!finished) {clearTimeout(timer); reject(new Error(error?.message || 'Native host disconnected before lifecycle completed'));}
    });
    port.onMessage.addListener(message => {
      if (message.type === 'error') {clearTimeout(timer); reject(new Error(JSON.stringify(message))); port.disconnect(); return;}
      states.push(message.state);
      if (message.state === 'RUNNING') port.postMessage({type:'control.ping'});
      else if (message.state === 'HEALTHY') port.postMessage({type:'control.stop'});
      else if (message.state === 'STOPPED') {finished = true; clearTimeout(timer); port.disconnect(); resolve(states);}
    });
  }));
  assert.deepEqual(states, ['RUNNING','HEALTHY','STOPPED']);
  report.native_messaging = true;
  report.status = 'PASSED';
  console.log(`PASS: Production extension ${id} loaded, rendered an actual tab message and completed real Native Messaging RUNNING/HEALTHY/STOPPED.`);
} catch (error) {
  report.error = error.message;
  if (/disabled by the administrator/i.test(error.message)) {
    report.status = 'BLOCKED';
    process.exitCode = 2;
  } else {process.exitCode = 1;}
  console.error(`${report.status}: ${error.message}`);
} finally {
  if (context) await context.close();
  if (process.env.YLT_BROWSER_REPORT) await writeFile(process.env.YLT_BROWSER_REPORT, JSON.stringify(report,null,2)+'\n');
  await rm(sandbox, {recursive:true, force:true});
}
