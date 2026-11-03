import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import DiagnosisResult from './DiagnosisResult';
import { buildResultView } from '../lib/result-view';
import { knowledgeFixture } from '../test/kb-fixture';
import { scanFixture } from '../test/fixtures';
import { localFixture } from '../test/local-fixture';
import { configShape } from '../lib/scan-contract';
import type { StoredResult } from '../lib/local-result';

const knowledge = knowledgeFixture();

function show(result: StoredResult) {
  const view = buildResultView(result, knowledge)!;
  expect(view).toBeDefined();
  return render(
    <DiagnosisResult
      result={view.prediction}
      analysisMode={view.analysisMode}
      verdict={view.verdict}
      severity={view.severity}
      confidenceMin={configShape.min_confidence}
      onScanAgain={vi.fn()}
      onOpenKnowledge={vi.fn()}
    />,
  );
}

function predicted(canonical: string) {
  return scanFixture({
    prediction: { ...scanFixture().prediction, class_name: canonical, top_k: [] },
    advice: { ...scanFixture().advice, canonical },
  });
}

it('shows every record the knowledge base serves, including the two the classifier never outputs', () => {
  for (const record of knowledge) {
    const result = record.canonical === 'physical_burn'
      ? scanFixture({ burn_analysis: { ...scanFixture().burn_analysis, verdict: 'physical_burn' } })
      : predicted(record.canonical);
    const { unmount } = show(result);
    expect(screen.getByRole('heading', { name: record.disease_name_th })).toBeInTheDocument();
    unmount();
  }
});

it('never presents other_disease as a disease it has named', () => {
  // The record exists so the product can say "something is wrong and it is not
  // one of the three", instead of naming the nearest of the three confidently.
  show(predicted('other_disease'));

  expect(screen.getByRole('heading', { name: 'ความผิดปกติอื่น ๆ (ไม่ตรงโรคหลัก)' })).toBeInTheDocument();
  for (const named of ['โรคใบไหม้เทา', 'โรคใบไหม้น้ำตาล', 'โรคจุดสาหร่าย / สนิมสาหร่าย']) {
    expect(screen.queryByText(new RegExp(named))).not.toBeInTheDocument();
  }
});

it('says which mode produced the answer, on a server result and on a device one', () => {
  // docs/DESIGN.md section 8.1: the result card must always state the mode, so
  // nobody reads a device answer as the full six-stage pipeline.
  const { unmount } = show(scanFixture());
  expect(screen.getByText(/วิเคราะห์ครบขั้นตอนจากเซิร์ฟเวอร์/)).toBeInTheDocument();
  unmount();

  show(localFixture());
  expect(screen.getByText(/จำแนกโรคเท่านั้น/)).toBeInTheDocument();
});

it('shows measured severity for a server result and invents none for a device one', () => {
  const { unmount } = show(scanFixture());
  expect(screen.getByText(/ความรุนแรง ปานกลาง/)).toBeInTheDocument();
  expect(screen.getByText(/12%/)).toBeInTheDocument();
  unmount();

  show(localFixture());
  // Saying the severity stage has not run yet is not the same as naming a level.
  expect(screen.queryByText(/ความรุนแรง (เล็กน้อย|ปานกลาง|รุนแรง)/)).not.toBeInTheDocument();
  expect(screen.queryByText(/พื้นที่เสียหาย/)).not.toBeInTheDocument();
});

it('suppresses the disease the classifier named when the verdict is physical burn', () => {
  show(scanFixture({
    burn_analysis: { ...scanFixture().burn_analysis, verdict: 'physical_burn', burn_likelihood: 0.9 },
  }));

  expect(screen.getByRole('heading', { name: 'รอยไหม้ทางกายภาพ (แดดเผา / สารเคมี)' })).toBeInTheDocument();
  expect(screen.queryByText(/ใบไหม้เทา/)).not.toBeInTheDocument();
  expect(screen.getByText(/ไม่ต้องฉีดพ่นสารป้องกันกำจัดโรคพืชจากผลนี้/)).toBeInTheDocument();
});

it('offers no spray advice on a device result, because no stage decided burn or disease', () => {
  show(localFixture());

  expect(screen.getByText(/ยังแยกโรคกับแผลไหม้ไม่ได้/)).toBeInTheDocument();
  expect(screen.getByText(/รอการวิเคราะห์ครบขั้นตอนก่อนพิจารณาการใช้สารป้องกันกำจัด/)).toBeInTheDocument();
  expect(screen.queryByText(/การใช้สารสำหรับ/)).not.toBeInTheDocument();
});

it('quotes the threshold from the config rather than a number of its own', () => {
  show(scanFixture({ prediction: { ...scanFixture().prediction, low_confidence: true } }));

  expect(screen.getByText(/ต่ำกว่าเกณฑ์ 60%/)).toBeInTheDocument();
});
