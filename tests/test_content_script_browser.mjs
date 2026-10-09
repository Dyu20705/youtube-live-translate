/** Chromium classic-script/module-loading harness with mocked Chrome messaging.
 * This checks production JS execution and rendering, not extension registration.
 * NODE_PATH=<playwright install>/node_modules node tests/test_content_script_browser.mjs
 */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium} = createRequire(import.meta.url)('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const browser = await chromium.launch({executablePath:process.env.CHROMIUM_BIN || '/usr/bin/chromium', headless:true, args:['--no-sandbox']});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://www.youtube.com/**', async route => {
    const filename = new URL(route.request().url()).pathname.split('/').pop();
    if (['subtitle_renderer.js','subtitle_adapter.js'].includes(filename)) {
      await route.fulfill({contentType:'application/javascript', body:await readFile(path.join(root, 'src/extension/content', filename), 'utf8')});
    } else {
      await route.fulfill({contentType:'text/html',body:'<html><body><div id="movie_player"><video></video></div></body></html>'});
    }
  });
  await page.addInitScript(() => {
    window.testListeners = [];
    window.chrome = {runtime: {
      getURL: name => new URL(name, 'https://www.youtube.com/').href,
      onMessage: {addListener: callback => testListeners.push(callback)}
    }, storage:{local:{get: (keys, callback) => callback({})}}};
  });
  await page.goto('https://www.youtube.com/watch?v=fixture');
  // addScriptTag has classic-script semantics: the old static imports fail here.
  await page.addScriptTag({path:path.join(root,'src/extension/content/content_script.js')});
  await page.waitForSelector('.ylt-viewport', {state:'attached'});
  const accepted = await page.evaluate(() => {
    let response;
    testListeners[0]({type:'SUBTITLE_EVENT',payload:{version:'1.0',type:'subtitle.update',segment_id:1,source_revision:1,committed_text:'Hello',provisional_text:'world'}}, {}, result => response=result);
    return response.success;
  });
  assert.equal(accepted,true);
  await page.waitForFunction(() => document.body.textContent.includes('Hello'));
  assert.deepEqual(errors,[]);
  console.log('PASS: Production classic content script imported modules and rendered a wire subtitle in Chromium (Chrome API harness).');
} finally {await browser.close();}
