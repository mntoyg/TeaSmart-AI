/**
 * Telling "the server could not be reached" apart from "the server answered no".
 *
 * The app has two ways to analyse a leaf: the server, which runs the whole
 * pipeline, and the model on the device, which runs the classifier alone. The
 * choice is currently made by `navigator.onLine`, which is true whenever the
 * phone has any network interface - a wifi access point with no route out
 * satisfies it. On a mountain estate that is the normal case, and the user sees
 * an error instead of a result.
 *
 * Falling back is right only when the request never got an answer. If the
 * server answered and said no - a blurred photograph the quality gate
 * rejected - running the classifier locally would paper over a deliberate
 * "take it again" with a result the server had already declined to give. And a
 * user who pressed cancel wants nothing to happen, not a second analysis.
 *
 * So these are the three cases, and they must stay distinguishable.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { isServerUnreachable, ServerUnreachableError, scanImage } from './api';

const leaf = () => new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' });

afterEach(() => vi.unstubAllGlobals());

describe('isServerUnreachable', () => {
  it('is true for the error the transport layer raises', () => {
    expect(isServerUnreachable(new ServerUnreachableError())).toBe(true);
  });

  it('is false for an ordinary error, which is how a refusal arrives', () => {
    expect(isServerUnreachable(new Error('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น'))).toBe(false);
  });

  it('is false for a user abort, so cancelling does not start a local scan', () => {
    expect(isServerUnreachable(new DOMException('cancelled', 'AbortError'))).toBe(false);
  });

  it('is false for things that are not errors at all', () => {
    for (const value of [undefined, null, 'offline', 0]) {
      expect(isServerUnreachable(value)).toBe(false);
    }
  });
});

describe('scanImage', () => {
  it('raises ServerUnreachableError when the request gets no answer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(scanImage(leaf())).rejects.toBeInstanceOf(ServerUnreachableError);
  });

  it('treats a timeout as unreachable, because no answer came back', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new DOMException('timed out', 'TimeoutError')),
    );
    await expect(scanImage(leaf())).rejects.toBeInstanceOf(ServerUnreachableError);
  });

  it('passes a user abort through unchanged, not as unreachable', async () => {
    const abort = new DOMException('cancelled', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort));
    await expect(scanImage(leaf())).rejects.toBe(abort);
  });

  it('does not call a refusal unreachable: the server answered', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail_th: 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น' }), {
          status: 422,
        }),
      ),
    );
    const failure = await scanImage(leaf()).catch((error: unknown) => error);
    expect(isServerUnreachable(failure)).toBe(false);
    expect(failure).toBeInstanceOf(Error);
    expect((failure as Error).message).toBe('ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น');
  });
});
