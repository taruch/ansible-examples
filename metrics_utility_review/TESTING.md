# Live Validation Runbook: `metrics-utility` Host Deduplication

This is a repeatable runbook for validating the claims in [`README.md`](README.md)
against a real AAP containerized deployment, rather than just the synthetic
fixtures in [`test_renewal_dedup.py`](test_renewal_dedup.py). It assumes:

- A containerized AAP deployment, task container named `automation-controller-task`
  (adjust if yours differs — check with `podman ps`).
- Test instances provisioned, hostnames starting with `metrics`, added to
  the AAP demo inventory, which has been synced: 2 RHEL9 + 2 Windows for
  Phases 1-6, plus 3 additional RHEL nodes (one RHEL8-based) held in
  reserve, untouched by fact caching, specifically for the Phase 3.5/7
  before/after causation test — that test depends on starting from hosts
  with zero `ansible_facts`, so it needs its own clean nodes rather than
  reusing ones already exercised elsewhere in the runbook.
- A basic connectivity check (e.g. `ansible.builtin.ping` / `win_ping`) has
  been run against the 2 RHEL9 + 2 Windows hosts **as an actual Job
  Template**, not as an ad-hoc "Run Command" from the Inventory page — see
  the note in Phase 1 for why that distinction matters. (If that job
  template happens to have "Use Fact Cache" enabled, that's fine for
  Phases 1-3, which only need `HostMetric` rows — just don't run it
  against the reserved RHEL nodes before Phase 3.5.)

Each phase below states what it validates, references the relevant README
section, gives the exact command, and states the expected result so you can
tell a pass from a fail without re-deriving the logic each time.

---

## Phase 0 — Record what you actually have

Before running anything, record the **exact** hostnames as they appear in
your inventory (`main_host.name`), including casing — you'll need this
for the Phase 2 comparison. Every query in this runbook uses this same
combined filter, so it always picks up both the `metrics*`-named hosts
and the Phase 3.5 cross-inventory host (synced under a raw EC2 public DNS
name like `ec2-18-117-241-37.us-east-2.compute.amazonaws.com`) regardless
of which of them already exist at that point in the sequence:

```bash
podman exec -it automation-controller-task awx-manage dbshell -- -c "
SELECT name FROM main_host
WHERE name ILIKE 'metrics%'
   OR name ILIKE '%compute.amazonaws%';
"
```

Also note whether your 2 RHEL and 2 Windows instances were cloned from the
same base image/template respectively — this matters for Phase 5.

---

## Phase 1 — Baseline: did the ping run populate `HostMetric`?

**Validates:** README → "Does AAP Itself Deduplicate?" — that `HostMetric`
rows are created from playbook-based Job Template runs, and that AAP
lowercases hostnames on write (`awx/main/models/events.py:583-584`).

