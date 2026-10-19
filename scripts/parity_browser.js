/**
 * The browser half of the section 8.4 parity check.
 *
 *   1. backend/.venv/Scripts/python.exe scripts/prepare_parity.py
 *   2. cd frontend && npm run dev
 *   3. open http://localhost:5173/scan, then paste this into the console
 *
 * It decodes the same JPEGs the Python side read, preprocesses them with the
 * app's own `preprocess`, runs the same ONNX graph through onnxruntime-web,
 * and compares against the answer sheet. Top-1 must agree on every image and
 * no class probability may differ by more than 0.05.
 *
 * It deliberately goes through `createImageBitmap` and a canvas, which is how
 * the app gets pixels from a file. That means JPEG decoding differences
 * between Pillow and the browser are inside the measurement rather than
 * assumed away.
 *
 * Note the dynamic imports: they only resolve under the dev server, which
 * serves `/src` and `/node_modules`. This is a development check, not
 * something the built app can run.
 */
export async function runParity() {
  const answers = await (await fetch('/parity/answers.json')).json();
  const config = await (await fetch('/api/v1/config')).json();

  const ort = await import('/node_modules/onnxruntime-web/dist/ort.wasm.min.mjs');
  ort.env.wasm.numThreads = 1;
  const session = await ort.InferenceSession.create(`/models/${config.onnx.file}`, {
    executionProviders: ['wasm'],
  });
  const { preprocess } = await import('/src/lib/inference.ts');

  async function rgbOf(url) {
    const bitmap = await createImageBitmap(await (await fetch(url)).blob());
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(bitmap, 0, 0);
    const data = ctx.getImageData(0, 0, bitmap.width, bitmap.height).data;
    const rgb = new Uint8Array(bitmap.width * bitmap.height * 3);
    for (let i = 0, j = 0; i < data.length; i += 4, j += 3) {
      rgb[j] = data[i];
      rgb[j + 1] = data[i + 1];
      rgb[j + 2] = data[i + 2];
    }
    return { rgb, width: bitmap.width, height: bitmap.height };
  }

  const softmax = (v) => {
    const m = Math.max(...v);
    const e = v.map((x) => Math.exp(x - m));
    const s = e.reduce((a, b) => a + b, 0);
    return e.map((x) => x / s);
  };

  let agree = 0;
  let worst = 0;
  let worstFile = '';
  let sumDelta = 0;
  let n = 0;
  const disagreements = [];

  for (const entry of answers.entries) {
    const { rgb, width, height } = await rgbOf(`/parity/${entry.file}`);
    if (width !== entry.width || height !== entry.height) {
      disagreements.push(`${entry.file}: decoded ${width}x${height}, expected ${entry.width}x${entry.height}`);
      continue;
    }
    const input = preprocess(rgb, width, height, config);
    const out = await session.run({
      [config.onnx.input]: new ort.Tensor('float32', input, [1, 3, 224, 224]),
    });
    const probs = softmax(Array.from(out[config.onnx.output].data));
    const top = config.class_order[probs.indexOf(Math.max(...probs))];
    const delta = Math.max(...probs.map((p, i) => Math.abs(p - entry.probabilities[i])));

    sumDelta += delta;
    n++;
    if (delta > worst) {
      worst = delta;
      worstFile = entry.file;
    }
    if (top === entry.top1) agree++;
    else disagreements.push(`${entry.file}: browser ${top} vs python ${entry.top1}`);
  }

  return {
    images: n,
    top1_agreement: `${agree}/${n}`,
    max_prob_delta: +worst.toFixed(5),
    mean_prob_delta: +(sumDelta / n).toFixed(5),
    worstFile,
    bound: answers.bound,
    passes: agree === n && worst <= answers.bound,
    disagreements,
  };
}

// Paste-and-run convenience when this file is dropped straight into a console.
if (typeof window !== 'undefined' && !window.__teasmartParityLoaded) {
  window.__teasmartParityLoaded = true;
  window.runParity = runParity;
}
