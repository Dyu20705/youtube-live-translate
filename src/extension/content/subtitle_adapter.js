/**
 * subtitle_adapter.js - Subtitle State Adapter.
 *
 * Enforces monotonic revision ordering, rejects stale frames, filters duplicate
 * states, handles backpressure, and coalesces updates to the browser animation cadence.
 */

export class SubtitleStateAdapter {
  constructor(renderer, options = {}) {
    this.renderer = renderer;
    this.options = {
      enableCoalescing: options.enableCoalescing !== false,
      logTelemetry: options.logTelemetry || false,
      ...options
    };

    // State tracking
    this.currentSegmentId = 0;
    this.currentSourceRevision = 0;
    this.lastCommittedText = '';
    this.lastProvisionalText = '';
    this.lastIsFinal = false;

    // Coalescing & Backpressure Queue
    this.pendingState = null;
    this.rafHandle = null;

    // Telemetry
    this.metrics = {
      totalReceived: 0,
      appliedUpdates: 0,
      noopUpdates: 0,
      staleRejectedUpdates: 0,
      coalescedUpdates: 0,
      renderLatenciesMs: []
    };
  }

  /**
   * Main entry point for wire messages (JSON string or parsed Object).
   * Returns boolean indicating if update was accepted for processing.
   */
  processMessage(rawMessage) {
    this.metrics.totalReceived += 1;
    const startTime = typeof performance !== 'undefined' ? performance.now() : Date.now();

    let data;
    try {
      data = typeof rawMessage === 'string' ? JSON.parse(rawMessage) : rawMessage;
    } catch (e) {
      if (this.options.logTelemetry) console.warn('[SubtitleAdapter] Rejected malformed JSON:', e);
      return false;
    }

    if (!data || typeof data !== 'object') {
      return false;
    }

    const type = data.type;
    if (type === 'status' || type === 'error') {
      if (this.renderer && typeof this.renderer.handleStatus === 'function') {
        this.renderer.handleStatus(data);
      }
      return true;
    }

    if (type !== 'subtitle.update' && type !== 'subtitle.final') {
      return false;
    }

    const segmentId = Number(data.segment_id || 0);
    const sourceRevision = Number(data.source_revision || 0);
    const committedText = String(data.committed_text || '');
    const provisionalText = String(data.provisional_text || '');
    const isFinal = Boolean(data.is_final || (type === 'subtitle.final'));

    // 1. Segment Monotonic Check
    if (segmentId < this.currentSegmentId) {
      this.metrics.staleRejectedUpdates += 1;
      return false;
    }

    // 2. Duplicate State Deduplication
    if (
      segmentId === this.currentSegmentId &&
      committedText === this.lastCommittedText &&
      provisionalText === this.lastProvisionalText &&
      isFinal === this.lastIsFinal
    ) {
      this.metrics.noopUpdates += 1;
      return false;
    }

    // 3. Stale Revision Protection within segment
    if (segmentId === this.currentSegmentId && sourceRevision <= this.currentSourceRevision) {
      this.metrics.staleRejectedUpdates += 1;
      return false;
    }

    const isNewSegment = segmentId > this.currentSegmentId;
    this.currentSegmentId = segmentId;
    this.currentSourceRevision = sourceRevision;

    // 4. Queue / Frame Coalescing
    if (this.options.enableCoalescing) {
      if (this.pendingState !== null) {
        this.metrics.coalescedUpdates += 1;
      }

      this.pendingState = {
        segmentId,
        sourceRevision,
        committedText,
        provisionalText,
        isFinal,
        isNewSegment,
        startTime
      };

      this._scheduleFrame();
    } else {
      this._applyState({
        segmentId,
        sourceRevision,
        committedText,
        provisionalText,
        isFinal,
        isNewSegment,
        startTime
      });
    }

    return true;
  }

  _scheduleFrame() {
    if (this.rafHandle !== null) {
      return; // Frame already scheduled
    }

    const requestFrame = typeof requestAnimationFrame !== 'undefined'
      ? requestAnimationFrame
      : (cb) => setTimeout(cb, 16);

    this.rafHandle = requestFrame(() => {
      this.rafHandle = null;
      if (this.pendingState) {
        const state = this.pendingState;
        this.pendingState = null;
        this._applyState(state);
      }
    });
  }

  _applyState(state) {
    this.lastCommittedText = state.committedText;
    this.lastProvisionalText = state.provisionalText;
    this.lastIsFinal = state.isFinal;
    this.metrics.appliedUpdates += 1;

    if (this.renderer) {
      this.renderer.renderSubtitle({
        segmentId: state.segmentId,
        committedText: state.committedText,
        provisionalText: state.provisionalText,
        isFinal: state.isFinal,
        isNewSegment: state.isNewSegment
      });
    }

    const endTime = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const latency = endTime - state.startTime;
    this.metrics.renderLatenciesMs.push(latency);
  }

  reset() {
    if (this.rafHandle !== null) {
      const cancelFrame = typeof cancelAnimationFrame !== 'undefined'
        ? cancelAnimationFrame
        : clearTimeout;
      cancelFrame(this.rafHandle);
      this.rafHandle = null;
    }
    this.pendingState = null;
    this.currentSegmentId = 0;
    this.currentSourceRevision = 0;
    this.lastCommittedText = '';
    this.lastProvisionalText = '';
    this.lastIsFinal = false;
    if (this.renderer && typeof this.renderer.clear === 'function') {
      this.renderer.clear();
    }
  }

  getTelemetry() {
    const latencies = [...this.metrics.renderLatenciesMs];
    latencies.sort((a, b) => a - b);
    const p50 = latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.5)] : 0;
    const p95 = latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.95)] : 0;

    return {
      ...this.metrics,
      p50RenderLatencyMs: Number(p50.toFixed(3)),
      p95RenderLatencyMs: Number(p95.toFixed(3))
    };
  }
}
