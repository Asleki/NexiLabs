import assert from "node:assert/strict";
import test from "node:test";

import {
  AdminReviewStatus,
  AdminReviewUiState,
  createAdminReviewView,
  createUnavailableAdminReviewView,
} from "../../src/app/admin/admin-review-view-model.js";
import { adminWorkspaceMarkup, AdminWorkspaceSection } from "../../src/ui/pages/admin-workspace.js";

const elevation = {
  elevationId: "admin-elevation:1",
  adminOperatorId: "admin-operator:1",
  expiresAt: "2026-09-24T22:00:00+00:00",
  permissions: ["NEXILABS.ADMIN.ELEVATE", "NEXILABS.AUDIT.READ"],
};

test("Admin Workspace is elevation-guarded and exposes all six required sections", () => {
  assert.equal(adminWorkspaceMarkup({ elevation: null }), "");
  const html = adminWorkspaceMarkup({ elevation });
  assert.match(html, /Admin Workspace/);
  for (const section of Object.values(AdminWorkspaceSection)) {
    assert.match(html, new RegExp(`data-admin-workspace-section="${section}"`));
  }
  for (const label of ["Overview", "Reviews", "Developer Access", "Enigma Governance", "Audit", "Admin Session"]) {
    assert.match(html, new RegExp(label));
  }
});

test("Reviews exposes four governed states plus search, sort, detail and unavailable decision authority", () => {
  const html = adminWorkspaceMarkup({
    elevation,
    activeSection: AdminWorkspaceSection.REVIEWS,
    reviewStatus: AdminReviewStatus.PENDING,
  });
  for (const label of ["Pending", "Under Review", "Approved", "Rejected"]) assert.match(html, new RegExp(label));
  assert.match(html, /data-admin-review-search/);
  assert.match(html, /data-admin-review-sort/);
  assert.match(html, /Review detail/);
  assert.match(html, /Decision authority unavailable/i);
  assert.match(html, /No review decision can be persisted/i);
});

test("review view model supports loading empty denied stale unavailable error without fabricated records", () => {
  for (const state of Object.values(AdminReviewUiState)) {
    const view = createAdminReviewView({ state, records: [] });
    assert.equal(view.records.length, 0);
  }
  const unavailable = createUnavailableAdminReviewView(AdminReviewStatus.REJECTED);
  assert.equal(unavailable.status, AdminReviewStatus.REJECTED);
  assert.equal(unavailable.decisionAuthorityAvailable, false);
});

test("a real adapter record can be rendered, but decision controls stay disabled without real authority", () => {
  const view = createAdminReviewView({
    state: AdminReviewUiState.READY,
    status: AdminReviewStatus.PENDING,
    selectedRequestReference: "request:123",
    records: [{
      requestReference: "request:123",
      status: "PENDING",
      applicantName: "Applicant One",
      applicantEmail: "applicant@example.com",
      submittedAt: "2026-09-24T10:00:00Z",
      updatedAt: "2026-09-24T10:00:00Z",
    }],
    decisionAuthorityAvailable: false,
  });
  const html = adminWorkspaceMarkup({
    elevation,
    activeSection: AdminWorkspaceSection.REVIEWS,
    reviewStatus: AdminReviewStatus.PENDING,
    reviewView: view,
  });
  assert.match(html, /request:123/);
  assert.match(html, /Applicant One/);
  assert.match(html, /Decision reason/);
  assert.match(html, /Safe applicant explanation/);
  assert.match(html, /data-admin-review-decision="approve" disabled/);
  assert.match(html, /data-admin-review-decision="reject" disabled/);
  assert.match(html, /no history is fabricated locally/i);
});

test("Admin session surface preserves exact operator, expiry, permissions and reversible elevation", () => {
  const html = adminWorkspaceMarkup({ elevation, activeSection: AdminWorkspaceSection.ADMIN_SESSION });
  assert.match(html, /admin-operator:1/);
  assert.match(html, /2026-09-24T22:00:00\+00:00/);
  assert.match(html, /NEXILABS.ADMIN.ELEVATE/);
  assert.match(html, /volatile browser context/);
  assert.match(html, /data-admin-auth-action="revoke"/);
});
