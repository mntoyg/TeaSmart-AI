import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import KnowledgePanel from './KnowledgePanel';
import { knowledgeFixture } from '../test/kb-fixture';
import { toDisease } from '../lib/result-view';

const diseases = () => knowledgeFixture().map((record) => toDisease(record, record));

it('counts the records it was handed, not the four the design was drawn with', () => {
  render(<KnowledgePanel diseases={diseases()} />);
  expect(screen.getByText('6 ระเบียนในคลังความรู้')).toBeInTheDocument();
  expect(screen.getByText('06')).toBeInTheDocument();
  expect(screen.queryByText(/4 คลาสสำหรับต้นแบบ/)).not.toBeInTheDocument();
  expect(screen.queryByText('04')).not.toBeInTheDocument();
});

it('counts three diseases, because the burn verdict is not one of them', () => {
  render(<KnowledgePanel diseases={diseases()} />);
  const summary = screen.getByText(/โรคหลักสามชนิด/);
  expect(summary).toHaveTextContent('รอยไหม้ทางกายภาพซึ่งเป็นคำตัดสิน ไม่ใช่โรค');
  expect(screen.queryByText(/โรคใบชา 3 คลาส และใบสุขภาพดี 1 คลาส/)).not.toBeInTheDocument();
});

it('gives every record a card of its own', () => {
  render(<KnowledgePanel diseases={diseases()} />);
  for (const record of knowledgeFixture()) {
    expect(screen.getByText(record.disease_name_th)).toBeInTheDocument();
  }
});

it('reads a record with four records as well, which is what a smaller base would serve', () => {
  render(<KnowledgePanel diseases={diseases().slice(0, 4)} />);
  expect(screen.getByText('4 ระเบียนในคลังความรู้')).toBeInTheDocument();
  expect(screen.getByText('04')).toBeInTheDocument();
});
