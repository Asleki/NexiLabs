/** P006.UI.10.4 — Separate Admin credential and Enigma views inside Production. */
function esc(value) {
  return String(value ?? "").replace(/[&<>\"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

export function adminLoginMarkup({ eligibility, error = "" } = {}) {
  return `<section class="entry-page auth-page admin-auth-page" data-role="admin-auth-boundary" data-admin-auth-step="credentials" aria-labelledby="admin-login-title">
    <p class="eyebrow">Production · Admin Access</p>
    <p class="section-kicker">Admin elevation · Layer 1</p>
    <h1 id="admin-login-title">Admin sign in</h1>
    <p class="summary">Confirm the separately governed Admin credentials bound to this eligible Developer identity.</p>

    ${eligibility?.boundEmailHint ? `
      <div class="admin-bound-identity">
        <span>Bound Admin</span>
        <strong>${esc(eligibility.boundEmailHint)}</strong>
      </div>` : ""}

    <form class="auth-form admin-auth-form" data-admin-auth-form="elevate" autocomplete="off">
      <label>Admin email<input name="adminEmail" type="email" autocomplete="username" required></label>
      <label>Separate Admin password<input name="adminPassword" type="password" autocomplete="current-password" required></label>
      ${error ? `<p class="auth-message auth-message-error" role="alert">${esc(error)}</p>` : ""}
      <button class="primary-button" type="submit">Continue to Admin Enigma</button>
    </form>

    <div class="auth-page-actions">
      <button class="text-button" type="button" data-admin-auth-action="back-developer">← Back to Developer Workspace</button>
    </div>
    <button class="workspace-signout-button admin-signout-button" type="button" data-auth-action="logout">Sign out</button>
  </section>`;
}

export function adminEnigmaMarkup({ challenge, error = "" } = {}) {
  const words = (challenge?.words || []).map((value) => `<strong>${esc(value)}</strong>`).join("");
  return `<section class="entry-page auth-page admin-auth-page" data-role="admin-auth-boundary" data-admin-auth-step="enigma" aria-labelledby="admin-enigma-title">
    <p class="eyebrow">Production · Admin Access</p>
    <p class="section-kicker">Admin elevation · Layer 2</p>
    <h1 id="admin-enigma-title">Admin Enigma</h1>
    <p class="summary">Secondary authority verification. Use the governed lookup method with your separate Admin bootstrap Enigma secret.</p>

    <div class="enigma-challenge admin-enigma-challenge" aria-label="Admin Enigma challenge words">${words}</div>
    <p class="enigma-meta">${esc(challenge?.period || "")} · ${esc(challenge?.wordLength || "")}-letter challenge</p>

    <form class="auth-form admin-auth-form" data-admin-auth-form="enigma" autocomplete="off">
      <label>Admin Enigma response<input name="response" type="password" autocomplete="off" autocapitalize="characters" spellcheck="false" required></label>
      ${error ? `<p class="auth-message auth-message-error" role="alert">${esc(error)}</p>` : ""}
      <button class="primary-button" type="submit">Verify &amp; elevate</button>
    </form>

    <div class="auth-page-actions">
      <button class="text-button" type="button" data-admin-auth-action="back-credentials">← Back to Admin credentials</button>
    </div>
    <button class="workspace-signout-button admin-signout-button" type="button" data-auth-action="logout">Sign out</button>
  </section>`;
}

/* Preserved predecessor presentation helper for P006.UI.10.3 compatibility tests. */
export function adminElevatedMarkup({ elevation } = {}) {
  const permissions = (elevation?.permissions || []).map((value) => `<li>${esc(value)}</li>`).join("");
  return `<section class="workspace-section" data-role="admin-auth-boundary" aria-labelledby="admin-elevated-title">
    <div class="workspace-section-heading"><p class="section-kicker">Admin elevation</p><h2 id="admin-elevated-title">Elevated Admin context</h2></div>
    <dl class="workspace-facts">
      <div><dt>Admin Operator</dt><dd>${esc(elevation?.adminOperatorId)}</dd></div>
      <div><dt>Expires</dt><dd>${esc(elevation?.expiresAt)}</dd></div>
      <div><dt>Elevation</dt><dd>Active · volatile browser context</dd></div>
    </dl>
    <p>Exact active permissions:</p><ul>${permissions}</ul>
    <button class="text-button" type="button" data-admin-auth-action="revoke">Leave Admin context</button>
  </section>`;
}
