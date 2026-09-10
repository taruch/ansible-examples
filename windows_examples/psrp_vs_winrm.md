# PSRP vs. WinRM Connection Plugins: Functionality and Security Implications

## 1. The Question

Ansible offers two connection plugins for talking to Windows hosts: `ansible_connection: winrm` and `ansible_connection: psrp`. Both are commonly (and loosely) described as "the WinRM connection" and "the PSRP connection," which invites the wrong mental model — that they're two different network protocols or two different listeners to secure. They aren't. This document is written for the same security-focused audience as [`windows_certificate_authentication.md`](./windows_certificate_authentication.md) and [`wsman_mapping_credential_options.md`](./wsman_mapping_credential_options.md), and the first thing worth correcting in that conversation is what is actually different between the two.

## 2. What's Actually Different

Both plugins connect to the **same WinRm listener** (WS-Management / WSMan, TCP 5985 HTTP or 5986 HTTPS), and both support the **same authentication mechanisms** the listener offers: Basic, NTLM, Kerberos, CredSSP, and certificate. Enabling PSRP does not open a new port, a new service, or a new listener on the target — `Enable-PSRemoting` and the WinRM HTTPS listener setup this repo already documents (`setup_winrm_https.yml`, `WINRM_TROUBLESHOOTING.md`) is the same prerequisite either way.

What differs is the **client library and remoting model** layered on top of that shared transport:

- **`winrm` plugin** — uses `pywinrm`. Each task is executed by opening a WinRM shell and sending an `exec_command`-style operation (conceptually similar to `winrs`/`WinRM CommandLine`). Ansible's PowerShell module wrapper is base64-encoded and passed as the command to run.
- **`psrp` plugin** — uses `pypsrp`, which implements the actual PowerShell Remoting Protocol (PSRP) — the same protocol behind native `Enter-PSSession` / `Invoke-Command`. Tasks run inside a real PowerShell runspace on the target, with PSRP's own message-fragmentation and object-serialization layer instead of a bare exec command.

So the honest framing for a customer is: **same door, same lock, two different ways of walking through it once you're authenticated.**

Both python libraries are available in the supported EE's from Red Hat.
registry.redhat.io/ansible-automation-platform-26/ee-supported-rhel9:latest
registry.redhat.io/ansible-automation-platform-26/ee-minimal-rhel9:latest

## 3. Functionality Implications

| Concern | `winrm` | `psrp` |
|---|---|---|
| Underlying library | `pywinrm` | `pypsrp` |
| Remoting model | WinRM shell / exec_command | Full PSRP (real PowerShell runspace) |
| Session reuse across tasks | Limited — closer to one-shot exec per task | Native — a runspace persists for the play, closer to how interactive `Invoke-Command` behaves |
| Large stdout / output volume | More prone to hitting `MaxEnvelopeSizekb` / shell buffer limits on chatty tasks; may require tuning the listener | PSRP's own fragmentation handles larger payloads more gracefully, generally less tuning needed |
| File transfer (`win_copy`, module argument staging) | Base64 payload embedded in exec commands; large files can require raising `MaxEnvelopeSizekb` | Uses PSRP's native chunked transfer; typically less sensitive to envelope-size limits |
| Certificate authentication | Supported by `pywinrm` (`ansible_winrm_transport: certificate`), but less commonly exercised in Ansible-for-Windows tooling | Supported via `ansible_psrp_auth: certificate` — this is what `windows_certificate_authentication.md` Phase 3 already uses as the standard in this repo |
| EE / dependency footprint | Needs `pywinrm` (+ `requests-credssp`, `pyspnego`/`pykerberos` for those transports) baked into the Execution Environment | Needs `pypsrp` (+ `pyspnego` for Kerberos/CredSSP) baked into the EE instead |
| Behavioral fidelity to "real" PowerShell | Slightly more removed — each task is closer to a fresh non-interactive PowerShell invocation | Closer to genuine interactive remoting semantics (pipeline, streams, runspace state) since it *is* that protocol |

None of this makes one plugin "more capable" for the core `ansible.windows`/`community.windows` module set — those modules are written to run under either connection plugin, and this repo's playbooks work today under `winrm`. The differences mostly surface at the edges: large-output tasks, large file transfers, and multi-task plays against the same host where session-reuse overhead adds up. If you've hit `MaxEnvelopeSizekb`-related truncation or timeout tuning pain with `winrm` (see `WINRM_TROUBLESHOOTING.md`), that is the class of problem PSRP tends to reduce, not eliminate.

## 4. Security Implications

**The wire-level security posture is identical, because it's the same listener and the same auth stack.** Switching connection plugin does not, by itself, change what's encrypted, what's authenticated, or what an attacker with network access to port 5985/5986 can attempt. Anyone framing PSRP as "the secure one" and WinRM as "the insecure one" is describing the auth *transport chosen* (e.g., CredSSP vs. Kerberos vs. certificate), not the connection plugin. That distinction matters when explaining this to a security team — the real security lever is `ansible_winrm_transport` / `ansible_psrp_auth`, not `ansible_connection`.

Points worth making explicitly:

