/**
 * test_renderer.mjs - Unit tests for SubtitleStateAdapter and SubtitleRenderer (Tests A through J).
 * Runs cleanly in Node.js ES Modules environment.
 */

import assert from 'node:assert/strict';

// Lightweight DOM Mock for Node.js testing
class MockElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.id = '';
    this.className = '';
    const classes = new Set();
    this.classList = {
      _classes: classes,
      add: (c) => classes.add(c),
      remove: (c) => classes.delete(c),
      contains: (c) => classes.has(c)
    };

    this.style = {};
    this.textContent = '';
    this.children = [];
    this.parentNode = null;
    this.boxLeft = 100;
    this.boxTop = 200;
    this.boxWidth = 50;
    this.boxHeight = 30;
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    const idx = this.children.indexOf(child);
    if (idx !== -1) {
      this.children.splice(idx, 1);
      child.parentNode = null;
    }
    return child;
  }

  querySelector(selector) {
    if (selector.startsWith('#')) {
      const id = selector.slice(1);
      return this._find((el) => el.id === id);
    }
    if (selector.startsWith('.')) {
      const cls = selector.slice(1);
      return this._find((el) => el.classList.contains(cls));
    }
    return null;
  }

  _find(predicate) {
    if (predicate(this)) return this;
    for (const child of this.children) {
      const found = child._find(predicate);
      if (found) return found;
    }
    return null;
  }

  getBoundingClientRect() {
    return {
      left: this.boxLeft,
      top: this.boxTop,
      right: this.boxLeft + this.boxWidth,
      bottom: this.boxTop + this.boxHeight,
      width: this.boxWidth,
      height: this.boxHeight
    };
  }
}

globalThis.document = {
  createElement: (tag) => new MockElement(tag),
  body: new MockElement('body'),
  querySelector: (sel) => globalThis.document.body.querySelector(sel)
};

// Import S5 components
const { SubtitleRenderer } = await import('../content/subtitle_renderer.js');
const { SubtitleStateAdapter } = await import('../content/subtitle_adapter.js');

console.log('Running Stage S5 Renderer & Adapter Test Suite...\n');

let passedTests = 0;

function runTest(name, fn) {
  try {
    fn();
    console.log(`PASS: ${name}`);
    passedTests += 1;
  } catch (err) {
    console.error(`FAIL: ${name}`);
    console.error(err);
    process.exit(1);
  }
}

// Test A — Committed Update
runTest('Test A — Initial committed update creates distinct committed & provisional regions', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 1,
    committed_text: 'I want to',
    provisional_text: 'go home'
  });

  assert.equal(renderer.committedTextEl.textContent, 'I want to');
  assert.equal(renderer.provisionalTextEl.textContent, ' go home');
  assert.equal(renderer.committedBoxEl.style.display, 'inline');
  assert.equal(renderer.provisionalBoxEl.style.display, 'inline');
});

// Test B — Provisional Mutation
runTest('Test B — Updating provisional text does NOT change committed DOM node', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 1,
    committed_text: 'I want to',
    provisional_text: 'go home'
  });

  const committedNodeRef = renderer.committedTextEl;

  // Mutate provisional tail
  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 2,
    committed_text: 'I want to',
    provisional_text: 'go to the store'
  });

  assert.equal(renderer.committedTextEl, committedNodeRef); // Same DOM node
  assert.equal(renderer.committedTextEl.textContent, 'I want to');
  assert.equal(renderer.provisionalTextEl.textContent, ' go to the store');
});

// Test C — Finalization
runTest('Test C — Finalization clears provisional styling and merges text into committed presentation', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 1,
    committed_text: 'I want to',
    provisional_text: 'go to the store'
  });

  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.final',
    segment_id: 1,
    source_revision: 2,
    committed_text: 'I want to go to the store.',
    provisional_text: '',
    is_final: true
  });

  assert.equal(renderer.committedTextEl.textContent, 'I want to go to the store.');
  assert.equal(renderer.provisionalTextEl.textContent, '');
  assert.equal(renderer.provisionalBoxEl.style.display, 'none');
  assert.ok(renderer.lineEl.classList.contains('ylt-final'));
});

