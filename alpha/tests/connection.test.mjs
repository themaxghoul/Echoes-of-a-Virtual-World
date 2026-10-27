import test from 'node:test';
import assert from 'node:assert/strict';
import {snapshotFresh} from '../../docs/play/connection.js';
test('missing and stale snapshots disable a seemingly open connection',()=>{
  assert.equal(snapshotFresh(0,100),false);
  assert.equal(snapshotFresh(1000,1100),true);
  assert.equal(snapshotFresh(1000,7001),false);
});