- **CredSSP is CredSSP regardless of plugin.** This repo's own `hosts` file and `WINRM_TROUBLESHOOTING.md` default several examples to `ansible_winrm_transport=credssp`. CredSSP delegates credentials to the target (double-hop support) and has a materially weaker security history (e.g., the CredSSP encryption-oracle issue, CVE-2018-0886) than Kerberos or certificate auth. This is true whether it's driven through `winrm` or `psrp` — CredSSP support exists on both plugins. A security-conscious customer should be steered off CredSSP as a transport, independent of which connection plugin is in use.
- **Certificate-based mutual auth is the strongest option available today, and in this repo it is wired through `psrp`, not `winrm`.** `windows_certificate_authentication.md` uses `ansible_connection: psrp` with `ansible_psrp_auth: certificate` — no password is ever sent by or known to AAP for that connection. This is a practical reason to standardize on `psrp` for security-sensitive fleets even though the underlying WSMan trust model (client cert → mapped local logon, see `wsman_mapping_credential_options.md`) is conceptually plugin-agnostic.
- **Attack surface exposed to an authenticated caller is essentially equivalent.** Both plugins ultimately run PowerShell on the target under the authenticated identity. PSRP doesn't expose "more" of the PowerShell engine than the winrm plugin's wrapper-script execution does in practice — both give you full remote code execution as the authenticated account. Don't let "PSRP is the real PowerShell Remoting Protocol" get oversold as a bigger attack surface than the winrm plugin; the winrm plugin still executes arbitrary PowerShell via its command wrapper.
- **Detection/log visibility may differ and should be validated against the customer's actual SIEM/EDR, not asserted from first principles.** Because PSRP is genuine PowerShell remoting, sessions may correlate more directly with native PowerShell remoting log sources (WinRM operational log, PowerShell Operational log, script block logging event IDs) that a blue team's detections were likely built around, since those detections were probably written against real `Invoke-Command`/`Enter-PSSession` usage. The `winrm` plugin's exec-command wrapper may or may not generate the exact same log signature. This is a claim to verify empirically in the customer's environment (test a task, check what lands in their SIEM) rather than assert as fixed fact here.
- **Dependency/supply-chain surface differs.** `pywinrm` and `pypsrp` are separate third-party libraries with independent maintenance and CVE histories. Whichever plugin is standardized on, that library (and its transport-specific extras — `requests-credssp`, `pyspnego`, etc.) becomes something to track for advisories in the Execution Environment build.
- **Neither plugin changes anything about the credential-management questions in `wsman_mapping_credential_options.md`.** Blast radius, rotation, and kill-switch tradeoffs for the mapping account are properties of the WSMan `ClientCertificate` mapping and the account behind it — not of `ansible_connection`.

## 5. Comparison Summary

| Dimension | `winrm` | `psrp` |
|---|---|---|
| Network surface / listener | Same WinRM listener, same ports | Same WinRM listener, same ports |
| Supported auth transports | Basic, NTLM, Kerberos, CredSSP, certificate | Basic, NTLM, Kerberos, CredSSP, certificate |
| Strongest auth path in this repo's tooling | Certificate auth supported by `pywinrm` but not what this repo's docs standardize on | Certificate auth (`ansible_psrp_auth: certificate`) — the documented default in `windows_certificate_authentication.md` |
| CredSSP risk | Present if selected as transport | Present if selected as transport — same risk, same CVE history |
| Large output / large file handling | More prone to envelope-size and buffer tuning | Generally more forgiving, less tuning |
| Session reuse across tasks in a play | Weaker | Native runspace reuse |
| RCE surface for an authenticated caller | Full PowerShell via wrapper execution | Full PowerShell via native runspace — practically equivalent |
| Log/SIEM correlation with native PS remoting detections | Uncertain — verify in environment | Likely closer, since it *is* PS remoting — verify in environment |
| EE dependency | `pywinrm` + transport extras | `pypsrp` + transport extras |

## 6. Talking Points

- Lead with the correction, not the comparison: **PSRP and WinRM are not two different security postures** — they're two client implementations of the same WSMan trust boundary. The security conversation is really about which *auth transport* (CredSSP vs. Kerberos vs. certificate) is selected, which is orthogonal to `ansible_connection`.
- **Recommend `psrp` as the default for new work in this repo**, primarily because it's what the certificate-auth architecture (`windows_certificate_authentication.md`) already standardizes on, and secondarily because it tends to need less tuning for larger payloads. This is a functionality/maintainability reason more than a hard security win.
- **Flag CredSSP usage already present in this repo's examples** (`hosts`, several blocks in `WINRM_TROUBLESHOOTING.md`) as something to revisit with a security-conscious customer — recommend migrating those examples toward Kerberos or certificate auth, independent of which connection plugin is chosen.
- Don't let "PSRP is the real protocol" get mistaken for "PSRP has a bigger attack surface" or "PSRP is safer" — both are overclaims in opposite directions. The honest position is *functionally different, security-equivalent at the transport layer, with certificate auth (available via `psrp` in this repo's tooling) being the actual security upgrade*, not the plugin choice itself.
- The log-visibility question is the one item here worth testing rather than asserting — if the customer has PowerShell remoting detections already tuned, it's worth a quick side-by-side test (`winrm` task vs. `psrp` task) to see what actually lands in their SIEM before making claims about detection parity.
