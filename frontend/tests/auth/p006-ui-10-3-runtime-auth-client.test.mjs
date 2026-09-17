import assert from "node:assert/strict";
import test from "node:test";

import { createRuntimeAuthClient } from "../../src/app/auth/runtime-auth-client.js";

function response(payload, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload };
}

test("Production Developer Layer 1 is routed to port 8767", async () => {
  const urls = [];
  const client = createRuntimeAuthClient({
    windowRef: { location: { hostname: "127.0.0.1" } },
    fetchRef: async (url) => {
      urls.push(url);
      return response({ ok: true, attemptId: "a", challenge: {} });
    },
  });
  await client.startDeveloper({ username: "alex", password: "pw", runtime: "production" });
  assert.equal(urls[0], "http://127.0.0.1:8767/auth/developer/start");
});


test("Guest auth remains on locked development authority in 10.3", async () => {
  const urls = [];
  const client = createRuntimeAuthClient({
    windowRef: { location: { hostname: "127.0.0.1" } },
    fetchRef: async (url) => {
      urls.push(url);
      return response({ ok: true, session: {} });
    },
  });
  await client.loginGuest({ username: "guest", password: "pw", runtime: "production" });
  assert.equal(urls[0], "http://127.0.0.1:8766/auth/guest/login");
});
