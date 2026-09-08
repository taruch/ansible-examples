# WSMan ClientCertificate Mapping: Credential Management Options

## 1. The Problem

[`windows_certificate_authentication.md`](./windows_certificate_authentication.md) (Phase 3, step 4) maps an AAP-presented client certificate to a Windows logon identity using `New-Item -Path WSMan:\localhost\ClientCertificate ... -Credential $credential`. Certificate authentication over WinRM/PSRP does not eliminate the need for a credential — it eliminates the need for AAP to *send* one at connection time. Something must still exist, ahead of time, that tells Windows "when a client presents a certificate with this Subject and Issuer, log the session in as account X." That account's password is what's registered in the mapping, and it is the thing an administrator (or an automation job) must set, store, and eventually rotate.

This document lays out the options for managing that mapping-credential account, and the security tradeoffs of each. It's written as a standalone reference because the choice matters independently of the certificate-auth architecture itself — the same three options and tradeoffs apply to any WinRM/PSRP deployment that maps an external identity to a local logon account.

Five options were considered. One was ruled out immediately; the other four are live tradeoffs.

## 2. Ruled Out: Group Managed Service Accounts (gMSA)

gMSAs solve a different problem than the one here. A gMSA lets a **host** authenticate **as** the gMSA when running a service on that host — Windows retrieves and rotates the password internally, and it is deliberately never exposed as a usable plaintext value. There is no supported way to extract a gMSA's password into a `PSCredential` object for an **external caller** (AAP) to present when logging **into** a target host. The direction of authentication is backwards from what the WSMan mapping needs, so gMSA isn't a candidate here regardless of its other security properties.

## 3. Option A: Static Shared Account (Local or Domain)

This is what the example in Phase 3 currently shows: a single account (local or domain) with a Vault-encrypted password, created once, mapped on every host in `win_servers`, with `password_never_expires: true`.

**Benefits:**
- Simplest possible implementation — one credential, one playbook, no additional orchestration or Windows-side tooling.
- No dependency on AD infrastructure beyond what's already required for the CA.
- Easy to reason about and explain: "AAP knows one password, every host trusts it."

**Cons:**
- **The password is identical across every host in the fleet.** A shared secret does not contain blast radius by account scope (local vs. domain) — the account's *reach* is what matters, and here that reach is the entire fleet. Compromise of the password on one host, or exfiltration from the AAP vault, is equivalent to compromising all of them.
- Rotation is manual and fleet-wide: changing the password means re-running the mapping playbook against every host before the old password can be safely retired, with no enforced cadence.
- `password_never_expires: true` is required to keep automation from silently breaking, which means there is no organic expiration pressure — the password lives until someone deliberately rotates it.
- No fail-closed kill switch: revoking access in an incident requires actively pushing a change to every host, not flipping a single control point.

This option is reasonable for a lab or proof-of-concept, but should be presented to a security-conscious customer as the weakest posture of the three, not a production target.

## 4. Option B: Domain Account + AD-Rotation AAP Workflow

A domain account is used for the mapping, managed by a two-node AAP workflow: **Node A** rotates the account's password in AD and updates the corresponding AAP credential (`ansible.controller.credential`); **Node B** re-applies the WSMan mapping fleet-wide using the new credential.

**Benefits:**
- Rotation is centralized in AD rather than requiring a full fleet resync to *change* the password — Node A's AD password change is a single API call.
- **Rotating the AD password is an immediate, fail-closed kill switch.** The moment Node A runs, every host's WSMan mapping goes stale simultaneously, because they all validate against the same AD-backed credential. For incident response — "we believe this account is compromised, cut it off now" — this is the fastest option of the three to guarantee no further use of the old password anywhere in the fleet.
- Rotation can be scheduled and fully automated (AAP workflow schedule), giving a real, enforced cadence instead of "whenever someone remembers."
- Standard AD authentication logging/auditing applies, which plugs into existing SIEM tooling most enterprises already have pointed at domain controllers.

