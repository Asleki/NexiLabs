import test from "node:test";
import assert from "node:assert/strict";
import { loadPartial, ShellPartial } from "../../../src/app/shell/partial-loader.js";

test("P006.UI.1 shared header/footer partials load into shell slots", async () => {
  const slot = { innerHTML: "", dataset: {} };
  const documentRef = { querySelector: () => slot };
  const fetchRef = async () => ({ ok: true, async text() { return "<header>Shared</header>"; } });
  const receipt = await loadPartial({ documentRef, fetchRef, descriptor: ShellPartial.HEADER });
  assert.equal(receipt.ready, true);
  assert.equal(slot.dataset.partialReady, "true");
  assert.match(slot.innerHTML, /Shared/);
});

test("Bundle 12.0C bounds a stalled partial fetch instead of leaving the application in BOOTING", async () => {
  const slot = { innerHTML: "", dataset: {} };
  const documentRef = { querySelector: () => slot };
  const fetchRef = () => new Promise(() => {});
  await assert.rejects(
    loadPartial({ documentRef, fetchRef, descriptor: ShellPartial.HEADER, timeoutMs: 20 }),
    /Timed out loading shell partial/,
  );
  assert.notEqual(slot.dataset.partialReady, "true");
});

test("successful partial insertion announces shell chrome availability", async () => {
  const slot = { innerHTML: "", dataset: {} };
  const events = [];
  const documentRef = {
    querySelector: () => slot,
    dispatchEvent(event) { events.push(event.type); return true; },
  };
  const fetchRef = async () => ({
    ok: true,
    async text() { return "<footer>Shared</footer>"; },
  });

  await loadPartial({
    documentRef,
    fetchRef,
    descriptor: ShellPartial.FOOTER,
  });

  assert.deepEqual(events, ["nexilabs:shell-partial-loaded"]);
});
