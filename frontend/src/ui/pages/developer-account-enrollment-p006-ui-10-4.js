/** P006.UI.10.4 — Successor Developer enrollment presentation. */
import { AccountEnrollmentRoute } from "../../app/account/account-enrollment-route.js";
import {
  developerAccessRequestMarkup,
  developerRequestReceivedMarkup,
  developerSetupVerificationMarkup,
  developerEmailVerificationMarkup,
  developerEnigmaProvisioningMarkup,
  developerAccountCompleteMarkup,
} from "./developer-account-enrollment.js";

export {
  developerAccessRequestMarkup,
  developerRequestReceivedMarkup,
  developerSetupVerificationMarkup,
  developerEmailVerificationMarkup,
  developerEnigmaProvisioningMarkup,
  developerAccountCompleteMarkup,
};

function foundationNotice(message) {
  return `<div class="account-foundation-note" role="note"><strong>Frontend foundation</strong><p>${message}</p></div>`;
}

export function developerRegistrationMarkup() {
  return `
    <section class="entry-page account-page account-form-page" aria-labelledby="developer-register-title">
      <p class="eyebrow">NexaDevs Developer</p>
      <h1 id="developer-register-title">Create Developer credentials</h1>
      <p class="summary">Approved identity fields become authoritative read-only values after Developer Setup verification. Profile details such as date of birth and address are deliberately deferred.</p>

      <form class="account-form" data-account-foundation-form="developer-register" data-account-foundation-only="true" novalidate>
        <label>Developer Setup ID<input name="developerSetupId" value="" placeholder="Provided after verification" readonly></label>
        <label>Approved name<input name="approvedName" value="" placeholder="Provided after verification" readonly></label>
        <label>Approved email<input name="approvedEmail" type="email" value="" placeholder="Provided after verification" readonly></label>
        <label>Username<input name="username" autocomplete="username" required></label>
        <label>Password<input name="password" type="password" autocomplete="new-password" required></label>
        <label>Confirm password<input name="confirmPassword" type="password" autocomplete="new-password" required></label>
        <div class="password-requirements" data-password-strength-presentation aria-label="Future password strength presentation">
          <strong>Password strength</strong>
          <output data-password-strength>Not evaluated</output>
          <p>Final strength measurement, qualification policy and enforcement belong to the future Production credential authority.</p>
        </div>
        <p class="account-authority-message" data-account-authority-message role="status" aria-live="polite"></p>
        <button class="primary-button" type="submit">Continue</button>
      </form>

      ${foundationNotice("No username or password is stored by P006.UI.10.4. Developer Setup verification, credential persistence, OTP and profile enrichment remain governed later authority.")}
      <button class="text-button" type="button" data-account-route="${AccountEnrollmentRoute.DEVELOPER_VERIFY_SETUP}">← Verify Developer Setup</button>
    </section>`;
}
