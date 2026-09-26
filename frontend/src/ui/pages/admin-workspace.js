/** P006.UI.10.4 — Guarded elevated Admin Workspace presentation. */
import {
  AdminReviewStatus,
  AdminReviewUiState,
  createUnavailableAdminReviewView,
} from "../../app/admin/admin-review-view-model.js";

export const AdminWorkspaceSection = Object.freeze({
  OVERVIEW: "overview",
  REVIEWS: "reviews",
  DEVELOPER_ACCESS: "developer-access",
  ENIGMA_GOVERNANCE: "enigma-governance",
  AUDIT: "audit",
  ADMIN_SESSION: "admin-session",
});

const SECTION_LABELS = Object.freeze({
  [AdminWorkspaceSection.OVERVIEW]: "Overview",
  [AdminWorkspaceSection.REVIEWS]: "Reviews",
  [AdminWorkspaceSection.DEVELOPER_ACCESS]: "Developer Access",
  [AdminWorkspaceSection.ENIGMA_GOVERNANCE]: "Enigma Governance",
  [AdminWorkspaceSection.AUDIT]: "Audit",
  [AdminWorkspaceSection.ADMIN_SESSION]: "Admin Session",
});

const REVIEW_LABELS = Object.freeze({
  [AdminReviewStatus.PENDING]: "Pending",
  [AdminReviewStatus.UNDER_REVIEW]: "Under Review",
  [AdminReviewStatus.APPROVED]: "Approved",
  [AdminReviewStatus.REJECTED]: "Rejected",
});

