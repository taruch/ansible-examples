# Indirect Managed Node Counting — AAP + `metrics-utility`

This document covers a subsystem distinct from everything in
[`README.md`](README.md): **indirect managed node counting**. It has its
own AWX model (`IndirectManagedNodeAudit`), its own pipeline, and feeds a
different report sheet (`Indirectly Managed nodes` in `CCSP`/`CCSPv2`) —
not `RENEWAL_GUIDANCE`, and not `main_hostmetric`.

Everything below is traced directly from source: a full local checkout of
`ansible/awx` (`devel` branch) for the AAP/Controller side, and
`ansible/metrics-utility` (`devel` branch) for the reporting side.

## Table of Contents

- [What "Indirect" Means](#what-indirect-means)
- [The Two-Sided Mechanism](#the-two-sided-mechanism)
- [The AWS Example](#the-aws-example)
- [The VMware Example](#the-vmware-example)
- [AWS vs. VMware: a Structural Difference](#aws-vs-vmware-a-structural-difference)
- [Full Pipeline, Traced from Source](#full-pipeline-traced-from-source)
- [How This Reaches metrics-utility](#how-this-reaches-metrics-utility)
- [Confirmed Finding: The Final Dedup Key Is Just `host_name`](#confirmed-finding-the-final-dedup-key-is-just-host_name)
- [Confirmed Finding: Untagged AWS Resources Can False-Merge](#confirmed-finding-untagged-aws-resources-can-false-merge)
- [Prerequisites](#prerequisites)
- [Practical Guidance](#practical-guidance)
- [Sources](#sources)

## What "Indirect" Means

A **direct** managed node is one Ansible connects to and runs tasks
against (SSH/WinRM to a host, tracked via `HostMetric`/`main_host`). An
**indirect** managed node is a real-world resource that Ansible never
connects to directly, but clearly manages via an API — an EC2 instance
discovered/managed through the AWS API, a VMware guest managed through
vCenter's API, an S3 bucket, a load balancer, an RDS cluster. Ansible only
ever makes one connection (typically `local`, to call the cloud/virt API),
yet potentially many real resources get created, modified, or discovered
in that single task. AAP needs a way to count those resources for
licensing/compliance purposes without mistaking "one API call" for "one
managed node."

## The Two-Sided Mechanism

**Collection/module side:** a collection ships a file at
`extensions/audit/event_query.yml` containing **jq expressions**, keyed
by fully-qualified module name (or `collection.name.*` for a wildcard
across the whole collection), that tell AWX how to parse *that specific
module's JSON return value* to discover which real-world resources it
touched, and how to derive stable identifying facts for each one.

**AWX/AAP side:** a subsystem that scrapes these jq queries out of
installed collections at job-completion time, runs them against every job
event's raw module result, and records one `IndirectManagedNodeAudit` row
per matched resource.

Both `amazon.aws` and `community.vmware` ship this file (confirmed
directly on GitHub):
- [`amazon.aws/extensions/audit/event_query.yml`](https://github.com/ansible-collections/amazon.aws/blob/main/extensions/audit/event_query.yml)
- [`community.vmware/extensions/audit/event_query.yml`](https://github.com/ansible-collections/community.vmware/blob/main/extensions/audit/event_query.yml)

## The AWS Example

```yaml
amazon.aws.ec2_instance_info:
  query: >-
    .instances[] | select(. != null) | {
      name: (.name // .tags.Name // "UNKNOWN"),
      canonical_facts: {
        id: .instance_id,
        status: .state.name,
        tags: (.tags // {}),
      },
      facts: {
        infra_type: "PublicCloud",
        infra_bucket: "Compute",
        device_type: "EC2"
      },
    }
```

This targets `ec2_instance_info` — the **read-only, list-returning `_info`
module**, not the state-changing `ec2_instance`. The jq iterates
`.instances[]` (potentially dozens/hundreds of instances from one API
call) and emits one `{name, canonical_facts, facts}` record per instance.
`canonical_facts` (AWS `instance_id`, state, tags) is carried through as
metadata; `facts` (`infra_bucket`, `device_type`) is purely descriptive.
The collection ships equivalent queries for `elb_application_lb_info`,
`ec2_vpc_net_info`, `ec2_vpc_subnet_info`, `ec2_vpc_nat_gateway_info`,
`ec2_vpc_igw_info`, `ec2_vpc_vgw_info`, `ec2_vpc_route_table_info`,
`ec2_vpc_vpn_info`, `ec2_vpc_peering_info`, `s3_bucket_info`,
`s3_object_info`, `rds_instance_info`, and `rds_cluster_info` — every one
of them an `_info` (discovery) module, never a state-changing one.

## The VMware Example

```yaml
community.vmware.vmware_guest:
  query: >-
    .instance | {
      name: .moid,
      canonical_facts: {
        instance_uuid: .instance_uuid,
        bios_uuid: .hw_product_uuid,
        moid: .moid,
        esxi: .hw_esxi_host
      },
      facts: {
        infra_type: "private_cloud",
        infra_bucket: "compute",
        device_type: "virtual_machine"
      }
    }
```

Structurally different from AWS: this targets the actual **management
module** (`vmware_guest`, not an `_info` variant), and the jq operates on
`.instance` (**singular**) — one invocation manages one VM. `canonical_facts`
here is vCenter's `instance_uuid`, the VM's own hardware UUID
(`hw_product_uuid` — the same DMI-style concept as `ansible_product_serial`
elsewhere in this project, but sourced from vCenter's inventory rather
than the guest OS), `moid` (vCenter's managed object ID), and which ESXi
host it's running on.

## AWS vs. VMware: a Structural Difference

Collections have complete freedom in how they define this, and these two
examples show the two natural shapes:
- **AWS's approach**: one `_info` module call discovers **many** resources
  at once (`.instances[]`). Indirect counting piggybacks on routine
  discovery/inventory-sync playbooks.
- **VMware's approach**: one management module call manages **one**
  resource (`.instance`, singular). Indirect counting piggybacks on the
  actual VM lifecycle management task itself.

Neither is "more correct" — a collection maintainer writes the jq to
match whatever shape that module's `res` actually has.

## Full Pipeline, Traced from Source

1. When a job's EE runs, the runtime (ansible-runner/receptor tooling)
   writes `ansible_data.json` into the job's artifact directory, listing
   installed collections plus, for any collection shipping
   `extensions/audit/event_query.yml`, its `host_query` content.
2. `artifacts_handler()` in [`awx/main/tasks/callback.py`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/callback.py)
   reads this file after the job finishes and — **only if the feature
   flag `FEATURE_INDIRECT_NODE_COUNTING_ENABLED` is on** — creates one
   `EventQuery` DB row per unique `(collection, version)` pair, storing
   that collection's jq queries:
   ```python
   if flag_enabled("FEATURE_INDIRECT_NODE_COUNTING_ENABLED"):
       self.delay_update(event_queries_processed=False)
       collections_info = collect_queries(query_file_contents)
       for collection, data in collections_info.items():
           version = data['version']
           event_query = data['host_query']
           instance = EventQuery(fqcn=collection, collection_version=version, event_query=event_query)
           instance.save()
   ```
3. `save_indirect_host_entries()` (queued from `awx/main/tasks/system.py`,
   same feature-flag gate) then runs for that job:
   - `fetch_job_event_query()` pulls the `EventQuery` rows matching
     whatever collections that job actually used (via `job.installed_collections`).
   - `build_indirect_host_data()` walks every `JobEvent` where
     `event_data['res']` exists, matches `event_data['resolved_action']`
     (the FQCN actually invoked) against a query, runs the jq expression
     against `res`, and for each emitted `{name, canonical_facts, facts}`
     builds/increments an `IndirectManagedNodeAudit` row — deduplicated
     **within that one job's scope** by hashing `canonical_facts`.
4. `IndirectManagedNodeAudit.count` tracks how many times a registered
   module hit that same resource within the job; `events` lists which
   FQCNs contributed. The model enforces `unique_together = [('name', 'job')]`
   — one row per resource name per job.

(Source: [`awx/main/tasks/host_indirect.py`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/host_indirect.py), [`awx/main/models/indirect_managed_node_audit.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/indirect_managed_node_audit.py), [`awx/main/models/event_query.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/event_query.py))

## How This Reaches metrics-utility

`metrics-utility`'s `main_indirectmanagednodeaudit` collector is a plain
`SELECT` over `main_indirectmanagednodeaudit`, joined to job/inventory/
organization/project for context — no deduplication at the collector
level:
```sql
SELECT
    main_indirectmanagednodeaudit.name as host_name,
    main_indirectmanagednodeaudit.canonical_facts,
    main_indirectmanagednodeaudit.facts,
    main_indirectmanagednodeaudit.events,
    main_indirectmanagednodeaudit.count as task_runs,
    ...
FROM main_indirectmanagednodeaudit
LEFT JOIN main_job ON ...
```

That feeds into `DataframeJobhostSummaryUsage.build_dataframe()`, which
merges direct (`job_host_summary`) and indirect
(`main_indirectmanagednodeaudit`) data into one dataframe, tagged with a
`managed_node_type` column (`DIRECT`/`INDIRECT`). The CCSP/CCSPv2 report
builder later splits this back into two sheets by that tag:
```python
directs = job_host_summary_dataframe[job_host_summary_dataframe['managed_node_type'] == DIRECT]
indirects = job_host_summary_dataframe[job_host_summary_dataframe['managed_node_type'] == INDIRECT]
...
ws = self.add_sheet('Indirectly Managed nodes', sheet_index, ...)
self._build_data_section_usage_by_node(1, ws, indirects, managed_node_type='indirect')
```
(Source: [`dataframe_jobhost_summary_usage.py`](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dataframe_engine/dataframe_jobhost_summary_usage.py), [`report_ccsp.py`](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/report/report_ccsp.py))

## Confirmed Finding: The Final Dedup Key Is Just `host_name`

This is the important part, and it's confirmed directly from
`_build_data_section_usage_by_node` in `report/base.py`:
```python
ccsp_report_dataframe = dataframe.groupby('host_name', dropna=False).agg(
    host_runs=('host_name', 'count'),
    task_runs=('task_runs', 'sum'),
    first_automation=('first_automation', 'min'),
    last_automation=('last_automation', 'max'),
    canonical_facts=('canonical_facts', lambda x: merge_json_sets(x)),
    ...
)
```
**Unlike `RENEWAL_GUIDANCE`'s transitive `canonical_facts`-based matching
for direct hosts, the final `Indirectly Managed nodes` sheet groups
strictly by the literal `host_name` string** — which for indirect
resources is exactly the `name` field your collection's jq query emitted
(for AWS: `.name // .tags.Name // "UNKNOWN"`; for VMware: `.moid`).
`canonical_facts` is carried through as a *display* column, merged via
`merge_json_sets` — it is **not** part of the grouping key at all.

The good news this confirms: an intermediate dataframe-rollup step keeps
`job_remote_id` in its grouping key (`unique_index_columns()` in
`DataframeJobhostSummaryUsage`), but the *final* sheet-rendering groupby
above does not — so a resource re-discovered by the same scheduled
discovery job every day for a month correctly collapses to **one** row
in the final sheet, with `task_runs` summed across every discovery. Cross-job aggregation
for indirect nodes works correctly by design.

## Confirmed Finding: Untagged AWS Resources Can False-Merge

The flip side of keying purely on `host_name`: AWS's `ec2_instance_info`
query falls back to the literal string `"UNKNOWN"` when an instance has
neither a `name` attribute nor a `Name` tag:
```yaml
name: (.name // .tags.Name // "UNKNOWN"),
```
Since the final sheet groups by that exact string, **every untagged EC2
instance in your environment collapses into the same single `"UNKNOWN"`
row** — undercounting real indirect nodes, potentially significantly, in
any environment that doesn't consistently tag EC2 instances with a `Name`
tag. This is the inverse of every host-dedup failure mode documented in
`README.md` (which are all about failure to merge / overcounting) — here
the risk runs the other way, toward silent undercounting through a
naming collision baked into the collection's own query.

The same risk applies to any collection's jq query with a fallback
default for `name` — it's worth reading a collection's
`extensions/audit/event_query.yml` for exactly this pattern before
trusting its indirect node counts.

## Prerequisites

Same pattern as `use_fact_cache` for direct hosts in the main
`README.md` — this entire mechanism is silently inert unless every one of
these is true:
- **`FEATURE_INDIRECT_NODE_COUNTING_ENABLED`** must be on (an AAP feature
  flag — check via the Feature Flags admin page, or
  `mcp__aap-monitoring__feature_flags_state_retrieve`). Gates both
  `EventQuery` scraping (`tasks/callback.py`) and audit-record creation
  (`tasks/system.py`, `tasks/jobs.py`).
- The playbook must actually invoke a module the collection has
  registered a query for (e.g. `ec2_instance_info`, not any arbitrary AWS
  task).
- The EE's runtime must actually produce `ansible_data.json` with
  `installed_collections`/`host_query` populated — infrastructure-
  dependent (EE build, ansible-runner version), not something a playbook
  author controls directly.
- `METRICS_UTILITY_OPTIONAL_CCSP_REPORT_SHEETS` must include
  `indirectly_managed_nodes` (it's in the *default* list if unset, per
  `get_optional_ccsp_report_sheets()` — but worth confirming if you've
  customized that variable).
- `RENEWAL_GUIDANCE` does not surface indirect nodes at all — this data
  only appears in `CCSP`/`CCSPv2` reports.

## Practical Guidance

- If you rely on indirect node counts for compliance/billing evidence,
  **tag your cloud resources consistently** (a `Name` tag on every EC2
  instance, at minimum) — untagged resources silently undercount via the
  `"UNKNOWN"` collision above.
- Confirm `FEATURE_INDIRECT_NODE_COUNTING_ENABLED` is actually on before
  trusting a `0` or unexpectedly-low indirect node count — a disabled
  flag produces no error, just silently empty data.
- Read the specific `extensions/audit/event_query.yml` for any collection
  whose indirect counting you're relying on — behavior (list-based vs.
  single-resource, which modules are covered, what the `name` fallback
  logic is) is entirely collection-defined and varies collection to
  collection.
- Don't assume indirect nodes get the same sophisticated hardware-identity
  matching that `RENEWAL_GUIDANCE` applies to direct hosts — they don't;
  it's a simple, literal `host_name` match.

## Sources

- [`amazon.aws/extensions/audit/event_query.yml`](https://github.com/ansible-collections/amazon.aws/blob/main/extensions/audit/event_query.yml)
- [`community.vmware/extensions/audit/event_query.yml`](https://github.com/ansible-collections/community.vmware/blob/main/extensions/audit/event_query.yml)
- [`awx/main/tasks/host_indirect.py`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/host_indirect.py)
- [`awx/main/tasks/callback.py`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/callback.py)
- [`awx/main/tasks/system.py`](https://github.com/ansible/awx/blob/devel/awx/main/tasks/system.py)
- [`awx/main/models/indirect_managed_node_audit.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/indirect_managed_node_audit.py)
- [`awx/main/models/event_query.py`](https://github.com/ansible/awx/blob/devel/awx/main/models/event_query.py)
- [`main_indirectmanagednodeaudit.py` collector — ansible/metrics-utility](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/library/collectors/controller/main_indirectmanagednodeaudit.py)
- [`dataframe_jobhost_summary_usage.py` — ansible/metrics-utility](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dataframe_engine/dataframe_jobhost_summary_usage.py)
- [`report_ccsp.py` — ansible/metrics-utility](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/report/report_ccsp.py)
- [`dataframe_engine/base.py` — ansible/metrics-utility](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dataframe_engine/base.py)
- [`dedup/ccsp.py` — ansible/metrics-utility](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/dedup/ccsp.py)
- [`report/base.py` — ansible/metrics-utility](https://github.com/ansible/metrics-utility/blob/devel/metrics_utility/automation_controller_billing/report/base.py)