> **Important:** Running "ping" as an **ad-hoc command from the
> Inventory/Hosts page** ("Run Command") does **not** populate
> `HostMetric` — regardless of module used. `HostMetric` is only ever
> updated by `_update_host_metrics()`, which is defined on `JobEvent` (a
> subclass of `BasePlaybookEvent` — actual Job Template/playbook runs).
> Ad-hoc commands use a completely separate class, `AdHocCommandEvent`,
> which inherits from `BaseCommandEvent` instead and never calls that
> method — same is true for inventory syncs (`InventoryUpdateEvent`) and
> system jobs (`SystemJobEvent`). **Run an actual Job Template** (a
> playbook containing a `ping`/`win_ping` task, e.g. the AAP "Demo Job
> Template") against these hosts for this phase to produce any rows at all.
> (Source: [`awx/main/models/events.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/events.py) — `JobEvent` class ~line 470, `_update_host_metrics` ~line 596, vs. `AdHocCommandEvent`/`BaseCommandEvent` ~line 668-865.)

```bash
podman exec -it automation-controller-task awx-manage dbshell -- -c "
SELECT hostname, first_automation, last_automation, automated_counter, deleted
FROM main_hostmetric
WHERE hostname ILIKE 'metrics%'
   OR hostname ILIKE '%compute.amazonaws%'
ORDER BY hostname;
"
```

**Expected:** 4 rows, `automated_counter` >= 1, `deleted=false`, and every
`hostname` value is **all lowercase** regardless of how you typed the
inventory hostname — this is the live confirmation of AAP's native
`.lower()` normalization. If this returns 0 rows, confirm you ran an
actual Job Template (not an ad-hoc "Run Command") against these hosts.

- [ ] Ran an actual Job Template (not ad-hoc "Run Command") against the 4 hosts
- [ ] 4 rows returned
- [ ] All `hostname` values lowercase

---

## Phase 2 — Check hostname casing (does the join bug apply to you?)

**Validates:** README → use case #8 / "Where the Dedup Keys Actually Come
From" — the `main_host.name = main_hostmetric.hostname` join is exact-match
and case-sensitive, but only `main_hostmetric.hostname` is lowercased.

Compare the `main_host.name` values recorded in Phase 0
**character-for-character** against the matching `hostname` values from
Phase 1.

- [ ] All 4 match exactly (all-lowercase inventory names) → join bug does
      not apply to these hosts, skip ahead expecting clean results in Phase 4.
- [ ] One or more differ in casing → **note which hosts** — expect their
      `ansible_facts` lookup to return `NULL` in Phase 4 even after a
      successful fact-gather, since the collector's join will silently miss
      them.

---

## Phase 3 — Confirm facts are currently empty

**Validates:** README → "The prerequisite: Use Fact Cache must be enabled
somewhere" — `ping` never gathers facts, so `ansible_facts` should still be
untouched.

```bash
podman exec -it automation-controller-task awx-manage dbshell -- -c "
SELECT name, ansible_facts_modified,
       ansible_facts->>'ansible_product_serial' AS product_serial,
       ansible_facts->>'ansible_machine_id' AS machine_id
FROM main_host
WHERE name ILIKE 'metrics%'
   OR name ILIKE '%compute.amazonaws%';
"
```

**Expected:** `ansible_facts_modified` is `NULL` for all 4 rows. This is
your "before" snapshot.

- [ ] All 4 rows show `ansible_facts_modified = NULL`

---

## Phase 3.5 — Baseline: Prove `machine_id` Populating *Causes* a Behavior Change

**Why this phase exists:** Phases 4-6 on their own only show that facts
get populated and that `RENEWAL_GUIDANCE` picks them up — they don't
prove *causation*. To demonstrate that having `machine_id` populated
changes what metrics-utility does (not just that it exists), you need a
duplicate-reference case, and you need to see it **fail** to merge first,
so the later merge can't be coincidental or explained by something else
(e.g. a shared `ansible_host_variable`).

**The test case is cross-inventory.** The scenario this validates: the
*same* underlying VM tracked as **two separate `Host` objects in two
separate inventories**, under two completely different names — e.g.
`metrics_rhel9_x` in the **demo inventory** vs. its raw cloud-provider
hostname (e.g. `ec2-18-117-241-37.us-east-2.compute.amazonaws.com`) as
synced into a **central inventory** (an EC2 dynamic inventory source,
most likely). There is no shared `hostname` and no shared
`ansible_host_variable` between these two — the *only* thing that could
ever link them is matching `ansible_product_serial`/`ansible_machine_id`.
This is the exact real-world case use case #8 exists for.

**Important operational detail:** `main_host.ansible_facts` is per `Host`
row, i.e. per inventory. Since this VM is two separate `Host` objects
(one per inventory), running a fact-gathering job against the demo
inventory does **not** touch the `central` inventory's `Host` row for the
same VM, and vice versa — **you need two separate fact-gathering runs,
one per inventory**, each targeting that inventory's name for this host.
This gets done in Phase 4; this phase only needs the "before" (no facts
yet) state.

**Use one of the reserved RHEL nodes for this, not `metrics_rhel9_1`/
`metrics_rhel9_2`** — this test depends on starting from zero facts, so
it needs a node that hasn't been touched by any earlier fact-caching run.

1. Confirm the same VM is present in a second inventory (e.g. `central`)
   under its raw/cloud-provider name — either it's already there via an
   existing dynamic EC2 source sync, or add/sync it now.

2. Confirm **both** `Host` rows for this VM — the demo-inventory entry
   and the central-inventory entry — are genuinely fact-free. The same
   combined filter from Phase 0 covers both in one query — no need to
   type out the exact EC2 hostname, which is worth avoiding anyway since
   it embeds the instance's public IP and changes if the instance is
   stopped/started without an Elastic IP attached:
   ```bash
   podman exec -it automation-controller-task awx-manage dbshell -- -c "
   SELECT name, ansible_facts_modified,
          ansible_facts->>'ansible_product_serial' AS product_serial,
          ansible_facts->>'ansible_machine_id' AS machine_id
   FROM main_host
   WHERE name ILIKE 'metrics%'
      OR name ILIKE '%compute.amazonaws%'
   ORDER BY name;
   "
   ```
   Confirm `ansible_facts_modified IS NULL` for both rows of your chosen
   VM specifically (`metrics_rhel9_1`/`_2` may already show values from
   Phases 1-6 — expected, just don't use them for this test).

3. Run your connectivity Job Template (the one **without** "Use Fact
   Cache" enabled) against **both** inventories' entries for this VM, so
   two separate `HostMetric` rows exist (one per literal hostname, per
   Phase 1) while both `Host` rows' `ansible_facts` stay untouched.

4. Run the RENEWAL_GUIDANCE report now, **before** any fact-gathering job
   has touched either `Host` row — reuse the `build_report`/CSV-conversion
   commands from Phase 6, but ship to a clearly separate path so this
   "before" output can't get overwritten later:
   ```bash
   podman exec automation-controller-task mkdir -p /var/lib/awx/metrics-utility/out_before

   podman exec -it \
     -e METRICS_UTILITY_SHIP_TARGET=controller_db \
     -e METRICS_UTILITY_REPORT_TYPE=RENEWAL_GUIDANCE \
     -e METRICS_UTILITY_SHIP_PATH=/var/lib/awx/metrics-utility/out_before \
     -e METRICS_UTILITY_DEDUPLICATOR=renewal \
     automation-controller-task \
     metrics-utility build_report --since=1months --ephemeral=1month --force
   ```
   Convert and pull it out the same way as Phase 6 (swap the path to
   `out_before`), then check the `Managed nodes` sheet's CSV (see Phase 6
   for why that's the right sheet, not `Managed nodes ephemeral`, for a
   freshly-automated host).

**Expected ("before" state):** the two entries — `metrics_rhel9_x` (demo
inventory) and the raw EC2 hostname (central inventory) — appear as **two
completely separate rows**, since they share neither `hostname` nor
`ansible_host_variable`, and both have empty `ansible_product_serial`/
`ansible_machine_id`. `renewal` has no key at all to match on yet.

- [ ] Confirmed both `Host` rows (demo + central) are fact-free before this test
- [ ] Same VM confirmed present in both inventories under two different names
- [ ] "Before" RENEWAL_GUIDANCE run shows 2 separate rows for this VM
      — saved to `out_before/` for comparison in Phase 7

---

## Phase 4 — Run the dedicated fact-gathering job template

**Validates:** README → "How to Populate Hardware Facts for Dedup (Without
Touching Other Job Templates)."

1. Create a job template running a minimal playbook:
   ```yaml
   - hosts: all
     gather_facts: true
     tasks: []
   ```
2. Enable **"Use Fact Cache"** on the job template.
3. **RHEL hosts:** ensure the credential escalates (`become: true`) so
   `/sys/devices/virtual/dmi/id/product_serial` is readable — otherwise
   you'll get the literal string `'NA'` instead of a real serial.
4. **Windows hosts:** ensure the WinRM credential has local admin rights —
   `Win32_Bios.SerialNumber` requires it.
5. Launch it against the original 4 `metrics*` hosts (demo inventory).
6. **Cross-inventory case (Phase 3.5):** a job template is bound to one
   inventory, and `ansible_facts` lives on the `Host` row, not the VM
   itself — so the demo-inventory `Host` and the central-inventory `Host`
   for the same VM are two separate rows that each need their own run.
   Launch this same job template a **second time**, either by
   prompting for a different inventory at launch or via a second job
   template pointed at the `central` inventory, `--limit`ed to the raw
   EC2 hostname from Phase 3.5.

Then re-run Phase 3.5's combined query — its `metrics%` OR raw-hostname
filter already covers the original 4 hosts and both `Host` rows of the
cross-inventory VM in a single result set.

**Expected:**
- `ansible_facts_modified` is now populated (non-`NULL`) for all 4
  original hosts, **and separately** for both the demo-inventory and
  central-inventory `Host` rows of the Phase 3.5 VM.
- Hosts **unaffected** by a Phase 2 casing mismatch show real
  `product_serial`/`machine_id` values (not `NULL`, not `'NA'`).
- Hosts **affected** by a Phase 2 casing mismatch still show `NULL` here
  despite the job succeeding — this is the join bug reproduced live, not a
  fact-gathering failure. (Sanity-check this distinction by also querying
  `SELECT ansible_facts_modified FROM main_host WHERE name = '<exact literal
  name>'` directly — if *that* shows a fresh timestamp but the JSONB lookup
  above shows `NULL`, the facts exist on the host row; the collector's join
  is just not the thing failing here, since this query reads `main_host`
  directly, not through metrics-utility's collector. To actually reproduce
  the *collector's* join failure specifically, see Phase 6.)
- **The critical check for Phase 3.5/7:** the demo-inventory `Host` row
  and the central-inventory `Host` row for the same VM must now show
  **identical** `product_serial`/`machine_id` values to each other — since
  it's genuinely the same physical/virtual machine, its DMI serial and
  `/etc/machine-id` don't change based on which inventory happens to
  reference it. This identical-value match is exactly what Phase 7's
  merge depends on.

- [ ] All 4 original hosts show a fresh `ansible_facts_modified` timestamp
- [ ] RHEL hosts show a real (non-`NA`) `product_serial`
- [ ] Windows hosts show a real `product_serial` and a `machine_id` (Windows
      machine SID, not a GUID — don't expect systemd-style formatting)
- [ ] Both `Host` rows (demo + central) for the Phase 3.5 VM now show
      matching `product_serial`/`machine_id` values

---

## Phase 5 — Check for cloned-instance identity collisions

**Validates:** README → use case #8 platform notes — cloned VMs/images can
share `ansible_machine_id`, which would cause false merges.

```bash
podman exec -it automation-controller-task awx-manage dbshell -- -c "
SELECT name,
       ansible_facts->>'ansible_product_serial' AS product_serial,
       ansible_facts->>'ansible_machine_id' AS machine_id
FROM main_host WHERE name ILIKE 'metrics%';
"
```

Compare across your two RHEL hosts, and separately across your two Windows
hosts.

- [ ] Both RHEL hosts have **different** `machine_id` values
- [ ] Both Windows hosts have **different** `machine_id` values

If either pair matches, note it — Phase 6 will falsely merge that pair, and
that's expected/correct behavior given the input data, not a bug in
`metrics-utility`.

---

## Phase 6 — Run the actual RENEWAL_GUIDANCE report

**Validates:** the end-to-end pipeline, and specifically whether the
collector's `main_host`/`main_hostmetric` join picks up what Phase 4 wrote.

```bash
podman exec automation-controller-task mkdir -p /var/lib/awx/metrics-utility/out

podman exec -it \
  -e METRICS_UTILITY_SHIP_TARGET=controller_db \
  -e METRICS_UTILITY_REPORT_TYPE=RENEWAL_GUIDANCE \
  -e METRICS_UTILITY_SHIP_PATH=/var/lib/awx/metrics-utility/out \
  -e METRICS_UTILITY_DEDUPLICATOR=renewal \
  automation-controller-task \
  metrics-utility build_report --since=1months --ephemeral=1month --force
```

**`build_report` only produces `.xlsx`** — `report/base.py` is built
entirely on `openpyxl`, with no CLI flag for CSV or plain-text output. To
get something readable on the host without needing Excel/LibreOffice,
convert it to CSV *inside the container*, using the same Python venv
metrics-utility already runs from (which already has `openpyxl` installed
— no extra dependency needed):

```bash
podman exec -i automation-controller-task /var/lib/awx/venv/awx/bin/python3 <<'PY'
import csv
import glob
import os

import openpyxl

for xlsx_path in glob.glob('/var/lib/awx/metrics-utility/out/reports/**/*.xlsx', recursive=True):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    base = os.path.splitext(xlsx_path)[0]
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        safe_sheet_name = sheet_name.replace(' ', '_')
        csv_path = f'{base}__{safe_sheet_name}.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(row)
        print(f'wrote {csv_path}')
PY
```

Then pull everything (xlsx + the new CSVs) out to the host:

```bash
podman cp automation-controller-task:/var/lib/awx/metrics-utility/out/ ./out/
```

**Sheet names, confirmed from `report_renewal_guidance.py`** (there is no
sheet literally named `host_metric` — that's only the internal dataframe
key passed between the dedup and report-building code):
- `Usage Reporting` — always present, an aggregate summary.
- `Managed nodes` — per-host rows for hosts whose automation history is
  older than the `--ephemeral` window. **This is the one you want** for a
  freshly-automated test host (first automated today), since it doesn't
  qualify as "ephemeral" yet.
- `Managed nodes ephemeral` / `Managed nodes ephemeral usage` — only
  populated once a host's `first_automation` is old enough to fall inside
  the ephemeral threshold.
- `Deleted Managed nodes` — soft-deleted hosts.

**Don't use `column -s, -t` to read this CSV.** It splits on every literal
comma with no awareness of CSV quoting rules, and this report's data
routinely has both: multi-value fields like `hostnames` and
`ansible_product_serials` are themselves comma-joined lists (properly
quoted in the CSV), and headers like `First\nautomation` contain an
embedded newline (also properly quoted). `column` shreds both, producing
misaligned garbage — that's a `column` limitation, not something you can
fix by trimming columns.

Use a small CSV-aware viewer instead (stdlib `csv` module only, no extra
dependencies). **Use the single-line form below, not a heredoc** — pasting
a multi-line heredoc into an interactive terminal often causes the
terminal to re-indent the closing delimiter line, which breaks bash's
heredoc-termination matching and leaves the shell hanging on a `>`
prompt waiting for a terminator that will never arrive:

```bash
python3 -c "import csv,sys; rows=[[c.replace(chr(10),' ') for c in r] for r in csv.reader(open(sys.argv[1], newline=''))]; n=max(len(r) for r in rows); rows=[r+['']*(n-len(r)) for r in rows]; w=[max(len(r[i]) for r in rows) for i in range(n)]; print('\n'.join('  '.join(r[i].ljust(w[i]) for i in range(n)) for r in rows))" ./out/reports/*/*/*__Managed_nodes.csv | less -S
```

Check the `Managed nodes` sheet/CSV for your 4 `metrics*` hosts.

**Expected, cross-referenced against your earlier findings:**
- 4 separate rows, **unless** Phase 5 found a shared `machine_id` (then
  that pair legitimately merges into 1 row) or Phase 2 found a casing
  mismatch (then that host's row will show empty/`NA` for
  `ansible_product_serials`/`ansible_machine_ids`, confirming the collector
  never received its facts).
- For any row that *did* get real facts, `ansible_product_serials`/
  `ansible_machine_ids` columns are populated with the values from Phase 4.

- [ ] Row count and content match expectations from Phases 2, 4, and 5

---

## Phase 7 — "After": Confirm `machine_id` Populating Actually Changed the Result

**Validates:** README use case #2 and #8 — transitive matching across
`hostname`/`ansible_host_variable`/`ansible_product_serial`/`ansible_machine_id`
— and directly closes the loop opened in Phase 3.5: this is the "after"
half of that before/after comparison, not a separate standalone test. This
is the realistic scenario metrics-utility's hardware-identity dedup exists
for: the same VM appearing in two different inventories, under two
completely different, unrelated hostnames, with no shared `ansible_host`.

By this point, Phase 4 has already run the fact-gathering job template
against **both** the demo-inventory and central-inventory `Host` rows for
this VM, so nothing new needs to be set up here — just re-run the report
and compare.

1. Re-run Phase 6's `build_report` command (the normal
   `METRICS_UTILITY_SHIP_PATH=/var/lib/awx/metrics-utility/out` path, not
   `out_before`), convert to CSV, and pull it out.
2. Open the `Managed nodes` sheet's CSV and find both entries for this
   VM: the demo inventory's `metrics_rhel9_x` and the central inventory's raw EC2
   hostname.
3. Directly diff this against the `out_before/` CSV saved in Phase 3.5.

**Expected ("after" state, compared against Phase 3.5's "before"):**
- **Before (Phase 3.5):** 2 separate rows — `metrics_rhel9_x` (demo) and
  the raw EC2 hostname (central) — with empty
  `ansible_product_serials`/`ansible_machine_ids`, and nothing else
  linking them (different inventories, different hostnames, no shared
  `ansible_host_variable`).
- **After (this phase):** the two entries **collapse into one row**,
  matching purely on the shared `ansible_machine_id`/`ansible_product_serial`
  populated in Phase 4 — despite being in different inventories with
  completely unrelated hostnames. This is the live, cross-inventory
  version of Scenario H in `test_renewal_dedup.py`, and it's the direct
  causal proof that populating `machine_id` is what changed the outcome
  — not something else, since nothing but `ansible_facts` changed between
  the two runs.

- [ ] "Before" (Phase 3.5) showed 2 separate rows: demo-inventory name and
      central-inventory (raw EC2) name
- [ ] "After" (this phase) shows 1 merged row spanning both inventories
- [ ] The merged row's `ansible_machine_id`s / `ansible_product_serials`
      columns match the identical values confirmed in Phase 4
- [ ] The merged row's `hostnames` column lists both the demo-inventory
      name and the central-inventory (raw EC2) name

**Optional extra validation:** set a common `ansible_host` variable on
both `Host` entries instead (across both inventories), and confirm you
can *also* merge them via the `renewal-hostname` code path (Scenario B in
`test_renewal_dedup.py`) — independent of hardware facts. Doing both
proves the two mechanisms are genuinely independent paths to the same
outcome, not one silently doing all the work.

---

## Results Log

| Phase | Result | Notes |
|---|---|---|
| 1 — HostMetric created, lowercased | | |
| 2 — Casing mismatch present? | | |
| 3 — Facts empty before gather | | |
| 3.5 — "Before": duplicate pair shows 2 separate rows | | |
| 4 — Facts populated after gather | | |
| 5 — Cloned-instance ID collision? | | |
| 6 — RENEWAL_GUIDANCE row count matches expectations | | |
| 7 — "After": duplicate pair merges to 1 row, caused by `machine_id` | | |
