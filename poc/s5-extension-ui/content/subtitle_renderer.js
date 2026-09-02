/**
 * subtitle_renderer.js - Anchored Layout & Stable Subtitle Presentation for Stage S5.
 * 
 * Implements the Anchored Layout Contract:
 * - Dedicated spatially anchored committed text box (100% solid opacity).
 * - Visually secondary provisional text box (65% dimmed opacity, italic).
 * - Zero spatial displacement of committed text when provisional text mutates.
 */

export class SubtitleRenderer {
  constructor(containerElement = null, options = {}) {
    this.container = containerElement || (typeof document !== 'undefined' ? document.body : null);
    this.options = {
      classNamePrefix: 'ylt-',
      committedOpacity: 1.0,
      provisionalOpacity: 0.65,
      ...options
    };

    this.viewportEl = null;
    this.lineEl = null;
    this.committedBoxEl = null;
    this.committedTextEl = null;
    this.provisionalBoxEl = null;
    this.provisionalTextEl = null;
    this.statusBadgeEl = null;

    this.renderedCommittedText = '';
    this.renderedProvisionalText = '';
    this.isMounted = false;

    if (this.container && typeof document !== 'undefined') {
      this.mount(this.container);
    }
  }

  mount(targetContainer) {
    if (!targetContainer || typeof document === 'undefined') return;
    this.container = targetContainer;

    // Check if already mounted
    let existing = this.container.querySelector('#ylt-subtitle-viewport');
    if (existing) {
      this.viewportEl = existing;
    } else {
      this.viewportEl = document.createElement('div');
      this.viewportEl.id = 'ylt-subtitle-viewport';
      this.viewportEl.className = 'ylt-viewport';
      this.container.appendChild(this.viewportEl);
    }

    this.viewportEl.innerHTML = '';

    // Line container with left-anchored flow
    this.lineEl = document.createElement('div');
    this.lineEl.className = 'ylt-subtitle-line';

    // Dedicated Committed Box (Solid, Anchored)
    this.committedBoxEl = document.createElement('span');
    this.committedBoxEl.className = 'ylt-committed-box';
    this.committedTextEl = document.createElement('span');
    this.committedTextEl.className = 'ylt-committed-text';
    this.committedBoxEl.appendChild(this.committedTextEl);

    // Dedicated Provisional Box (Dimmed, Attached to tail)
    this.provisionalBoxEl = document.createElement('span');
    this.provisionalBoxEl.className = 'ylt-provisional-box';
    this.provisionalTextEl = document.createElement('span');
    this.provisionalTextEl.className = 'ylt-provisional-text';
    this.provisionalBoxEl.appendChild(this.provisionalTextEl);

    this.lineEl.appendChild(this.committedBoxEl);
    this.lineEl.appendChild(this.provisionalBoxEl);
    this.viewportEl.appendChild(this.lineEl);

    // Status Badge
    this.statusBadgeEl = document.createElement('div');
    this.statusBadgeEl.className = 'ylt-status-badge';
    this.statusBadgeEl.style.display = 'none';
    this.viewportEl.appendChild(this.statusBadgeEl);

    this.isMounted = true;
  }

  renderSubtitle(state) {
    if (!this.isMounted) {
      if (this.container) this.mount(this.container);
      else return;
    }

    const { committedText, provisionalText, isFinal, isNewSegment } = state;

    // Reset line if new segment arrives
    if (isNewSegment) {
      this.lineEl.classList.remove('ylt-final');
    }

    // 1. Update Committed Region ONLY if text changed
    if (committedText !== this.renderedCommittedText) {
      this.committedTextEl.textContent = committedText;
      this.renderedCommittedText = committedText;
      
      if (committedText) {
        this.committedBoxEl.style.display = 'inline';
      } else {
        this.committedBoxEl.style.display = 'none';
      }
    }

    // 2. Update Provisional Region ONLY if text changed
    if (provisionalText !== this.renderedProvisionalText) {
      // Add leading space if committed text exists and provisional text doesn't start with space or punctuation
      let formattedProv = provisionalText;
      if (committedText && formattedProv && !formattedProv.startsWith(' ') && !/^[,.!?]/.test(formattedProv)) {
        formattedProv = ' ' + formattedProv;
      }
      this.provisionalTextEl.textContent = formattedProv;
      this.renderedProvisionalText = provisionalText;

      if (provisionalText) {
        this.provisionalBoxEl.style.display = 'inline';
      } else {
        this.provisionalBoxEl.style.display = 'none';
      }
    }

    // 3. Handle Finalization
    if (isFinal) {
      this.lineEl.classList.add('ylt-final');
      this.provisionalBoxEl.style.display = 'none';
      this.renderedProvisionalText = '';
      this.provisionalTextEl.textContent = '';
    } else {
      this.lineEl.classList.remove('ylt-final');
    }

    // Display viewport visibility
    if (!committedText && !provisionalText) {
      this.lineEl.style.display = 'none';
    } else {
      this.lineEl.style.display = 'inline-block';
    }
  }

  handleStatus(statusMsg) {
    if (!this.statusBadgeEl) return;
    const state = statusMsg.state || 'READY';
    if (state === 'DEGRADED' || state === 'ERROR') {
      this.statusBadgeEl.textContent = `Live Translate: ${state} (${statusMsg.message || ''})`;
      this.statusBadgeEl.style.display = 'block';
    } else {
      this.statusBadgeEl.style.display = 'none';
    }
  }

  clear() {
    this.renderedCommittedText = '';
    this.renderedProvisionalText = '';
    if (this.committedTextEl) this.committedTextEl.textContent = '';
    if (this.provisionalTextEl) this.provisionalTextEl.textContent = '';
    if (this.committedBoxEl) this.committedBoxEl.style.display = 'none';
    if (this.provisionalBoxEl) this.provisionalBoxEl.style.display = 'none';
    if (this.lineEl) this.lineEl.style.display = 'none';
    if (this.statusBadgeEl) this.statusBadgeEl.style.display = 'none';
  }

  destroy() {
    if (this.viewportEl && this.viewportEl.parentNode) {
      this.viewportEl.parentNode.removeChild(this.viewportEl);
    }
    this.isMounted = false;
    this.viewportEl = null;
    this.lineEl = null;
    this.committedBoxEl = null;
    this.committedTextEl = null;
    this.provisionalBoxEl = null;
    this.provisionalTextEl = null;
    this.statusBadgeEl = null;
  }
}
