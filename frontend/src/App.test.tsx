import 'fake-indexeddb/auto';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import { store } from './lib/storage';
import { scanFixture } from './test/fixtures';

it('loads a persisted result by its URL after refresh', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  await store.save(scanFixture());
  render(<MemoryRouter initialEntries={[`/result/${scanFixture().scan_id}`]}><App /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'โรคใบไหม้เทา' })).toBeInTheDocument();
  vi.unstubAllGlobals();
});
it('offers a scan link when a result ID is absent', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  render(<MemoryRouter initialEntries={['/result/missing']}><App /></MemoryRouter>);
  expect(await screen.findByText('ไม่พบผลตรวจนี้ในอุปกรณ์')).toBeInTheDocument();
  expect(screen.getAllByRole('link', { name: 'ตรวจใบชา' })[0]).toHaveAttribute('href', '/scan');
  vi.unstubAllGlobals();
});