function esc(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function nav(activeSection) {
  return `<nav class="workspace-inline-nav" aria-label="Admin Workspace sections">${Object.entries(SECTION_LABELS).map(([id, label]) =>
    `<button class="text-button" type="button" data-admin-workspace-section="${id}" aria-current="${activeSection === id ? "page" : "false"}">${label}</button>`
  ).join("")}</nav>`;
}

function statusTabs(activeStatus) {
  return `<div class="workspace-inline-nav" role="tablist" aria-label="Review states">${Object.entries(REVIEW_LABELS).map(([status, label]) =>
    `<button class="text-button" type="button" role="tab" data-admin-review-status="${status}" aria-selected="${activeStatus === status}">${label}</button>`
  ).join("")}</div>`;
}

function reviewState(view) {
  if (view.state === AdminReviewUiState.LOADING) return `<p class="workspace-status" role="status">Loading Developer reviews…</p>`;
  if (view.state === AdminReviewUiState.EMPTY) return `<p class="workspace-status">No ${esc(REVIEW_LABELS[view.status]).toLowerCase()} Developer access reviews.</p>`;
  if (view.state === AdminReviewUiState.DENIED) return `<p class="form-error" role="alert">Your elevated Admin context does not have permission to read Developer reviews.</p>`;
  if (view.state === AdminReviewUiState.STALE) return `<p class="form-error" role="alert">This review changed after it was loaded. Refresh from the live authority before deciding.</p>`;
  if (view.state === AdminReviewUiState.ERROR) return `<p class="form-error" role="alert">${esc(view.message || "Developer Reviews could not be loaded.")}</p>`;
  if (view.state === AdminReviewUiState.SERVICE_UNAVAILABLE) return `<p class="workspace-status" role="status">${esc(view.message)}</p>`;
  return "";
}

function reviewList(view) {
  if (!view.records.length) return reviewState(view);
  return `<div class="workspace-capability-grid" data-admin-review-list>${view.records.map((record) => `
    <article class="workspace-capability-card" data-review-request="${esc(record.requestReference)}">
      <div><h3>${esc(record.requestReference)}</h3><p>${esc(record.applicantName || "Applicant identity withheld")}</p><p>${esc(record.applicantEmail || "Email withheld")}</p></div>
      <span class="workspace-status">${esc(REVIEW_LABELS[record.status])}</span>
    </article>`).join("")}</div>`;
}

function reviewDetail(view) {
  const record = view.selected;
  if (!record) return `<section class="workspace-section" aria-labelledby="review-detail-title"><h3 id="review-detail-title">Review detail</h3><p class="workspace-status">Select a live review when the Review API is connected.</p></section>`;
  const disabled = view.decisionAuthorityAvailable ? "" : ' disabled aria-disabled="true"';
  return `<section class="workspace-section" aria-labelledby="review-detail-title">
    <h3 id="review-detail-title">Review detail</h3>
    <dl class="workspace-facts">
      <div><dt>Request</dt><dd>${esc(record.requestReference)}</dd></div>
      <div><dt>Applicant</dt><dd>${esc(record.applicantName)}</dd></div>
      <div><dt>Email</dt><dd>${esc(record.applicantEmail)}</dd></div>
      <div><dt>Submitted</dt><dd>${esc(record.submittedAt)}</dd></div>
      <div><dt>Last updated</dt><dd>${esc(record.updatedAt)}</dd></div>
      <div><dt>State</dt><dd>${esc(REVIEW_LABELS[record.status])}</dd></div>
    </dl>
    <form data-admin-review-decision-form>
      <label>Decision reason<textarea name="reason" required></textarea></label>
      <label>Safe applicant explanation<textarea name="applicantExplanation" required></textarea></label>
      <label><input name="confirmDecision" type="checkbox" required> I confirm the decision details are correct.</label>
      <div class="account-inline-actions">
        <button class="primary-button" type="button" data-admin-review-decision="approve"${disabled}>Approve</button>
        <button class="secondary-button" type="button" data-admin-review-decision="reject"${disabled}>Reject</button>
      </div>
    </form>
    ${view.decisionAuthorityAvailable ? "" : `<p class="workspace-status">Decision authority unavailable — controls remain disabled until a governed Review API is connected.</p>`}
    <section aria-labelledby="review-history-title"><h4 id="review-history-title">History</h4><p class="workspace-status">A live authority timeline will appear here; no history is fabricated locally.</p></section>
  </section>`;
}

function reviewsSection(reviewView) {
  return `<section class="workspace-section" data-admin-workspace-panel="reviews" aria-labelledby="admin-reviews-title">
    <div class="workspace-section-heading"><p class="section-kicker">Governed queue</p><h2 id="admin-reviews-title">Reviews</h2></div>
    ${statusTabs(reviewView.status)}
    <div class="account-field-grid">
      <label>Search reviews<input type="search" data-admin-review-search placeholder="Request, applicant or email" autocomplete="off"></label>
      <label>Sort<select data-admin-review-sort><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="updated">Recently updated</option></select></label>
    </div>
    ${reviewList(reviewView)}
    ${reviewDetail(reviewView)}
  </section>`;
}

function sessionFacts(elevation) {
  const permissions = (elevation?.permissions || []).map((permission) => `<li>${esc(permission)}</li>`).join("");
  return `<dl class="workspace-facts">
    <div><dt>Admin Operator</dt><dd>${esc(elevation?.adminOperatorId)}</dd></div>
    <div><dt>Expires</dt><dd>${esc(elevation?.expiresAt)}</dd></div>
    <div><dt>Elevation</dt><dd>Active · volatile browser context</dd></div>
  </dl><p>Exact active permissions:</p><ul>${permissions}</ul>`;
}

function panel(activeSection, elevation, reviewView) {
  if (activeSection === AdminWorkspaceSection.REVIEWS) return reviewsSection(reviewView);
  if (activeSection === AdminWorkspaceSection.DEVELOPER_ACCESS) return `<section class="workspace-section" data-admin-workspace-panel="developer-access"><div class="workspace-section-heading"><p class="section-kicker">Enrollment</p><h2>Developer Access</h2></div><p class="summary">Developer request, Setup issuance and account activation authority remain deferred. This Admin surface does not fabricate applicant or approval state.</p></section>`;
  if (activeSection === AdminWorkspaceSection.ENIGMA_GOVERNANCE) return `<section class="workspace-section" data-admin-workspace-panel="enigma-governance"><div class="workspace-section-heading"><p class="section-kicker">Credential governance</p><h2>Enigma Governance</h2></div><p class="summary">Catalogue and profile governance remains server-side. Enigma secrets and private catalogue material are never exposed to the browser.</p></section>`;
  if (activeSection === AdminWorkspaceSection.AUDIT) return `<section class="workspace-section" data-admin-workspace-panel="audit"><div class="workspace-section-heading"><p class="section-kicker">Authority evidence</p><h2>Audit</h2></div><p class="summary">Runtime authentication already emits governed audit events. Browser audit retrieval is not connected in this milestone and no audit rows are fabricated.</p></section>`;
  if (activeSection === AdminWorkspaceSection.ADMIN_SESSION) return `<section class="workspace-section" data-admin-workspace-panel="admin-session"><div class="workspace-section-heading"><p class="section-kicker">Elevated authority</p><h2>Admin Session</h2></div>${sessionFacts(elevation)}<button class="text-button" type="button" data-admin-auth-action="revoke">Leave Admin context</button></section>`;
  return `<section class="workspace-section" data-admin-workspace-panel="overview"><div class="workspace-section-heading"><p class="section-kicker">Admin elevation</p><h2>Overview</h2></div><p class="summary">Elevated Admin authority is subordinate to the authenticated Production Developer session and remains live-only.</p>${sessionFacts(elevation)}<p class="workspace-status">Reviews are presentation-ready; persisted review decisions remain unavailable until a governed Review API exists.</p></section>`;
}

export function adminWorkspaceMarkup({
  elevation,
  activeSection = AdminWorkspaceSection.OVERVIEW,
  reviewStatus = AdminReviewStatus.PENDING,
  reviewView = createUnavailableAdminReviewView(reviewStatus),
} = {}) {
  if (!elevation) return "";
  const section = Object.values(AdminWorkspaceSection).includes(activeSection) ? activeSection : AdminWorkspaceSection.OVERVIEW;
  const view = reviewView?.status === reviewStatus ? reviewView : createUnavailableAdminReviewView(reviewStatus);
  return `<section class="workspace-page admin-workspace-page" data-role="admin-auth-boundary" data-admin-elevated="true" aria-labelledby="admin-workspace-title">
    <header class="workspace-heading">
      <p class="eyebrow">Production · Elevated Admin</p>
      <h1 id="admin-workspace-title">Admin Workspace</h1>
      <p class="summary">Developer identity remains authenticated beneath this separately elevated Admin context.</p>
    </header>
    ${nav(section)}
    ${panel(section, elevation, view)}
    <div class="workspace-terminal-actions">
      <button class="workspace-signout-button" type="button" data-auth-action="logout">Sign out</button>
    </div>
  </section>`;
}
