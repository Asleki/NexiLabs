/** P006.UI.10.3 R2 — Conditional Admin elevation inside Production. */
function esc(value) {
  return String(value ?? "").replace(/[&<>\"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

export function adminLoginMarkup({ eligibility, error = "" } = {}) {
  return `<section class="workspace-section" data-role="admin-auth-boundary" aria-labelledby="admin-login-title">
    <div class="workspace-section-heading">
      <p class="section-kicker">Admin elevation</p>
      <h2 id="admin-login-title">Admin Login</h2>
    </div>
    <p class="summary">This authenticated Developer identity is Admin-eligible. Continue with the bound Admin email and <strong>separate Admin password</strong>.</p>
    ${eligibility?.boundEmailHint ? `<p class="workspace-status">Bound email: ${esc(eligibility.boundEmailHint)}</p>` : ""}
    ${error ? `<p class="form-error" role="alert">${esc(error)}</p>` : ""}
    <form data-admin-auth-form="elevate" autocomplete="off">
      <label>Admin email<input name="adminEmail" type="email" autocomplete="username" required></label>
      <label>Separate Admin password<input name="adminPassword" type="password" autocomplete="current-password" required></label>
      <button class="primary-button" type="submit">Continue Admin Login</button>
    </form>
  </section>`;
}

export function adminEnigmaMarkup({ challenge, error = "" } = {}) {
  const words = (challenge?.words || []).map((value) => `<strong>${esc(value)}</strong>`).join(" &nbsp; ");
  return `<section class="workspace-section" data-role="admin-auth-boundary" aria-labelledby="admin-enigma-title">
    <div class="workspace-section-heading">
      <p class="section-kicker">Admin elevation</p>
      <h2 id="admin-enigma-title">Admin Enigma</h2>
    </div>
    <p class="summary">Use the same governed lookup method with the Admin bootstrap Enigma secret.</p>
    <p class="workspace-status">${words}</p>
    <p class="workspace-status">${esc(challenge?.period || "")} · ${esc(challenge?.wordLength || "")}‑letter challenge</p>
    ${error ? `<p class="form-error" role="alert">${esc(error)}</p>` : ""}
    <form data-admin-auth-form="enigma" autocomplete="off">
      <label>Admin Enigma response<input name="response" type="password" autocomplete="off" required></label>
      <button class="primary-button" type="submit">Elevate Admin</button>
    </form>
  </section>`;
}

export function adminElevatedMarkup({ elevation } = {}) {
  const permissions = (elevation?.permissions || []).map((value) => `<li>${esc(value)}</li>`).join("");
  return `<section class="workspace-section" data-role="admin-auth-boundary" aria-labelledby="admin-elevated-title">
    <div class="workspace-section-heading">
      <p class="section-kicker">Admin elevation</p>
      <h2 id="admin-elevated-title">Elevated Admin context</h2>
    </div>
    <dl class="workspace-facts">
      <div><dt>Admin Operator</dt><dd>${esc(elevation?.adminOperatorId)}</dd></div>
      <div><dt>Expires</dt><dd>${esc(elevation?.expiresAt)}</dd></div>
      <div><dt>Elevation</dt><dd>Active · volatile browser context</dd></div>
    </dl>
    <p>Exact active permissions:</p><ul>${permissions}</ul>
    <button class="text-button" type="button" data-admin-auth-action="revoke">Leave Admin context</button>
  </section>`;
}
