import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { ResultCard } from './ResultCard';
import { scanFixture } from '../test/fixtures';

it('orders Thai disease, severity, verdict and advice, and labels the producing mode', () => {
  render(<ResultCard result={scanFixture()} />);
  const card = screen.getByRole('article');
  const content = card.textContent!;
  expect(content.indexOf('โรคใบไหม้เทา')).toBeLessThan(content.indexOf('ปานกลาง'));
  expect(content.indexOf('ปานกลาง')).toBeLessThan(content.indexOf('เกิดจากโรค'));
  expect(content.indexOf('เกิดจากโรค')).toBeLessThan(content.indexOf('คำแนะนำจากระบบ'));
  expect(screen.getByText(/วิเคราะห์ครบขั้นตอนจากเซิร์ฟเวอร์/)).toBeInTheDocument();
  expect(screen.getByText(/12/)).toBeInTheDocument();
});

it('suppresses disease identity and unsafe chemical advice when the verdict is physical burn', () => {
  render(<ResultCard result={scanFixture({
    burn_analysis: { ...scanFixture().burn_analysis, verdict: 'physical_burn', burn_likelihood: 0.9 },
  })} knowledge={{ canonical: 'grey_blight', disease_name_th: 'โรคใบไหม้เทา',
    class_id: 0, class_name: 'Grey blight', pathogen: '', symptoms: '',
    immediate_action: 'ฉีดพ่นยา', cultural_control: '', chemical_treatment: 'ฉีดพ่นยา', preventive_measures: '' }} />);
  expect(screen.getByRole('heading', { name: 'อาการไหม้จากปัจจัยทางกายภาพ' })).toBeInTheDocument();
  expect(screen.getByText(/ไม่แนะนำให้ฉีดพ่น/)).toBeInTheDocument();
  expect(screen.queryByText('ฉีดพ่นยา')).not.toBeInTheDocument();
});
