import { expect, it } from 'vitest';
import { inferOffline } from './offline';
import { configShape } from './scan-contract';
it('refuses offline inference without a validated cached config', async () => {
  await expect(inferOffline(new File(['leaf'], 'leaf.jpg'), crypto.randomUUID(), new Date().toISOString(), undefined))
    .rejects.toThrow('การตั้งค่า');
});
