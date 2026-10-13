import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { ResultCard } from './ResultCard';
import { localFixture } from '../test/local-fixture';

it('never invents severity, burn verdict or spray advice for classifier-only output', () => {
  render(<ResultCard result={localFixture()} />);
  expect(screen.getByText(/จำแนกโรคเท่านั้น/)).toBeInTheDocument();
  expect(screen.getByText(/ยังแยกโรคกับแผลไหม้ไม่ได้/)).toBeInTheDocument();
  expect(screen.getByText(/รอการวิเคราะห์เพิ่มเติม/, { selector: '.severity' })).toBeInTheDocument();
  expect(screen.queryByText('เกิดจากโรค')).not.toBeInTheDocument();
});
