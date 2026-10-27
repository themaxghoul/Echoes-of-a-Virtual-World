const { test } = require('node:test');
const assert = require('node:assert/strict');
const { shouldToggleChat } = require('./gameShortcuts.cjs');

test('T toggles chat when the map has keyboard focus', () => {
  assert.equal(shouldToggleChat({ key: 't', target: { tagName: 'CANVAS' } }), true);
});

test('T remains text in inputs and editable surfaces', () => {
  for (const target of [
    { tagName: 'INPUT' },
    { tagName: 'TEXTAREA' },
    { tagName: 'SELECT' },
    { tagName: 'BUTTON' },
    { tagName: 'DIV', isContentEditable: true },
  ]) {
    assert.equal(shouldToggleChat({ key: 't', target }), false);
  }
});

test('modified T shortcuts do not collide with browser and assistive shortcuts', () => {
  for (const modifier of ['altKey', 'ctrlKey', 'metaKey', 'shiftKey']) {
    assert.equal(shouldToggleChat({ key: 't', target: { tagName: 'CANVAS' }, [modifier]: true }), false);
  }
  assert.equal(shouldToggleChat({ key: 'w', target: { tagName: 'CANVAS' } }), false);
});