// Test D — Duplicate Message
runTest('Test D — Duplicate identical state triggers 0 repaints', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  const msg = {
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 1,
    committed_text: 'Hello',
    provisional_text: 'world'
  };

  const acc1 = adapter.processMessage(msg);
  assert.equal(acc1, true);

  const acc2 = adapter.processMessage(msg);
  assert.equal(acc2, false); // Rejected as duplicate
  assert.equal(adapter.metrics.noopUpdates, 1);
});

// Test E — Stale Message Protection
runTest('Test E — Older revision arriving after newer revision is safely rejected', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 10,
    committed_text: 'Newest',
    provisional_text: ''
  });

  // Out-of-order stale revision 9 arrives
  const accepted = adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 9,
    committed_text: 'Old',
    provisional_text: ''
  });

  assert.equal(accepted, false);
  assert.equal(adapter.metrics.staleRejectedUpdates, 1);
  assert.equal(renderer.committedTextEl.textContent, 'Newest');
});

// Test F — Rapid Frame Coalescing
runTest('Test F — Rapid updates coalesce into single render frame', () => {
  let scheduledCb = null;
  globalThis.requestAnimationFrame = (cb) => {
    scheduledCb = cb;
    return 1;
  };

  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: true });

  // Burst 5 updates in 1 frame
  for (let i = 1; i <= 5; i++) {
    adapter.processMessage({
      version: '1.0',
      type: 'subtitle.update',
      segment_id: 1,
      source_revision: i,
      committed_text: 'Stable',
      provisional_text: `burst ${i}`
    });
  }

  assert.equal(adapter.metrics.coalescedUpdates, 4);
  assert.equal(adapter.metrics.appliedUpdates, 0); // Not yet flushed to DOM

  // Execute animation frame
  scheduledCb();

  assert.equal(adapter.metrics.appliedUpdates, 1);
  assert.equal(renderer.provisionalTextEl.textContent, ' burst 5');
});

// Test G — Long Provisional Text Handling
runTest('Test G — Long provisional suffix updates without mutating committed structure', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 1,
    source_revision: 1,
    committed_text: 'Short',
    provisional_text: 'this is an extremely long provisional suffix that stretches across the viewport'
  });

  assert.equal(renderer.committedTextEl.textContent, 'Short');
  assert.ok(renderer.provisionalTextEl.textContent.includes('extremely long'));
});

// Test H — Segment Transition Isolation
runTest('Test H — Segment boundary cleanly resets without state leakage', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  // Segment 1
  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.final',
    segment_id: 1,
    source_revision: 1,
    committed_text: 'Segment One final.',
    provisional_text: '',
    is_final: true
  });
  assert.equal(renderer.committedTextEl.textContent, 'Segment One final.');

  // Segment 2 begins
  adapter.processMessage({
    version: '1.0',
    type: 'subtitle.update',
    segment_id: 2,
    source_revision: 1,
    committed_text: 'Segment Two',
    provisional_text: 'beginning'
  });

  assert.equal(renderer.committedTextEl.textContent, 'Segment Two');
  assert.equal(renderer.provisionalTextEl.textContent, ' beginning');
  assert.equal(renderer.lineEl.classList.contains('ylt-final'), false);
});

// Test I — Malformed Transport Message Handling
runTest('Test I — Malformed payloads reject safely without throwing', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  assert.equal(adapter.processMessage('INVALID_JSON'), false);
  assert.equal(adapter.processMessage(null), false);
  assert.equal(adapter.processMessage({ type: 'unknown_type' }), false);
});

// Test J — Runtime Degraded State Handling
runTest('Test J — Runtime status error/degraded updates status badge cleanly', () => {
  const container = document.createElement('div');
  const renderer = new SubtitleRenderer(container);
  const adapter = new SubtitleStateAdapter(renderer, { enableCoalescing: false });

  adapter.processMessage({
    version: '1.0',
    type: 'status',
    state: 'DEGRADED',
    message: 'Native bridge disconnected'
  });

  assert.equal(renderer.statusBadgeEl.style.display, 'block');
  assert.ok(renderer.statusBadgeEl.textContent.includes('DEGRADED'));
});

console.log(`\nAll ${passedTests} S5 Renderer & Adapter tests PASSED successfully!`);
