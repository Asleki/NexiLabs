/** P006.UI.10.4 — Replaceable Admin Reviews presentation contract. */
export const AdminReviewStatus = Object.freeze({
  PENDING: "PENDING",
  UNDER_REVIEW: "UNDER_REVIEW",
  APPROVED: "APPROVED",
  REJECTED: "REJECTED",
});

export const AdminReviewUiState = Object.freeze({
  LOADING: "loading",
  READY: "ready",
  EMPTY: "empty",
  DENIED: "denied",
  STALE: "stale",
  SERVICE_UNAVAILABLE: "service-unavailable",
  ERROR: "error",
});

const STATUSES = new Set(Object.values(AdminReviewStatus));
const UI_STATES = new Set(Object.values(AdminReviewUiState));

function text(value) { return String(value ?? "").trim(); }

export function normalizeAdminReviewRecord(record) {
  if (!record || typeof record !== "object") throw new TypeError("review record is required");
  const requestReference = text(record.requestReference);
  const status = text(record.status).toUpperCase();
  if (!requestReference) throw new TypeError("requestReference is required");
  if (!STATUSES.has(status)) throw new TypeError("unsupported review status");
  return Object.freeze({
    requestReference,
    status,
    applicantName: text(record.applicantName),
    applicantEmail: text(record.applicantEmail),
    submittedAt: text(record.submittedAt),
    updatedAt: text(record.updatedAt),
    reviewReason: text(record.reviewReason),
    applicantExplanation: text(record.applicantExplanation),
  });
}

export function createAdminReviewView({
  state = AdminReviewUiState.SERVICE_UNAVAILABLE,
  status = AdminReviewStatus.PENDING,
  records = [],
  selectedRequestReference = "",
  message = "Review authority is not available in this milestone.",
  decisionAuthorityAvailable = false,
} = {}) {
  if (!UI_STATES.has(state)) throw new TypeError("unsupported review UI state");
  if (!STATUSES.has(status)) throw new TypeError("unsupported review status");
  const normalized = Object.freeze(records.map(normalizeAdminReviewRecord));
  const selected = normalized.find((record) => record.requestReference === selectedRequestReference) || null;
  return Object.freeze({
    state,
    status,
    records: normalized,
    selected,
    message: text(message),
    decisionAuthorityAvailable: decisionAuthorityAvailable === true,
  });
}

export function createUnavailableAdminReviewView(status = AdminReviewStatus.PENDING) {
  return createAdminReviewView({
    state: AdminReviewUiState.SERVICE_UNAVAILABLE,
    status,
    records: [],
    message: "Decision authority unavailable — Developer Review authority is not connected yet. No review decision can be persisted from this interface.",
    decisionAuthorityAvailable: false,
  });
}
