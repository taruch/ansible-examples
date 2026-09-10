# PSRP vs. WinRM Connection Plugins: Functionality and Security Implications

## 1. Overview

Ansible offers two connection plugins for talking to Windows hosts: `ansible_connection: winrm` and `ansible_connection: psrp`. These are often described as "the WinRM connection" and "the PSRP connection," which implies they are two different network protocols or two different listeners. They are not. Both connect to the same WinRM listener using the same authentication mechanisms; what differs is the client library and remoting model layered on top.

## 2. What's Actually Different

Both plugins connect to the same WinRM listener (WS-Management / WSMan, TCP 5985 HTTP or 5986 HTTPS), and both support the same authentication mechanisms the listener offers: Basic, NTLM, Kerberos, CredSSP, and certificate. Enabling PSRP does not open a new port, a new service, or a new listener on the target — `Enable-PSRemoting` and the WinRM HTTPS listener setup this repo already documents (`setup_winrm_https.yml`, `WINRM_TROUBLESHOOTING.md`) is the same prerequisite either way.

What differs is the client library and remoting model layered on top of that shared transport:

- **`winrm` plugin** — uses `pywinrm`. Each task is executed by opening a WinRM shell and sending an `exec_command`-style operation (conceptually similar to `winrs`/`WinRM CommandLine`). Ansible's PowerShell module wrapper is base64-encoded and passed as the command to run.
- **`psrp` plugin** — uses `pypsrp`, which implements the actual PowerShell Remoting Protocol (PSRP) — the same protocol behind native `Enter-PSSession` / `Invoke-Command`. Tasks run inside a real PowerShell runspace on the target, with PSRP's own message-fragmentation and object-serialization layer instead of a bare exec command.

Both python libraries are available in the supported Execution Environments from Red Hat:
- `registry.redhat.io/ansible-automation-platform-26/ee-supported-rhel9:latest`
- `registry.redhat.io/ansible-automation-platform-26/ee-minimal-rhel9:latest`

## 3. Functionality Implications

| Concern | `winrm` | `psrp` |
|---|---|---|
| Underlying library | `pywinrm` | `pypsrp` |
| Remoting model | WinRM shell / exec_command | Full PSRP (real PowerShell runspace) |
| Session reuse across tasks | Limited — closer to one-shot exec per task | Native — a runspace persists for the play, closer to how interactive `Invoke-Command` behaves |
| Large stdout / output volume | More prone to hitting `MaxEnvelopeSizekb` / shell buffer limits on chatty tasks; may require tuning the listener | PSRP's own fragmentation handles larger payloads more gracefully, generally less tuning needed |
| File transfer (`win_copy`, module argument staging) | Base64 payload embedded in exec commands; large files can require raising `MaxEnvelopeSizekb` | Uses PSRP's native chunked transfer; typically less sensitive to envelope-size limits |
| Certificate authentication | Supported by `pywinrm` (`ansible_winrm_transport: certificate`), but less commonly exercised in Ansible-for-Windows tooling | Supported via `ansible_psrp_auth: certificate` — this is what `windows_certificate_authentication.md` Phase 3 uses as the standard in this repo |
| EE / dependency footprint | Needs `pywinrm` (+ `requests-credssp`, `pyspnego`/`pykerberos` for those transports) baked into the Execution Environment | Needs `pypsrp` (+ `pyspnego` for Kerberos/CredSSP) baked into the EE instead |
| Behavioral fidelity to "real" PowerShell | Slightly more removed — each task is closer to a fresh non-interactive PowerShell invocation | Closer to genuine interactive remoting semantics (pipeline, streams, runspace state) since it *is* that protocol |

Neither plugin is "more capable" for the core `ansible.windows`/`community.windows` module set — those modules run under either connection plugin, and this repo's playbooks work today under `winrm`. The differences mostly surface at the edges: large-output tasks, large file transfers, and multi-task plays against the same host where session-reuse overhead adds up. `MaxEnvelopeSizekb`-related truncation or timeout tuning issues under `winrm` (see `WINRM_TROUBLESHOOTING.md`) are the class of problem PSRP tends to reduce, not eliminate.

## 4. Security Implications

The wire-level security posture is identical between the two plugins, because it's the same listener and the same auth stack. Switching connection plugin does not, by itself, change what's encrypted, what's authenticated, or what an attacker with network access to port 5985/5986 can attempt. Describing PSRP as "the secure one" and WinRM as "the insecure one" conflates the auth *transport* chosen (e.g., CredSSP vs. Kerberos vs. certificate) with the connection plugin. The security-relevant setting is `ansible_winrm_transport` / `ansible_psrp_auth`, not `ansible_connection`.