**Cons:**
- It is still **one shared secret across the entire fleet** — the same blast-radius characteristic as Option A. Rotation hygiene is better, but a live compromise between rotations is just as fleet-wide as the static-account case.
- The fail-closed kill switch cuts both ways: **legitimate access is also down** for every host from the moment Node A rotates until Node B finishes re-applying the mapping across the whole fleet. A large fleet or a slow Node B run means a real availability gap, not just for an attacker.
- Node A itself becomes a high-value target: it holds (transiently) the new domain password and write access to the AAP credential store. Compromising Node A's execution path is now equivalent to compromising the mapping account, so it needs tighter scoping/RBAC than a routine job template.
- Domain account membership means a compromise of this credential has to be evaluated against whatever else that account can reach in AD, not just the WSMan mappings — the blast radius isn't strictly contained to "Windows remote management," unless the account is deliberately scoped down (no other group memberships, restricted logon rights).
- Adds real orchestration complexity: two coordinated job templates, partial-failure handling if Node B doesn't complete against the whole fleet, and a window where hosts are in an inconsistent state.

## 5. Option C: Windows LAPS-Managed Local Account

A dedicated local account (e.g. `aap_winrm_svc`) on each host is enrolled in Windows LAPS (2023+ supports naming an arbitrary local account, not just the built-in `Administrator`). LAPS rotates each host's password independently, on its own policy-driven schedule. AAP's role shifts from *setting* the password to *reading* it: a low-privilege "LAPS reader" domain service account calls `Get-LapsADPassword` to fetch the current value and re-syncs the WSMan mapping.

**Benefits:**
- **Per-host unique passwords.** This is the one option that actually delivers the blast-radius containment that a shared-password approach only implies — compromising the mapping credential on one host tells an attacker nothing about any other host.
- Rotation is a mature, Microsoft-native, AD-schema-integrated mechanism, not custom automation logic — less surface area for the rotation process itself to have bugs.
- AAP no longer holds any credential capable of *setting* a password. The "LAPS reader" account only has read access to AD-stored LAPS passwords, which is a materially lower-value credential than either Option A's or Option B's shared account — compromising it lets an attacker read current passwords, but not silently mint new ones or persist access through a rotation.
- LAPS rotation events are logged (Windows Security event log / AD), giving a native audit trail per host.

**Cons:**
- Requires RSAT LAPS tooling reachable from the automation path to call `Get-LapsADPassword` — this **cannot** be invoked directly from a Linux Execution Environment, so the architecture needs a Windows hop in the automation path that the other two options don't require. That's a real infrastructure dependency to introduce.
- **Staleness window:** the WSMan mapping only reflects the password LAPS had at the time of the last resync job. LAPS rotates on its own schedule, independent of AAP — after a rotation, the mapping is broken until AAP's resync job next runs. Left on a timer/poll, this could be minutes to hours of broken (not compromised — just non-functional) automation access per host.
  - The proposed mitigation is an EDA rulebook watching for the LAPS rotation Windows Security event and triggering an immediate per-host resync, rather than polling on a fixed interval. This closes the gap but is additional infrastructure that has to be built and maintained — it is not a solved problem out of the box the way Option B's rotation is a single scheduled workflow.
- No fleet-wide fail-closed kill switch. Because passwords are per-host, "cut off this account everywhere right now" means either waiting for/forcing a LAPS rotation on every host individually, or falling back to disabling the WSMan mapping directly — there's no single AD-side action that invalidates the account everywhere at once the way Option B's domain password rotation does.
- The "LAPS reader" account's read access to plaintext LAPS passwords is itself a sensitive delegation in AD and needs its own scoping (which OUs/computer objects it can read LAPS passwords for) — it's lower-value than Options A/B's account, but it isn't a zero-value credential.
- Same fan-out mechanics as Option B are still needed after every rotation (re-apply the mapping to the affected host), just triggered per-host/event-driven instead of via a scheduled fleet-wide workflow.

## 6. Option D: Local Account, Ephemeral Per-Host Password (Never Stored)

A dedicated local account is used, but its password is never persisted anywhere — not in AAP's Vault, not in a credential object, not on disk. Every time the mapping-refresh playbook runs, it generates a fresh random password in memory, sets it on the local account, and immediately uses that same in-memory value to (re)create the WSMan `ClientCertificate` mapping. The password exists only for the duration of that single playbook run.

This works because two things are true: `win_user` *sets* a password rather than verifying a prior one, so the playbook never needs to know what the password was before; and AAP never needs the mapping account's password to actually *use* the certificate-authenticated connection — only the certificate's Subject/Issuer are ever sent from AAP to the host. The account's password only matters inside the target host's own logon subsystem, and this option is the only one that keeps it confined to exactly that scope.

