/** P006.UI.10/P006.UI.14 — Production Developer Workspace and separated developer diagnostics. */
import { ApplicationRoute } from "../../app/navigation/application-route.js";
import { DEVELOPER_CAPABILITIES, CapabilityAvailability } from "../../app/workspaces/workspace-capabilities.js";

function esc(value) {
  return String(value ?? "").replace(/[&<>\"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function capabilityCard(item) {
  const available = item.availability === CapabilityAvailability.AVAILABLE;
  const action = available && item.route === "production-novegeo"
    ? `<button class="workspace-action" type="button" data-route="${ApplicationRoute.PRODUCTION_NOVEGEO}">Open NoveGeo</button>`
    : `<span class="workspace-status" data-availability="${item.availability}">${item.availability}</span>`;
  return `<article class="workspace-capability-card" data-capability="${item.id}">
    <div><h2>${esc(item.title)}</h2><p>${esc(item.description)}</p></div>${action}
  </article>`;
}

export function productionDeveloperWorkspaceMarkup(session) {
  return `
    <section class="workspace-page" aria-labelledby="developer-workspace-title">
      <header class="workspace-heading workspace-heading-with-actions">
        <div class="workspace-heading-copy">
          <p class="eyebrow">Production · NexaDevs</p>
          <h1 id="developer-workspace-title">Production Developer Workspace</h1>
          <p class="summary">Governed supervision and production-system access. This is not a raw PostgreSQL administration console.</p>
        </div>
        <div class="workspace-heading-actions" data-role="developer-admin-actions" aria-label="Developer workspace actions"></div>
      </header>

      <section class="workspace-section" aria-labelledby="developer-systems-title">
        <div class="workspace-section-heading"><p class="section-kicker">Systems</p><h2 id="developer-systems-title">Available and reserved capabilities</h2></div>
        <div class="workspace-capability-grid">${DEVELOPER_CAPABILITIES.map(capabilityCard).join("")}</div>
      </section>

      <section class="workspace-section workspace-identity" aria-labelledby="developer-access-title">
        <div class="workspace-section-heading"><p class="section-kicker">Access</p><h2 id="developer-access-title">Developer context</h2></div>
        <dl class="workspace-facts">
          <div><dt>Principal</dt><dd>${esc(session?.principalId)}</dd></div>
          <div><dt>Runtime</dt><dd>${esc(session?.runtime || "production")}</dd></div>
          <div><dt>Authentication</dt><dd>${esc(session?.authenticationStrength)}</dd></div>
          <div><dt>Session</dt><dd>Active</dd></div>
        </dl>
      </section>

      <section class="workspace-section developer-diagnostics" data-role="developer-diagnostics" aria-labelledby="developer-diagnostics-title">
        <div class="workspace-section-heading"><p class="section-kicker">Developer diagnostics</p><h2 id="developer-diagnostics-title">Platform boundary</h2></div>
        <dl class="workspace-facts">
          <div><dt>Hosted API</dt><dd>Not connected in this browser workspace</dd></div>
          <div><dt>PostgreSQL</dt><dd>Server-side authority only</dd></div>
          <div><dt>Name Catalogue</dt><dd>Foundation ready; browser read interface deferred</dd></div>
          <div><dt>Secrets</dt><dd>Never exposed to the browser</dd></div>
        </dl>
      </section>

      <div class="workspace-terminal-actions">
        <button class="workspace-signout-button" type="button" data-auth-action="logout">Sign out</button>
      </div>
    </section>`;
}