- **CredSSP risk is transport-specific, not plugin-specific.** This repo's own `hosts` file and `WINRM_TROUBLESHOOTING.md` default several examples to `ansible_winrm_transport=credssp`. CredSSP delegates credentials to the target (double-hop support) and has a materially weaker security history (e.g., the CredSSP encryption-oracle issue, CVE-2018-0886) than Kerberos or certificate auth. CredSSP support exists on both plugins, so this risk applies regardless of which one is used.
- **Certificate-based mutual auth is the strongest option available, and in this repo it is wired through `psrp`, not `winrm`.** `windows_certificate_authentication.md` uses `ansible_connection: psrp` with `ansible_psrp_auth: certificate` — no password is ever sent by or known to AAP for that connection. The underlying WSMan trust model (client cert → mapped local logon, see `wsman_mapping_credential_options.md`) is conceptually plugin-agnostic, but `psrp` is what this repo's tooling currently implements it with.
- **Attack surface exposed to an authenticated caller is essentially equivalent.** Both plugins ultimately run PowerShell on the target under the authenticated identity. PSRP does not expose more of the PowerShell engine than the winrm plugin's wrapper-script execution does in practice — both provide full remote code execution as the authenticated account.
- **Detection/log visibility may differ and should be validated against the target environment's SIEM/EDR rather than assumed.** Because PSRP is genuine PowerShell remoting, sessions may correlate more directly with native PowerShell remoting log sources (WinRM operational log, PowerShell Operational log, script block logging event IDs) than the `winrm` plugin's exec-command wrapper does. This should be confirmed empirically (run a task under each plugin and check what lands in the SIEM) rather than assumed.
- **Dependency/supply-chain surface differs.** `pywinrm` and `pypsrp` are separate third-party libraries with independent maintenance and CVE histories. Whichever plugin is used, that library (and its transport-specific extras — `requests-credssp`, `pyspnego`, etc.) is what needs to be tracked for advisories in the Execution Environment build.
- **Neither plugin changes the credential-management tradeoffs in `wsman_mapping_credential_options.md`.** Blast radius, rotation, and kill-switch tradeoffs for the mapping account are properties of the WSMan `ClientCertificate` mapping and the account behind it, not of `ansible_connection`.

## 5. Comparison Summary

| Dimension | `winrm` | `psrp` |
|---|---|---|
| Network surface / listener | Same WinRM listener, same ports | Same WinRM listener, same ports |
| Supported auth transports | Basic, NTLM, Kerberos, CredSSP, certificate | Basic, NTLM, Kerberos, CredSSP, certificate |
| Auth path used in this repo's tooling | Not used for certificate auth in current docs | Certificate auth (`ansible_psrp_auth: certificate`) — used in `windows_certificate_authentication.md` |
| CredSSP risk | Present if selected as transport | Present if selected as transport — same risk, same CVE history |
| Large output / large file handling | More prone to envelope-size and buffer tuning | Generally more forgiving, less tuning |
| Session reuse across tasks in a play | Weaker | Native runspace reuse |
| RCE surface for an authenticated caller | Full PowerShell via wrapper execution | Full PowerShell via native runspace — practically equivalent |
| Log/SIEM correlation with native PS remoting detections | Unconfirmed — validate per environment | Likely closer, since it *is* PS remoting — validate per environment |
| EE dependency | `pywinrm` + transport extras | `pypsrp` + transport extras |

## 6. Summary

PSRP and WinRM are not two different security postures — they are two client implementations of the same WSMan trust boundary. The security-relevant choice is the auth transport (CredSSP vs. Kerberos vs. certificate), which is orthogonal to `ansible_connection`.

This repo's certificate-auth architecture (`windows_certificate_authentication.md`) is implemented on `psrp`, and `psrp` also tends to need less tuning for large-output or large-file tasks. CredSSP usage present in this repo's examples (`hosts`, several blocks in `WINRM_TROUBLESHOOTING.md`) carries the same risk regardless of connection plugin and should be migrated toward Kerberos or certificate auth where feasible. Log/SIEM correlation between the two plugins is the one item in this document that is not asserted as fact and should be validated against the target environment's detection tooling before drawing conclusions.