**Benefits:**
- Per-host uniqueness, same as Option C (LAPS) — compromising the mapping credential on one host reveals nothing about any other host.
- No stored secret exists to steal, anywhere. There's no AAP Vault entry, no AD-replicated LAPS value, nothing at rest for an attacker (or an insider with vault access) to exfiltrate for this account.
- No separate Windows hop or RSAT LAPS tooling dependency — the entire mapping-refresh operation runs as an ordinary task from the same Linux Execution Environment already used for everything else in this architecture.
- Rotation and the incident-response kill switch collapse into the same single action: re-run the mapping playbook against the host(s) in question. No staleness window (unlike LAPS, which rotates on its own schedule independent of AAP) and no fleet-wide availability gap (unlike the domain-rotation workflow, since each host's password was always independent of every other host's).
- Simplest workflow of the non-static options: one job template, no two-node orchestration, no reader account, no EDA rulebook required.

**Cons:**
- Only works for a **local** account. A domain account has exactly one password by definition — you cannot give a single AD identity a different password per host, so this technique doesn't extend to Option B's domain-account model.
- The password still exists transiently: in the playbook's variables, in the `win_user` call, and on the wire to that host during the run. Every task touching it needs `no_log: true`, or the value lands in AAP job stdout/event data and the entire benefit is defeated.
- No durable record of "what is the current password" for audit purposes. Not a functional gap — nothing external ever needs the value — but it's a departure from a compliance posture that expects credential values to be inspectable/attestable somewhere.
- Local account password complexity/history policy on the target still applies to whatever value is generated.
- No native scheduled rotation the way LAPS provides — rotation only happens when the mapping-refresh job actually runs, so a deliberate AAP workflow schedule still needs to be configured to get an enforced cadence; it isn't automatic.

## 7. Comparison Summary

| Dimension | A: Static Shared Account | B: Domain Account + AD-Rotation Workflow | C: LAPS-Managed Local Account | D: Local Account, Ephemeral Password |
|---|---|---|---|---|
| Blast radius of one compromised credential | Entire fleet | Entire fleet | Single host | Single host — and there's no persisted secret to compromise in the first place |
| Rotation authority | Manual, ad hoc | Scheduled, centralized in AD | Automatic, per-host, Microsoft-native | Ad hoc — happens whenever the mapping playbook is run; schedule it explicitly for cadence |
| Fleet-wide fail-closed kill switch | No | Yes (single AD password change) | No (per-host only) | No (per-host only, but there's nothing stored to "switch off") |
| Availability impact during rotation | None (rotation rarely happens) | Fleet-wide access gap until Node B completes | None (per-host resync only) | None (per-host, synchronous, single job) |
| Credential AAP holds day-to-day | High-value (sets fleet password) | High-value (sets domain password) | Low-value (read-only LAPS reader) | None — no persisted secret for this account exists anywhere |
| Extra infrastructure required | None | Two-node AAP workflow | Windows hop for RSAT LAPS tooling; ideally an EDA rulebook | None beyond the existing mapping-refresh playbook |
| Native audit trail | Minimal | AD authentication logs | LAPS rotation events (per host) | None built-in; rely on AAP job history for when the mapping was last refreshed |

## 8. Talking Points

- There is no option here that is simply "more secure" than the others in every dimension — Option B optimizes for incident-response speed at the cost of a fleet-wide availability window and a still-shared secret; Option C optimizes for blast-radius containment at the cost of infrastructure complexity and a rotation-staleness window; Option D gets the same blast-radius containment as C without either of those costs, at the cost of having no fleet-wide kill switch and no durable audit record of the credential value; Option A optimizes for simplicity at the cost of everything else.
- **Option D is the recommended default** for this architecture: it matches LAPS's per-host containment, requires no additional infrastructure beyond what's already in the automation path, and has no rotation-staleness window. `windows_certificate_authentication.md` uses it as the default in Phase 3.
- Reach for Option B instead specifically when the requirement is a fleet-wide, single-action kill switch (e.g., responding to a suspected domain-wide compromise) and the availability tradeoff during rotation is acceptable.
- Option C remains relevant if LAPS is already deployed fleet-wide for other accounts and there's value in managing this account the same way, with the same tooling and audit trail, as everything else.
- If the driving concern is "how much does a single compromised credential actually expose," lead with Option C or D — they're the only two where compromising one host's mapping credential implies nothing about the rest of the fleet.
- Option A should not be presented as a security control at all — it's a functional baseline, appropriate for a lab/POC, not a production recommendation.
- gMSA comes up often in these conversations because it *sounds* like the modern, password-less answer — worth proactively explaining why it doesn't apply to this direction of authentication, rather than waiting to be asked.
