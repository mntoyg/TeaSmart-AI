import { expect, it } from 'vitest';
import { buildResultView } from './result-view';
import { knowledgeFixture } from '../test/kb-fixture';
import { scanFixture } from '../test/fixtures';
import { localFixture } from '../test/local-fixture';

const knowledge = knowledgeFixture();

it('dresses a server result in the record the knowledge base serves', () => {
  const view = buildResultView(scanFixture(), knowledge);

  expect(view?.analysisMode).toBe('full');
  expect(view?.verdict).toBe('disease');
  expect(view?.severity).toEqual({ level: 'moderate', affectedPct: 0.12 });
  expect(view?.prediction.disease.nameTh).toBe('โรคใบไหม้เทา');
  expect(view?.prediction.disease.pathogen).toBe('Pestalotiopsis theae');
  expect(view?.prediction.isDemo).toBe(false);
  expect(view?.prediction.status).toBe('ok');
});

it('prefers the advice the server sent with the scan over the cached record', () => {
  // The server ran the whole pipeline over this photograph; the cached record is
  // the general case. Where both describe the same disease, the specific one wins.
  const view = buildResultView(scanFixture(), knowledge);
  expect(view?.prediction.disease.immediateAction).toBe('คำแนะนำจากระบบ');
});

it('answers with the burn record, never the disease the classifier named', () => {
  const burnt = scanFixture({
    burn_analysis: { ...scanFixture().burn_analysis, verdict: 'physical_burn', burn_likelihood: 0.9 },
  });

  const view = buildResultView(burnt, knowledge);

  expect(view?.verdict).toBe('physical_burn');
  expect(view?.prediction.disease.classId).toBe(5);
  expect(view?.prediction.disease.nameTh).toBe('รอยไหม้ทางกายภาพ (แดดเผา / สารเคมี)');
  // The scan said grey blight and carried grey blight advice. Neither may survive.
  expect(JSON.stringify(view?.prediction.disease)).not.toContain('ใบไหม้เทา');
  expect(JSON.stringify(view?.prediction.disease)).not.toContain('คำแนะนำจากระบบ');
});

it('keeps a device result classifier-only, with no verdict and no severity to show', () => {
  const view = buildResultView(localFixture(), knowledge);

  expect(view?.analysisMode).toBe('classifier_only');
  expect(view?.verdict).toBeUndefined();
  expect(view?.severity).toBeUndefined();
  expect(view?.prediction.disease.nameTh).toBe('โรคใบไหม้เทา');
});

it('marks a low-confidence answer uncertain and ranks what else it could be', () => {
  const unsure = scanFixture({
    prediction: { ...scanFixture().prediction, low_confidence: true },
  });

  const view = buildResultView(unsure, knowledge);

  expect(view?.prediction.status).toBe('uncertain');
  expect(view?.prediction.candidates.map((candidate) => candidate.disease.nameTh))
    .toEqual(['โรคใบไหม้เทา', 'โรคใบไหม้น้ำตาล']);
});

it('still shows a server result that arrived before the knowledge base was cached', () => {
  // A full scan carries its own advice, so it does not need the cache to be
  // readable. What it cannot supply is pathogen and symptoms, and the screen
  // leaves those out rather than printing an empty label.
  const view = buildResultView(scanFixture(), []);

  expect(view?.prediction.disease.nameTh).toBe('โรคใบไหม้เทา');
  expect(view?.prediction.disease.immediateAction).toBe('คำแนะนำจากระบบ');
  expect(view?.prediction.disease.pathogen).toBe('');
  expect(view?.prediction.disease.symptoms).toBe('');
});

it('has nothing to show when a device result meets an empty knowledge base', () => {
  // Classifier-only output is a class name and a number. Without the records
  // there is no advice to give, and inventing one is the failure to avoid.
  expect(buildResultView(localFixture(), [])).toBeUndefined();
});
