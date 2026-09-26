import assert from "node:assert/strict";
import test from "node:test";

import {
  developerAccessRequestMarkup,
  developerRegistrationMarkup,
  developerSetupVerificationMarkup,
} from "../../src/ui/pages/developer-account-enrollment-p006-ui-10-4.js";

test("successor Developer request remains identity-only and frontend-only", () => {
  const html = developerAccessRequestMarkup();
  assert.match(html, /name="firstName"/);
  assert.match(html, /name="lastName"/);
  assert.match(html, /name="email"/);
  assert.match(html, /data-account-foundation-only="true"/);
  assert.doesNotMatch(html, /name="password"/);
});

test("successor Developer Setup verification remains distinct from credential registration", () => {
  const html = developerSetupVerificationMarkup();
  assert.match(html, /name="developerSetupId"/);
  assert.doesNotMatch(html, /name="username"|name="password"/);
});

test("P006.UI.10.4 registration removes DOB/profile enrichment but preserves credential presentation", () => {
  const html = developerRegistrationMarkup();
  assert.match(html, /name="developerSetupId"[^>]*readonly/);
  assert.match(html, /name="approvedName"[^>]*readonly/);
  assert.match(html, /name="approvedEmail"[^>]*readonly/);
  assert.match(html, /name="username"/);
  assert.match(html, /name="password"/);
  assert.match(html, /name="confirmPassword"/);
  assert.doesNotMatch(html, /name="dateOfBirth"|autocomplete="bday"/);
  assert.match(html, /date of birth and address are deliberately deferred/i);
  assert.match(html, /does not submit|No username or password is stored/i);
});

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

test("account enrollment experience routes Developer registration through the P006.UI.10.4 successor without adding an API", () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const source = readFileSync(resolve(root, "src/app/account/account-enrollment-experience.js"), "utf8");
  assert.match(source, /developer-account-enrollment-p006-ui-10-4\.js/);
  assert.doesNotMatch(source, /\bfetch\s*\(/);
  assert.doesNotMatch(source, /localStorage|sessionStorage/);
});
