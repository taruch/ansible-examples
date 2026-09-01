# Ansible Automation Platform `metrics-utility` — Use Cases

`metrics-utility` ([github.com/ansible/metrics-utility](https://github.com/ansible/metrics-utility))
is the CLI/library shipped with Ansible Automation Platform (AAP) Controller
that collects, analyzes, and reports automation usage data. It can run
standalone against a Controller Postgres database or from within
Controller's own Python environment (which unlocks additional settings
collection). Its primary business purpose is generating consumption/billing
reports — **CCSP**, **CCSPv2**, and **RENEWAL_GUIDANCE** — used for
subscription compliance and Red Hat's Certified Cloud and Service Provider
(CCSP) partner billing.

This document focuses on **host deduplication**: why it matters and the
concrete scenarios `metrics-utility` (and the Controller data model it reads
from) is designed to handle.

## Table of Contents

- [Why Host Deduplication Matters](#why-host-deduplication-matters)
- [Does AAP Itself Deduplicate? (Native Compliance vs. `metrics-utility`)](#does-aap-itself-deduplicate-native-compliance-vs-metrics-utility)
- [Core Deduplication Use Cases](#core-deduplication-use-cases)
  - [1. Same host automated repeatedly within a billing cycle](#1-same-host-automated-repeatedly-within-a-billing-cycle)
  - [2. Same host referenced by multiple values (IP vs. hostname vs. FQDN)](#2-same-host-referenced-by-multiple-values-ip-vs-hostname-vs-fqdn)
  - [3. Same host present in multiple inventories or organizations](#3-same-host-present-in-multiple-inventories-or-organizations)
  - [4. Directly vs. indirectly managed nodes](#4-directly-vs-indirectly-managed-nodes)
  - [5. API / control-plane automation collapsing to `localhost`](#5-api--control-plane-automation-collapsing-to-localhost)
  - [6. Soft-deleted and reinstated hosts (Host Metrics dashboard)](#6-soft-deleted-and-reinstated-hosts-host-metrics-dashboard)
  - [7. Accurate CCSP / subscription compliance and renewal reporting](#7-accurate-ccsp--subscription-compliance-and-renewal-reporting)
  - [8. Hardware-identity-based deduplication (`ansible_product_serial` / `ansible_machine_id`)](#8-hardware-identity-based-deduplication-ansible_product_serial--ansible_machine_id)
    - [How to Populate Hardware Facts for Dedup (Without Touching Other Job Templates)](#how-to-populate-hardware-facts-for-dedup-without-touching-other-job-templates)
- [Summary](#summary)
- [How-To: Discrete Node Count Over Time for a Renewal Conversation](#how-to-discrete-node-count-over-time-for-a-renewal-conversation)
  - [Variant: Containerized Deployment (podman/docker-compose install)](#variant-containerized-deployment-podmandocker-compose-install)
  - [Variant: OpenShift / Operator-based Deployment](#variant-openshift--operator-based-deployment)
- [What Exactly Gets Deduplicated for RENEWAL_GUIDANCE (and How to Test It)](#what-exactly-gets-deduplicated-for-renewal_guidance-and-how-to-test-it)
  - [`renewal` (default)](#renewal-default)
  - [`renewal-hostname`](#renewal-hostname)
  - [`renewal-experimental` — confirmed bug on multi-hop mixed-key chains](#renewal-experimental--confirmed-bug-on-multi-hop-mixed-key-chains)
  - [How to test this yourself (or re-test after an AAP upgrade)](#how-to-test-this-yourself-or-re-test-after-an-aap-upgrade)
  - [Live Validation on Real AAP Infrastructure](#live-validation-on-real-aap-infrastructure)
- [Where the Dedup Keys Actually Come From (and a Prerequisite Nobody Documents)](#where-the-dedup-keys-actually-come-from-and-a-prerequisite-nobody-documents)
  - [The prerequisite: "Use Fact Cache" must be enabled somewhere](#the-prerequisite-use-fact-cache-must-be-enabled-somewhere)
  - [Quick check: is fact caching even in use in your environment?](#quick-check-is-fact-caching-even-in-use-in-your-environment)
  - [Direct SQL check for a specific host](#direct-sql-check-for-a-specific-host)
- [Practical Guidance](#practical-guidance)
- [Sources](#sources)
- [Notes / Caveats](#notes--caveats)

## Why Host Deduplication Matters

Red Hat's managed-node billing model counts **unique hosts automated during
a billing cycle**, not job runs. The official definition:

> "A managed node is counted as a connection to a unique host (as used in
> the Ansible `host` variable) per billing cycle... Multiple automation
> events against this host will remain ONE managed active node for the
> billing cycle." — [Managed Active Node Counting](https://access.redhat.com/articles/7088928)

Because counting is keyed to *what Ansible used to connect* (hostname/DNS
record, IP address, or `ansible_host` value) rather than a stable internal
host identity, `metrics-utility`'s reports and the Controller data it reads
from (`main_host`, `main_jobhostsummary`, `main_indirectmanagednodeaudit`)
need to collapse redundant references before numbers are trusted for
billing or compliance.

## Does AAP Itself Deduplicate? (Native Compliance vs. `metrics-utility`)

Before treating anything below as "how AAP counts hosts," it's important
to separate two things: what **AAP's own live subscription compliance
number** does, versus what `metrics-utility`'s optional `RENEWAL_GUIDANCE`
report does on top of that data. Traced directly from a full local
checkout of the `ansible/awx` `devel` branch — not just individual file
fetches — since this needed cross-referencing several files at once.

**The actual number AAP uses to validate license compliance:**
```python
# awx/main/utils/licensing.py:503
automated_instances = HostMetric.active_objects.count()
```
A flat `COUNT(*)` of non-deleted rows in `main_hostmetric`, compared
directly against license capacity. This is the real, live "Hosts
automated" figure — not a `metrics-utility` computation.

**The only normalization applied before a hostname is ever written to
that table:**
```python
# awx/main/models/events.py:583-584 -- inside per-job-event host processing
if not bool(summary.dark):
    updated_hosts_list.append(host.lower())
```
Confirmed: **AAP lowercases the hostname before writing to `HostMetric`.**
If the same Controller automates `WEB05` in one run and `web05` in
another, both collapse to a single `HostMetric` row (`hostname='web05'`)
and count as **one** host natively. This is, notably, *more*
case-handling than `metrics-utility`'s own `RENEWAL_GUIDANCE` dedup code
performs (confirmed case-sensitive earlier in this document) — it just
doesn't matter downstream, since metrics-utility only ever reads whatever
string Controller already wrote.

**Everything else is confirmed absent** at the native compliance layer:
- **No IP/hostname/FQDN collapsing.** `10.0.0.5` and `web05.example.com`
  for the same physical box create two separate `HostMetric` rows and
  both count toward the license, permanently, unless someone manually
  soft-deletes one via the Host Metrics dashboard.
- **No `ansible_host` awareness** anywhere in this write path — it
  operates purely on the literal `host` string from each job's per-host
  event data.
- **No hardware-identity matching at all.** `HostMetric` has no
  `ansible_product_serial`/`ansible_machine_id` columns (confirmed
  against the model). Those facts are used **exclusively** by
  `metrics-utility`'s optional `RENEWAL_GUIDANCE` report — they play
  **zero role** in AAP's actual subscription compliance number or its
  native Host Metrics dashboard.

**Bottom line:** every dedup use case documented below — IP/hostname/FQDN
consolidation, hardware-identity matching, everything in use cases #2 and
#8 — is something `metrics-utility` does (or attempts) *on top of* raw,
largely undeduplicated AAP data. None of it feeds back into or changes
what AAP itself reports as consumed against your license. If you want
AAP's own number to go down, the only native lever is manually
soft-deleting hosts via the Host Metrics dashboard (use case #6) —
running `metrics-utility` reports has no effect on the platform's live
compliance figure, only on the analysis you build from it.

(Sources: [`awx/main/utils/licensing.py`](https://github.com/ansible/awx/blob/devel/awx/main/utils/licensing.py), [`awx/main/models/events.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/events.py), [`awx/main/models/inventory.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/inventory.py))

## Core Deduplication Use Cases

### 1. Same host automated repeatedly within a billing cycle
`metrics-utility`'s preferred collector, `job_host_summary_service`, reads
`main_jobhostsummary` (one row per host per job run), first filters jobs by
`main_unifiedjob.finished` to reduce volume, then explicitly deduplicates
with `SELECT DISTINCT mjs.host_id ...` against the filtered jobs — so a
host automated hundreds of times in a period is counted once. (A legacy
`job_host_summary` collector filters by `main_jobhostsummary.modified`
instead and is noted in the repo docs as less preferred since it doesn't
align with job completion times.)
(Source: [collectors-and-partitions.md](https://github.com/ansible/metrics-utility/blob/devel/docs/collectors-and-partitions.md))

**"Billing cycle" is a `build_report` CLI parameter, not a fixed setting**
— confirmed against `build_report.py`/`management/validation.py`. For
`CCSP`/`CCSPv2`, `--month` and `--since`/`--until` are **mutually
exclusive** (`validate_ccsp_params()` raises `BadParameter` if both are
given):
- **`--month=YYYY-MM`** — exactly one calendar month. If omitted
  entirely, `handle_month()` silently defaults to **last calendar
  month** — that's the "1 month" behavior you get by doing nothing.
  ```bash
  metrics-utility build_report --month=2025-06
  ```
- **`--since=DATE --until=DATE`** — any custom range, any length: a
  week, a quarter, a full year.
  ```bash
  metrics-utility build_report --since=2025-01-01 --until=2025-12-31
  ```
  (`--until` requires `--since`; `parse_since_until()` also rejects
  `until` earlier than `since`.)

Either path feeds straight into the `job_host_summary_service`
collector's date filter — that's the literal window the
`SELECT DISTINCT mjs.host_id` dedup operates over. **One `build_report`
invocation produces one report for one cycle** — there's no single flag
meaning "billing cycle length"; for quarterly cycles you'd invoke it 4
times with per-quarter `--since`/`--until` bounds.

`RENEWAL_GUIDANCE` works differently: `--month` and `--until` are
explicitly disallowed (`validate_renewal_params()` raises
`BadParameter`), and `--since` is **required**. There, the cycle-length
knob is `--ephemeral` (bucket size within the `--since`-to-now window —
see the How-To section above). Note: the legacy
[`docs/old-readme.md`](https://github.com/ansible/metrics-utility/blob/devel/docs/old-readme.md)
claims `RENEWAL_GUIDANCE` "covers 365 days back by default," but the
current `devel` source raises `MissingRequiredParameter` if `--since` is
omitted — that legacy doc is stale, not current behavior.
(Source: [`build_report.py`](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/management/commands/build_report.py), [`management/validation.py`](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/management/validation.py))

### 2. Same host referenced by multiple values (IP vs. hostname vs. FQDN)
Because uniqueness is based on the literal connection string, an inventory
that reaches the same machine via `10.0.0.5`, `web01`, and
`web01.example.com` will be billed as **three** hosts even though it's one
machine. Red Hat's guidance is explicit that this is not automatically
deduplicated — it's remediated by:
- Cleaning up inventory to remove duplicate references to the same host, or
- Standardizing on the `ansible_host` variable so every reference to a
  given machine resolves to one common value.
(Source: [Managed Active Node Counting](https://access.redhat.com/articles/7088928))

**Same root cause, a subtler trigger: hostname casing.** `metrics-utility`'s
matching is plain-string comparison end to end — the SQL join
(`main_host.name = main_hostmetric.hostname`) and the `RENEWAL_GUIDANCE`
dedup classes (`==`/`.isin()` on `hostname`, `ansible_host_variable`,
`ansible_product_serial`, `ansible_machine_id`) both use case-sensitive
equality, with no `LOWER()`/`ILIKE`/`.casefold()` anywhere in the chain.
**Confirmed empirically** (see `test_renewal_dedup.py`, scenario I):
`WEB05` and `web05` are treated as two entirely separate hosts under
every `RENEWAL_GUIDANCE` deduplicator, unless they also share a common
`ansible_host_variable` or hardware fact — and note that fix is exposed
to the same problem: an `ansible_host` value of `WEB05` set on one entry
and `web05` on another would *also* fail to match, since that value is
compared with the same case-sensitive equality. Inconsistent hostname
casing (common with Windows inventories, or inventories merged from
multiple dynamic sources with different capitalization conventions) will
silently inflate the managed-node count exactly like the IP/hostname/FQDN
case above.

### 3. Same host present in multiple inventories or organizations
`metrics-utility` also snapshots the `main_host` table via its `main_host`
collector (all currently enabled hosts, joined to `main_inventory` and
`main_organization`, no time filter) and a `main_host_daily` variant
(same, but scoped to hosts created/modified in a given window). Per the
repo docs, **neither of these host-snapshot collectors applies its own
`DISTINCT`/dedup logic** — they report enabled hosts as-is per inventory.
The CCSP report layer is what turns this into a deduplicated view: a
per-organization sheet (in addition to the overall `managed_nodes` sheet)
and an `inventory_scope` sheet let reports show where a host is
referenced without inflating the unique-host total across organizational
boundaries.
(Source: [collectors-and-partitions.md](https://github.com/ansible/metrics-utility/blob/devel/docs/collectors-and-partitions.md))

### 4. Directly vs. indirectly managed nodes
`metrics-utility` incrementally collects `main_indirectmanagednodeaudit`,
which tracks **indirectly managed nodes** (e.g., systems touched by
modules/APIs rather than directly connected to). The CCSP report exposes
this as a separate `indirectly_managed_nodes` sheet so indirect automation
isn't silently merged into (or double-counted against) the directly
managed node count.

### 5. API / control-plane automation collapsing to `localhost`
When a job targets a cloud API or control plane rather than a discrete
machine, using a consistent connection scheme of `localhost` means many
operations count as a single managed node rather than one per task or
per API call. This is confirmed for collections such as
`azure.azcollection` and `amazon.aws`, though behavior can vary by
collection. (Source: [Managed Active Node Counting](https://access.redhat.com/articles/7088928))

### 6. Soft-deleted and reinstated hosts (Host Metrics dashboard)
AAP's Host Metrics feature (introduced in 2.4, and the data `metrics-utility`
ultimately reports on) lets admins **soft-delete** hosts — removing them
from the automated-host count — which is intended for ephemeral,
one-shot, or decommissioned hosts that would otherwise inflate the managed
node count. Key related counters:
- **Hosts automated** — counts against the subscription limit.
- **Hosts deleted** — soft-deleted hosts, decrementing the automated count.
- **Active hosts previously deleted** — if a soft-deleted host is
  automated again, it reappears here rather than quietly reducing the
  deletion tally, so reactivation can't be used to permanently undercount
  a host.
- Hosts also **auto soft-delete after 12 months** without updates and are
  **hard-deleted after 36 months**, on a fixed (non-configurable) schedule.
(Sources: [Subscription and Host Metric Changes in AAP 2.4](https://www.redhat.com/en/blog/subscription-and-host-metric-changes-in-ansible-automation-platform-2.4), [How to manage host metrics (managed nodes) in AAP](https://access.redhat.com/solutions/7075449))

This is effectively a deduplication safety valve: it lets genuinely
inactive hosts stop counting, while guaranteeing any host that resumes
activity is re-counted rather than permanently hidden.

### 7. Accurate CCSP / subscription compliance and renewal reporting
All of the above feeds the actual business use case: CCSP and CCSPv2
reports must reflect real, de-duplicated managed infrastructure so
partner billing and Red Hat subscription renewal guidance
(`RENEWAL_GUIDANCE` report type) are neither inflated (over-billing the
customer) nor deflated (compliance risk). The CCSP/CCSPv2 report formats
pull from the collected tarballs; the renewal-guidance report reads
directly from the Controller database, via a `main_hostmetric` collector
that joins `main_hostmetric` to `main_host` (by hostname) and filters on
`last_automation` — i.e., renewal guidance is keyed off the Host Metrics
dashboard data described in use case 6, not a separate counting model.
(Source: [collectors-and-partitions.md](https://github.com/ansible/metrics-utility/blob/devel/docs/collectors-and-partitions.md))

### 8. Hardware-identity-based deduplication (`ansible_product_serial` / `ansible_machine_id`)
For `RENEWAL_GUIDANCE` specifically, the default `renewal` deduplicator
doesn't only match on `hostname`/`ansible_host_variable` — it also
transitively matches on two hardware-identity facts pulled from
`main_host.ansible_facts`: `ansible_product_serial` (DMI/SMBIOS serial,
read from `/sys/devices/virtual/dmi/id/product_serial` or `dmidecode`)
and `ansible_machine_id` (systemd's `/etc/machine-id`, which survives
hostname renames but regenerates on reimage). This is what lets `renewal`
correctly merge a **renamed host** or a host reached via **IP, shortname,
and FQDN with no common `ansible_host_variable`** — cases that
`renewal-hostname` and CCSP-style matching (use case #2) cannot catch on
their own — confirmed empirically via `test_renewal_dedup.py`.

**This has a hard, undocumented prerequisite**: these facts are only
ever written to `main_host.ansible_facts` if a job template with
`use_fact_cache=True` (default: `False`) has actually automated that
host — otherwise the field stays `{}` forever and this entire dedup path
has nothing to match on, regardless of which `RENEWAL_GUIDANCE`
deduplicator you select. It's also **case-sensitive** end to end, same as
every other key metrics-utility matches on. See "Where the Dedup Keys
Actually Come From (and a Prerequisite Nobody Documents)" below for the
full traced mechanism, the confirmed `renewal-experimental`
double-counting bug on multi-hop chains, and a ready-to-run check for
whether fact caching is even in use in your environment.

**Platform-specific behavior — traced directly from each platform's fact
source:**

- **Windows: works the same way, out of the box.** The `ansible.windows`
  collection's `setup.ps1` populates the *exact same fact key names*:
  `ansible_product_serial` comes from `Win32_Bios.SerialNumber` (BIOS/SMBIOS
  serial — same hardware concept as the Linux DMI serial). `ansible_machine_id`
  is different in *kind*, though — it's not a `/etc/machine-id` equivalent,
  it's derived from the local Administrators group SID with the well-known
  `-500` RID suffix stripped (`$user.Sid.AccountDomainSid.Value`). It still
  changes on OS reinstall, but has its own cloning gotcha: **Windows images
  cloned without proper sysprep can share the same machine SID**, which
  would cause metrics-utility to falsely merge two genuinely different
  Windows hosts. Subject to the same `use_fact_cache=True` prerequisite as
  Linux — no special handling needed.
- **Network devices (Cisco IOS, Junos, EOS, etc.): no equivalent — this
  silently does not work at all.** Network OS platforms don't run
  `ansible.builtin.setup` (no general-purpose interpreter to run it
  against); platform-specific `*_facts` modules are used instead, and they
  populate an entirely different, incompatible key namespace. Confirmed
  directly from `cisco.ios`'s facts source — it sets `self.facts["serialnum"]`,
  which becomes `ansible_net_serialnum` once merged into `ansible_facts`
  (the standard `ansible.netcommon` `ansible_net_*` prefix: `ansible_net_serialnum`,
  `ansible_net_model`, `ansible_net_hostname`, `ansible_net_version`, etc.).
  Since metrics-utility's SQL does a literal
  `ansible_facts->>'ansible_product_serial'` / `->>'ansible_machine_id'`
  lookup, this returns `NULL` for **every** network device unconditionally
  — not a fact-caching configuration gap, but a structural blind spot:
  there is no fallback anywhere in metrics-utility that reads
  `ansible_net_serialnum` as a substitute. Network inventory dedup falls
  back entirely to case-sensitive `hostname`/`ansible_host_variable`
  matching, with zero hardware-identity safety net.
  (Sources: [`ansible.windows` `setup.ps1`](https://github.com/ansible-collections/ansible.windows/blob/main/plugins/modules/setup.ps1), [`cisco.ios` legacy facts](https://github.com/ansible-collections/cisco.ios/blob/main/plugins/module_utils/network/ios/facts/legacy/base.py))

### How to Populate Hardware Facts for Dedup (Without Touching Other Job Templates)

Given the `use_fact_cache` prerequisite above, the practical fix is a
**single, dedicated job template** for fact gathering — you do not need
to enable `use_fact_cache` on any of your actual automation job
templates. Confirmed from source: `start_fact_cache()`/`finish_fact_cache()`
only run `if self.should_use_fact_cache()` **for that specific job** —
a job template with `use_fact_cache=False` never reads from or writes
to `main_host.ansible_facts`, so it's fully decoupled from every other
job template's behavior.

**Job template setup:**
1. A minimal playbook is enough — the default `gather_facts: true` (or
   an explicit `ansible.builtin.setup` task) is all that's needed:
   ```yaml
   - hosts: all
     gather_facts: true
     tasks: []
   ```
2. On the job template, enable **"Use Fact Cache."**
3. On Linux targets, reading `/sys/devices/virtual/dmi/id/product_serial`
   often requires root — set `become: true`, or ensure `dmidecode` is
   installed as a fallback. Without this, you'll get the literal string
   `'NA'` instead of a real serial (which metrics-utility already treats
   as null).
4. On Windows targets, `Win32_Bios.SerialNumber` requires the WinRM
   credential to have admin rights on the host.
5. **Run it on a schedule, not just once.** A one-time run only captures
   facts at that moment — the entire point of hardware-identity dedup is
   catching *renamed/rebuilt* hosts, and a host rebuilt after your
   one-time run will never have its new identity captured. A daily or
   weekly scheduled job keeps this current. `RENEWAL_GUIDANCE` has no
   separate gather step of its own (it queries `main_host.ansible_facts`
   live at report-build time), so the very next `build_report` run will
   immediately reflect whatever this job most recently wrote.

**Two caveats this does *not* fix, both documented earlier:**
- **The uppercase-hostname join bug is independent of this.** If a
  host's inventory name contains any uppercase letter,
  `main_hostmetric.py`'s join (`main_host.name = main_hostmetric.hostname`)
  still won't match — `main_hostmetric.hostname` is always lowercased by
  AAP while `main_host.name` is not (see "Does AAP Itself Deduplicate?"
  above). Running this job will correctly populate `ansible_facts` on
  the `Host` row, but metrics-utility still won't be able to retrieve it
  for that host via the collector's join.
- **Multi-inventory duplicate-name fan-out.** `Host` uniqueness is
  `(name, inventory)`, not global. If the same hostname exists in two
  different inventories, the collector's join has no inventory scoping
  and can produce two rows for one `main_hostmetric` record — worth
  checking for if your inventory structure has overlapping hostnames
  across inventories.

## Summary

| Scenario | Without Deduplication | With Deduplication / Mitigation |
|---|---|---|
| Host automated many times in a cycle | Counted once per job run | Counted once per billing cycle (`main_jobhostsummary` rollup) |
| Host reached via IP, hostname, and FQDN | Counted as 3 separate hosts | Counted as 1, if inventory is cleaned up or `ansible_host` is standardized |
| Same host, inconsistent hostname casing (`WEB05` vs `web05`) | Counted as 2 separate hosts (confirmed, all matching is case-sensitive) | Counted as 1, only if casing is standardized in inventory (case-sensitive `ansible_host`/facts don't help either) |
| Renamed host, or IP/shortname/FQDN with no shared `ansible_host_variable` (RENEWAL_GUIDANCE) | Counted as 2+ separate hosts under `renewal-hostname` | Counted as 1 under default `renewal`, but **only if** `ansible_product_serial`/`ansible_machine_id` were actually captured (requires `use_fact_cache=True` on some job template) |
| Host in multiple inventories/orgs | Risk of inflated totals | Broken out via `inventory_scope` / per-org sheets |
| Indirectly managed nodes | Merged into direct count | Tracked separately via `indirectly_managed_nodes` sheet |
| API/control-plane calls | Counted per task/call | Collapsed to one host via consistent `localhost` connection |
| Host soft-deleted then reused | Could stay uncounted | Reappears as "active previously deleted," recounted |

## How-To: Discrete Node Count Over Time for a Renewal Conversation

The `RENEWAL_GUIDANCE` report type exists specifically for this: it reads
directly from the Controller DB's `HostMetric` table (**no gather step
needed** — nothing is written under `METRICS_UTILITY_SHIP_PATH` except the
final report) and applies deduplication to produce real historical
discrete-node usage. Red Hat's own docs mark it a **tech preview**, framed
as more informative than `awx-manage host_metric`, not a replacement for
AAP's official subscription compliance numbers — treat it as internal
renewal prep, and confirm with your Red Hat account team whether they want
this artifact or their own compliance report as the source of truth.

**Choosing a deduplication strategy** (`METRICS_UTILITY_DEDUPLICATOR`):
The dedup implementation is picked by a factory keyed on **both**
`METRICS_UTILITY_DEDUPLICATOR` and `METRICS_UTILITY_REPORT_TYPE`
(`metrics_utility/automation_controller_billing/dedup/factory.py`), and
`ccsp`/`ccsp-experimental` are **hard-restricted to `CCSP`/`CCSPv2`** —
using either with `RENEWAL_GUIDANCE` raises `KeyError: 'main_host'`,
because that dedup path expects a `main_host` dataframe that only exists
in the CCSP/CCSPv2 tarball-based flow. For `RENEWAL_GUIDANCE`, use one of:
- *(unset)* — defaults to `renewal` automatically for `RENEWAL_GUIDANCE`.
- `renewal` — default renewal dedup.
- `renewal-hostname` — hostname-based dedup, `RENEWAL_GUIDANCE`-only.
- `renewal-experimental` — more aggressive hardware/identity-based dedup
  (the `RENEWAL_GUIDANCE` analog of `ccsp-experimental`),
  `RENEWAL_GUIDANCE`-only.
(Source: [factory.py](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dedup/factory.py))

**Generic command shape** (env vars + `build_report`):
```bash
export METRICS_UTILITY_SHIP_TARGET=controller_db
export METRICS_UTILITY_REPORT_TYPE=RENEWAL_GUIDANCE
export METRICS_UTILITY_SHIP_PATH="./out"
export METRICS_UTILITY_DEDUPLICATOR=renewal   # or renewal-hostname / renewal-experimental

metrics-utility build_report --since=12months --ephemeral=1month --force
```
- `--since=12months` — how far back to look (defaults to 365 days back if
  omitted).
- `--ephemeral=1month` — buckets the discrete-node count into monthly
  slices, giving a month-by-month trend line of unique managed nodes
  rather than one flat number across the whole window — the shape you
  want for a renewal conversation.
- `--force` — regenerate rather than reuse cached output.

### Variant: Containerized Deployment (podman/docker-compose install)
In AAP's containerized install type, `metrics-utility` ships inside the
`automation-controller-task` container — there's no bare host shell with
it on `$PATH`. You must exec into that container, and you need root or
the `awx` user (it requires read access to `/etc/tower/SECRET_KEY`; a
regular user hits a `PermissionError`).

```bash
podman exec -it \
  -e METRICS_UTILITY_SHIP_TARGET=controller_db \
  -e METRICS_UTILITY_REPORT_TYPE=RENEWAL_GUIDANCE \
  -e METRICS_UTILITY_SHIP_PATH=/var/lib/awx/metrics-utility/out \
  -e METRICS_UTILITY_DEDUPLICATOR=renewal \
  automation-controller-task \
  metrics-utility build_report --since=12months --ephemeral=1month --force
```
Note: the target output directory must already exist inside the
container and be writable by whichever user runs the command — the tool
does not create it for you (`Invalid METRICS_UTILITY_SHIP_PATH: ... is
not an existing directory`). Create/chown it first, e.g.:
```bash
podman exec automation-controller-task mkdir -p /var/lib/awx/metrics-utility/out
podman exec automation-controller-task chown awx:awx /var/lib/awx/metrics-utility/out
```

Copy the generated report back out of the container afterward:
```bash
podman cp automation-controller-task:/var/lib/awx/metrics-utility/out/<generated-file>.xlsx ./
```

Verify before running:
1. Container name confirmed for this environment: `automation-controller-task`
   — check `podman ps` if you're working against a different environment,
   since this varies by install inventory naming.
2. Confirm the write path exists/is writable in that container, or bind-
   mount a host directory to it so `podman cp` isn't needed.
3. Run as root, or `podman exec --user awx ...`, to avoid the
   `SECRET_KEY` permission error.
(Source: [Chapter 12. Usage reporting with metrics-utility — AAP 2.5 Documentation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/configuring_automation_execution/metrics-utility) *(via search summary — direct fetch blocked, see caveat)*)

### Variant: OpenShift / Operator-based Deployment
On an Operator-managed (OpenShift/Kubernetes) install, the equivalent
target is the task pod, exec'd via `oc`/`kubectl` instead of `podman`.
Default storage for output in this deployment mode is a path on the
attached Persistent Volume Claim rather than local container disk.
The `automation-controller-task` container name below is confirmed only for
the podman-based deployment above — it is **not confirmed for OpenShift**;
verify it first with
`oc get pod <pod> -o jsonpath='{.spec.containers[*].name}'`.

```bash
oc exec -it deployment/<controller-instance>-task \
  -c automation-controller-task -- bash -c '
    export METRICS_UTILITY_SHIP_TARGET=controller_db
    export METRICS_UTILITY_REPORT_TYPE=RENEWAL_GUIDANCE
    export METRICS_UTILITY_SHIP_PATH=/var/lib/awx/metrics-utility/out
    export METRICS_UTILITY_DEDUPLICATOR=renewal
    mkdir -p "$METRICS_UTILITY_SHIP_PATH"
    metrics-utility build_report --since=12months --ephemeral=1month --force
  '
```

Then copy the report out via `oc cp`:
```bash
oc cp <task-pod-name>:/var/lib/awx/metrics-utility/out/<generated-file>.xlsx ./ -c automation-controller-task
```

Verify before running:
1. Get the actual task pod/deployment name with `oc get pods` (or
   `kubectl get pods -n <namespace>`) — naming depends on your Operator
   resource name.
2. Confirm `METRICS_UTILITY_SHIP_PATH` points at a location on the PVC
   that's actually mounted into that pod, since local container disk may
   not persist or may not be where you expect.
3. `oc rsh <pod>` is a viable alternative to `oc exec -it ... -- bash` if
   your `oc` version/RBAC setup makes that simpler.

## What Exactly Gets Deduplicated for RENEWAL_GUIDANCE (and How to Test It)

`RENEWAL_GUIDANCE` dedup is implemented in
[`dedup/renewal_guidance.py`](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dedup/renewal_guidance.py)
against the `HostMetric` table (fields: `hostname`, `ansible_host_variable`,
`ansible_product_serial`, `ansible_machine_id`, `deleted`,
`first_automation`, `last_automation`, `automated_counter`,
`deleted_counter`, `last_deleted`). Placeholder nulls (`'NA'`, `''`) are
scrubbed to `None` before matching, so two hosts that both merely lack a
serial are never treated as a match on that basis.

The following table and findings were **empirically verified** by running
the actual upstream classes against synthetic fixtures (see
`test_renewal_dedup.py` in this directory), not just read from source.

### `renewal` (default)
Iteratively expands a duplicate group by transitively following shared
values of `hostname`, `ansible_host_variable`, `ansible_product_serial`,
and `ansible_machine_id` — up to `REPORT_RENEWAL_GUIDANCE_DEDUP_ITERATIONS`
hops (**default: 3**, per `build_report.py`). Confirmed to correctly
collapse into a single host:
- The same hostname repeated across multiple `HostMetric` rows.
- Multiple hostnames (IP / short name / FQDN) sharing one
  `ansible_host_variable`.
- A renamed/rebuilt host with a new hostname but the same
  `ansible_machine_id`.
- A 3-node chain where host A and B share only `ansible_product_serial`,
  and B and C share only `ansible_machine_id` — i.e., A and C have *no*
  attribute directly in common, but the transitive walk still merges all
  three into one group.
Confirmed it correctly does **not** merge two hosts whose only "shared"
values are cleaned-up placeholders (`'NA'`/`''`).

### `renewal-hostname`
Matches strictly on `ansible_host_variable` (falling back to `hostname`
when absent) — a single-key exact match, no transitive expansion.
Confirmed it **does** merge the IP/short-name/FQDN case (they share one
`ansible_host_variable`), but **does not** merge the renamed-host or
transitive-chain cases from above, since those hosts share no hostname or
`ansible_host_variable` value.

### `renewal-experimental` — confirmed bug on multi-hop mixed-key chains
Runs `renewal-hostname` first, then a second pass merging hostname-groups
that share a `product_serial`/`machine_id` compound or individual key.
This correctly recovers the renamed-host/`machine_id` case that
`renewal-hostname` alone misses. **However, on the 3-node mixed-key chain
(A↔B via serial, B↔C via machine_id), it produced two overlapping merged
groups — `[A, B]` and `[B, C]` — with host B counted in both**, instead of
one fully merged group of 3. This is genuine double-counting, not just a
documented limitation, and was reproduced directly by running the shipped
code. Do not use `renewal-experimental` for a renewal headcount if your
data plausibly contains multi-hop chains linked through different
identifier types; use the default `renewal` deduplicator instead, which
handles this case correctly.

### How to test this yourself (or re-test after an AAP upgrade)
Two files ship alongside this readme:
- `renewal_guidance.py` — the exact upstream dedup source (unmodified,
  fetched from the `devel` branch).
- `test_renewal_dedup.py` — a fixture-based harness that imports the real
  `DedupRenewal`, `DedupRenewalHostname`, and `DedupRenewalExperimental`
  classes (no Django or database required — just `pandas`) and runs them
  against nine scenarios: exact-hostname duplicate, shared
  `ansible_host_variable`, renamed host sharing `machine_id`, a 3-way
  transitive chain, an independent control host, null-placeholder values
  that must *not* match, IP/shortname/FQDN records for the same machine
  both **without** and **with** a shared `ansible_machine_id` fact, and
  a same-host-different-case (`WEB05` vs `web05`) pair. It prints each
  strategy's output and asserts the behaviors
  confirmed above, including that IP/shortname/FQDN records with no
  `ansible_host_variable` and no shared hardware fact do **not** merge
  under any strategy.

Run it locally:
```bash
cd metrics_utility_review
python3 -m pip install --user pandas   # if not already available
python3 test_renewal_dedup.py
```

To validate against your **actual installed version** (dedup logic can
change between AAP releases — don't assume the `devel` branch copy here
matches your production version), pull the real file out of your
container first and overwrite the bundled copy before running the test:
```bash
podman cp automation-controller-task:/var/lib/awx/venv/awx/lib64/python3.12/site-packages/metrics_utility/automation_controller_billing/dedup/renewal_guidance.py ./renewal_guidance.py
python3 test_renewal_dedup.py
```
(On an OpenShift/Operator deployment, use `oc cp <task-pod>:<same path> ./renewal_guidance.py -c automation-controller-task` instead.)

### Live Validation on Real AAP Infrastructure

`test_renewal_dedup.py` confirms this logic against synthetic fixtures.
The table below is the same behavior confirmed **live**, on a real
containerized AAP instance, using the cross-inventory test design from
[`TESTING.md`](TESTING.md) (Phases 3.5/4/7): the same VM tracked as two
separate `Host` objects in two separate inventories — `demo` (a
hand-named entry) and `central` (an EC2 dynamic inventory source, synced
under the raw public DNS hostname) — with three deliberately different
combinations of shared identifiers:

| Scenario | Shared `ansible_host`? | Shared `machine_id`? | Expected | Observed |
|---|---|---|---|---|
| `metrics_rhel9_3` ↔ `ec2-18-117-241-37...` | No | Yes | Merge via `machine_id` | ✅ Merged (`hostmetric_record_count=2`) |
| `metrics_win_1` ↔ `ec2-3-129-12-48...` | No | Yes | Merge via `machine_id` | ✅ Merged (`hostmetric_record_count=2`) |
| `metrics_win_2` ↔ `ec2-3-141-10-16...` | Yes | No | Merge via `ansible_host` | ✅ Merged (`hostmetric_record_count=2`) |

All three merged as predicted, and the design isolates the two matching
mechanisms cleanly: the first two rows prove hardware-identity matching
(use case #8) works with **zero** help from `ansible_host` (neither side
of those pairs shares one), while the third proves `ansible_host_variable`
matching (use case #2) works with **zero** help from hardware facts,
since `ec2-3-141-10-16...` has no `machine_id` populated at all. This is
the same `renewal` deduplicator, the same transitive-matching code, doing
on real infrastructure exactly what the fixtures predicted.

Raw `Managed nodes` sheet output, parsed with the CSV-aware viewer from
`TESTING.md` (Phase 6) rather than `column -s, -t`, which mis-splits this
data — see `hostnames` and `Serial Numbers`/`Machine UUIDs`, which are
themselves comma-joined lists:

```
Host name                                        First automation            Last automation             Number of Automations  ...  Host names                                                          Variables ansible_host          Serial Numbers                        Machine UUIDs
metrics_rhel9_3                                  2026-09-01 14:21:43.118000  2026-09-01 15:27:23.063000  4                      ...  metrics_rhel9_3, ec2-18-117-241-37.us-east-2.compute.amazonaws.com  18.117.241.37                   ec2ba8b7-51d4-d0a0-74d7-cc1065d6727b  ec2ba8b751d4d0a074d7cc1065d6727b
ec2-3-129-12-48.us-east-2.compute.amazonaws.com  2026-09-01 13:59:20.038000  2026-09-01 15:58:39.430000  4                      ...  metrics_win_1, ec2-3-129-12-48.us-east-2.compute.amazonaws.com      3.129.12.48                     ec259b7a-b283-4459-daff-9fed84971ef6  S-1-5-21-4100766907-1347740291-2814610555
ec2-3-141-10-16.us-east-2.compute.amazonaws.com  2026-09-01 13:59:20.038000  2026-09-01 16:45:28.780000  2                      ...  ec2-3-141-10-16.us-east-2.compute.amazonaws.com, metrics_win_2      3.141.10.16                                                                                                    
ip-172-31-2-120.us-east-2.compute.internal       2025-07-07 21:24:56.312000  2026-08-12 19:29:20.873000  246                    ...  ip-172-31-2-120.us-east-2.compute.internal                                                                                                6508a74bf54348d3b99307a1df849adf
localhost                                        2025-06-30 17:39:28.922000  2026-09-01 14:19:39.228000  1776                   ...  localhost                                                                                                                                 990ff18f0daf4a578f5bfecaf8bc53ad
metrics_rhel8_4                                  2026-09-01 14:21:43.118000  2026-09-01 14:21:43.117000  1                      ...  metrics_rhel8_4                                                     18.219.185.242
metrics_rhel9_1                                  2026-09-01 14:07:15.884000  2026-09-01 14:21:43.117000  4                      ...  metrics_rhel9_1                                                     3.142.238.21                    ec2fd2ae-c188-1a4b-bc41-caa0c8cd0e5b  ec2fd2aec1881a4bbc41caa0c8cd0e5b
metrics_rhel9_2                                  2026-09-01 14:07:15.884000  2026-09-01 14:21:43.117000  4                      ...  metrics_rhel9_2                                                     18.191.194.75                   ec222231-778f-cb0d-0178-f30e8d513452  ec222231778fcb0d0178f30e8d513452
metrics_rhel9_4                                  2026-09-01 14:21:43.118000  2026-09-01 14:21:43.117000  1                      ...  metrics_rhel9_4                                                     3.15.185.84
wincerttest3                                     2026-05-14 22:31:08.893000  2026-08-24 17:10:01.152000  30                     ...  wincerttest3                                                        3.144.171.204, 18.119.163.152
wincerttest4                                     2026-05-26 14:43:33.416000  2026-08-24 17:10:01.152000  18                     ...  wincerttest4                                                        18.223.188.220, 18.222.114.117
```

The first three rows are the Phase 3.5/7 test pairs (already merged, one
row each). Everything below them (`ip-172-31-2-120...`, `localhost`,
`metrics_rhel8_4`, `metrics_rhel9_1`/`_2`/`_4`, `wincerttest3`/`4`) is
pre-existing, unrelated infrastructure in the same AAP instance — expected
to show up here since `RENEWAL_GUIDANCE` reports on the whole
environment's `HostMetric` history, not just a filtered test set. Note
that `metrics_rhel9_1` and `metrics_rhel9_2` show real `Serial
Numbers`/`Machine UUIDs` values here too — a different job template
against them happened to have "Use Fact Cache" enabled, independent of
the Phase 3.5/7 test design above.

## Where the Dedup Keys Actually Come From (and a Prerequisite Nobody Documents)

Traced directly from source, not inferred:

1. **`ansible_product_serial`** is gathered by Ansible's Linux hardware
   fact collector from `/sys/devices/virtual/dmi/id/product_serial`,
   falling back to `dmidecode -s system-serial-number`. **If the
   `dmidecode` binary isn't installed, this (and every other DMI field)
   is hardcoded to the literal string `'NA'`** — which is exactly why
   `metrics-utility` explicitly treats `'NA'` as null before matching.
   (Source: [`hardware/linux.py`](https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/facts/hardware/linux.py))
2. **`ansible_machine_id`** is read from `/var/lib/dbus/machine-id`,
   falling back to `/etc/machine-id` — systemd's per-OS-install ID. It
   survives hostname renames, but **regenerates on reimage**, and
   **cloned VMs from the same template can share one** unless something
   (cloud-init, `systemd-machine-id-setup --commit`) resets it on first
   boot.
   (Source: [`system/platform.py:92`](https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/facts/system/platform.py))
3. Neither field lives on `main_hostmetric` — that table only has
   `hostname`, `first_automation`, `last_automation`, `automated_counter`,
   `deleted_counter`, `deleted`, `last_deleted`, `used_in_inventories`
   (confirmed against the live `HostMetric` model). Both facts actually
   live in **`main_host.ansible_facts`**, a JSONB column on the live
   inventory Host row.
4. `metrics-utility`'s `main_hostmetric` collector pulls them in via
   `LEFT JOIN main_host ON main_host.name = main_hostmetric.hostname`,
   then `main_host.ansible_facts->>'ansible_product_serial'` /
   `->>'ansible_machine_id'` (and parses `ansible_host` out of
   `main_host.variables`).
   (Source: [`main_hostmetric.py`](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/library/collectors/controller/main_hostmetric.py))

### The prerequisite: "Use Fact Cache" must be enabled somewhere
`main_host.ansible_facts` is **only** written by Controller's fact-cache
write-back path (`finish_fact_cache()`), which only runs at all if the
job template that ran has `use_fact_cache=True` — a field that
**defaults to `False`**:
```python
use_fact_cache = models.BooleanField(
    default=False,
    help_text="If enabled, the service will act as an Ansible Fact Cache "
              "Plugin; persisting facts at the end of a playbook run to "
              "the database and caching facts for use by Ansible.",
)
```
(Source: [`awx/main/models/jobs.py:154`](https://github.com/ansible/awx/blob/devel/awx/main/models/jobs.py), gating confirmed in [`awx/main/tasks/jobs.py:1276-1369`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/jobs.py) and the write itself in [`awx/main/tasks/facts.py`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/facts.py))

If `use_fact_cache` was never enabled on any job template that automated
a host, **`ansible_facts` for that host stays `{}` forever** — Ansible
still gathers facts in-memory during the run, but nothing writes them
back to the Controller database. Practically: `renewal` and
`renewal-experimental` will then behave identically to
`renewal-hostname` for that host, regardless of which one you selected,
because there's no hardware-identity data for them to match on.

**This specific dependency is not documented anywhere.** The "Use Fact
Cache" job template setting is documented in the [AWX/Automation
Controller Job Templates user guide](https://docs.ansible.com/projects/awx/en/24.6.1/userguide/job_templates.html)
(confirms it's off by default, and that hostnames containing `/` break
fact caching for that host). But nothing in `metrics-utility`'s docs or
Red Hat's metrics-utility chapter says the `RENEWAL_GUIDANCE` hardware
dedup depends on it — that link only surfaces by reading both codebases.

### Quick check: is fact caching even in use in your environment?
Run this from the same container you build reports in:
```bash
podman exec -it automation-controller-task awx-manage shell -c "
from awx.main.models import Host, JobTemplate
print('Job templates with use_fact_cache=True:', JobTemplate.objects.filter(use_fact_cache=True).count())
print('Hosts with any cached facts:', Host.objects.exclude(ansible_facts={}).count())
print('Hosts with product_serial or machine_id fact populated:',
      Host.objects.filter(ansible_facts__has_any_keys=['ansible_product_serial', 'ansible_machine_id']).count())
"
```
If the first number is 0, hardware-based renewal dedup has no data to
work with anywhere in your environment, and you should rely on
`ansible_host_variable` standardization instead (see the
"Same host referenced by multiple values" use case above) rather than
expecting `renewal`/`renewal-experimental` to catch IP/shortname/FQDN
duplicates on their own.

### Direct SQL check for a specific host
To check one particular host by name, query `main_host` directly via
`awx-manage dbshell` — this reuses Controller's own configured DB
connection, so it works whether Postgres runs in a separate container,
a Pod, or an external managed DB, without you needing to know its
credentials or hostname:
```bash
podman exec -it automation-controller-task awx-manage dbshell -- -c "
SELECT name,
       ansible_facts ? 'ansible_product_serial' AS has_product_serial,
       ansible_facts->>'ansible_product_serial' AS product_serial,
       ansible_facts ? 'ansible_machine_id' AS has_machine_id,
       ansible_facts->>'ansible_machine_id' AS machine_id,
       ansible_facts_modified
FROM main_host
WHERE name = 'YOUR_HOSTNAME_HERE';
"
```
- `ansible_facts ? 'key'` is Postgres's JSONB "does this key exist"
  operator — useful because a key can exist and be null/`'NA'` versus
  not exist at all (never gathered).
- `ansible_facts_modified` tells you when (if ever) this host's fact
  cache was last written — `NULL` means `finish_fact_cache()` has never
  run for this host, i.e., `use_fact_cache` was never enabled on any job
  template that touched it.
- To check several hostnames at once (e.g., the IP/shortname/FQDN
  variants of one machine), swap the `WHERE` clause for
  `WHERE name IN ('10.0.0.5', 'web02', 'web02.example.com')` and eyeball
  whether they resolve to the same `product_serial`/`machine_id`.

If you don't have (or don't want to grant) `awx-manage dbshell` access,
and instead know the Postgres container name directly, the equivalent
raw `psql` form is:
```bash
podman exec -it automation-controller-postgres psql -U awx -d awx -c "
SELECT name, ansible_facts->>'ansible_product_serial' AS product_serial,
       ansible_facts->>'ansible_machine_id' AS machine_id
FROM main_host WHERE name = 'YOUR_HOSTNAME_HERE';
"
```
(Container name, DB name, and DB user vary by install — check
`podman ps` and your install inventory if `automation-controller-postgres`
/ `awx` / `awx` don't match your environment.)

## Practical Guidance

- Standardize how inventories reference hosts (prefer one canonical
  `ansible_host` value per machine, **with consistent casing**) before
  relying on `metrics-utility` output for billing decisions — matching is
  case-sensitive throughout, so `WEB05`/`web05` won't merge even if you
  otherwise standardize on `ansible_host`.
- Use the Host Metrics dashboard's soft-delete for genuinely ephemeral or
  decommissioned hosts — not as a way to manipulate compliance numbers
  (Red Hat's own guidance explicitly warns against this).
- Review the `inventory_scope` and `indirectly_managed_nodes` sheets in
  CCSP/CCSPv2 output, not just `managed_nodes`, to understand the full
  picture behind a reported host count.
- For `RENEWAL_GUIDANCE` specifically, use the default `renewal`
  deduplicator, not `renewal-experimental` — see the confirmed
  double-counting issue above — and run `test_renewal_dedup.py` against
  your actual installed `renewal_guidance.py` before presenting numbers
  externally.
- Before trusting hardware-identity-based dedup (`ansible_product_serial`
  / `ansible_machine_id`) at all, run the "Quick check" query above to
  confirm any job template has `use_fact_cache=True` and that
  `main_host.ansible_facts` is actually populated for your hosts — if
  not, renewal dedup is silently degraded to hostname/`ansible_host`
  matching only, no matter which deduplicator you set.

## Sources

- [ansible/metrics-utility (GitHub)](https://github.com/ansible/metrics-utility)
- [Managed Active Node Counting — Red Hat Customer Portal](https://access.redhat.com/articles/7088928)
- [`awx/main/utils/licensing.py` (native compliance count) — ansible/awx](https://github.com/ansible/awx/blob/devel/awx/main/utils/licensing.py)
- [`awx/main/models/events.py` (`HostMetric` write path, `.lower()` normalization) — ansible/awx](https://github.com/ansible/awx/blob/devel/awx/main/models/events.py)
- [`awx/main/models/inventory.py` (`HostMetric`/`Host` model definitions) — ansible/awx](https://github.com/ansible/awx/blob/devel/awx/main/models/inventory.py)
- [Subscription and Host Metric Changes in Ansible Automation Platform 2.4 — Red Hat Blog](https://www.redhat.com/en/blog/subscription-and-host-metric-changes-in-ansible-automation-platform-2.4)
- [How to manage host metrics (managed nodes) in AAP — Red Hat Customer Portal](https://access.redhat.com/solutions/7075449)
- [Turning Automation into Insights: Ansible's metrics-utility — Red Hat Customer Portal](https://access.redhat.com/articles/7127789)
- [Chapter 12. Usage reporting with metrics-utility — AAP 2.5 Documentation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/configuring_automation_execution/metrics-utility) *(blocked direct fetch, see caveat below)*
- [collectors-and-partitions.md — ansible/metrics-utility (devel branch)](https://github.com/ansible/metrics-utility/blob/devel/docs/collectors-and-partitions.md)
- [dedup/factory.py — ansible/metrics-utility (devel branch)](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dedup/factory.py)
- [dedup/renewal_guidance.py — ansible/metrics-utility (devel branch)](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dedup/renewal_guidance.py) — bundled as `renewal_guidance.py` in this directory, verified via `test_renewal_dedup.py`
- [main_hostmetric.py collector — ansible/metrics-utility (devel branch)](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/library/collectors/controller/main_hostmetric.py)
- [`hardware/linux.py` (ansible_product_serial / DMI facts) — ansible/ansible](https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/facts/hardware/linux.py)
- [`system/platform.py` (ansible_machine_id) — ansible/ansible](https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/facts/system/platform.py)
- [`awx/main/models/jobs.py` (`use_fact_cache` field) — ansible/awx](https://github.com/ansible/awx/blob/devel/awx/main/models/jobs.py)
- [`awx/main/tasks/facts.py` (`finish_fact_cache` write-back) — ansible/awx](https://github.com/ansible/awx/blob/devel/awx/main/tasks/facts.py)
- [AWX/Automation Controller Job Templates user guide — "Use Fact Cache"](https://docs.ansible.com/projects/awx/en/24.6.1/userguide/job_templates.html)
- [`build_report.py` (`--month`/`--since`/`--until`/`--ephemeral` handling) — ansible/metrics-utility (devel branch)](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/management/commands/build_report.py)
- [`management/validation.py` (per-report-type CLI validation) — ansible/metrics-utility (devel branch)](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/management/validation.py)

## Notes / Caveats

Most host-deduplication specifics in this document (collector names, the
`SELECT DISTINCT mjs.host_id` logic, `main_host`/`main_host_daily`/
`main_hostmetric` behavior) are pulled directly from the `metrics-utility`
repo's own `docs/collectors-and-partitions.md` on the `devel` branch —
treat that as the primary source of truth, and re-check it if you're on
an older release, since collector logic can change between versions.

`docs.redhat.com`'s official metrics-utility chapter still returns HTTP 403
to automated fetches (a site-level bot block, not a missing/moved page),
so CCSP/CCSPv2 report-sheet names (`managed_nodes`, `indirectly_managed_nodes`,
`inventory_scope`) and report-type names came from search-engine summaries
of that page rather than the primary text. If you need those confirmed
verbatim, open that URL in a browser directly.
