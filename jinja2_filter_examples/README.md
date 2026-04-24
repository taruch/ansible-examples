# jinja2_filter_examples

Standalone playbooks demonstrating Jinja2 filters in Ansible. All playbooks run on `localhost` with no inventory or credentials required.

```bash
ansible-playbook <playbook>.yml
```

---

## Playbooks

### [ip_set_filters.yml](ip_set_filters.yml) — Set filters with IP addresses

Demonstrates `difference`, `intersect`, `union`, and `symmetric_difference` using a realistic data-center IP address management scenario (full pool, production, blocked, reserved, and firewall allowlist datasets).

| Filter | Example use case |
|--------|-----------------|
| `difference` | Available IPs, safe prod hosts, rogue/stale addresses |
| `intersect` | Production hosts that are also blocked |
| `union` | Full managed address spaces |
| `symmetric_difference` | Firewall/production mismatches |
| Chained filters | True free pool; prod hosts missing firewall rules |

---

### [string_filters.yml](string_filters.yml) — String manipulation

Uses server hostnames and log message datasets to demonstrate string transformation filters.

| Filter | Example use case |
|--------|-----------------|
| `upper` / `lower` / `title` / `capitalize` / `swapcase` | Case normalization |
| `trim` / `center` / `ljust` / `rjust` | Whitespace and padding |
| `replace` | Swap environments in hostnames, fill template placeholders |
| `split` / `join` | Parse and rebuild FQDNs, split CSV tags |
| `truncate` / `wordwrap` / `indent` | Long text formatting for reports |
| `format` | Build connection strings |

---

### [list_filters.yml](list_filters.yml) — List and sequence filters

Uses a server inventory and CPU reading dataset to demonstrate list transformation and aggregation.

| Filter | Example use case |
|--------|-----------------|
| `map(attribute)` | Extract names, RAM values from a list of dicts |
| `selectattr` / `rejectattr` | Filter servers by env, CPU cores, RAM |
| `select` / `reject` | Filter numeric readings by threshold |
| `sort` | Sort servers by RAM or CPU |
| `min` / `max` / `sum` | Capacity aggregation across the fleet |
| `unique` / `flatten` | Deduplicate lists, flatten nested groups |
| `batch` / `slice` | Rolling update batches, report columns |
| `shuffle` | Randomize order for canary selection |

---

### [dict_filters.yml](dict_filters.yml) — Dict filters

Uses server configuration and inventory dicts to demonstrate dict transformation filters.

| Filter | Example use case |
|--------|-----------------|
| `combine` | Merge defaults with per-host overrides |
| `combine(recursive=True)` | Deep merge nested config dicts |
| `dict2items` | Iterate over config key/value pairs, filter sensitive keys |
| `items2dict` | Rebuild a dict after filtering its items |
| `dict(keys \| zip(values))` | Build a dict from two parallel lists |

---

### [math_filters.yml](math_filters.yml) — Math and numeric filters

Uses CPU readings, RAM sizes, and request counts for capacity planning calculations.

| Filter | Example use case |
|--------|-----------------|
| `abs` | Correct negative latency readings |
| `round` / `round(ceil)` / `round(floor)` | Conservative capacity estimates |
| `int` / `float` | Type conversion for thresholds and alerts |
| `int(base=16)` | Hex-to-int for VLAN/port conversion |
| `log` / `pow` / `sqrt` | Shard addressing, replication growth, std deviation |
| `sum` / `min` / `max` | Fleet-wide totals and outliers |

---

### [encoding_filters.yml](encoding_filters.yml) — Encoding, hashing, and serialization

Uses credentials, config dicts, and JSON/YAML strings to demonstrate data encoding and serialization filters.

| Filter | Example use case |
|--------|-----------------|
| `b64encode` / `b64decode` | HTTP Basic Auth headers, Kubernetes secrets |
| `hash('sha256')` | Integrity check hashes, deterministic deploy IDs |
| `password_hash('sha512')` | `/etc/shadow`-compatible password hashes |
| `to_json` / `from_json` | Serialize/parse JSON |
| `to_nice_json` / `to_nice_yaml` | Pretty-printed output for templates |
| `to_yaml` / `from_yaml` | Serialize/parse YAML |
| `urlencode` | Build safe query string parameters |

---

### [regex_filters.yml](regex_filters.yml) — Regular expression filters

Uses log lines, FQDNs, and config file content to demonstrate pattern matching and substitution.

| Filter | Example use case |
|--------|-----------------|
| `regex_search` | Extract timestamps, IPs, log levels, version numbers |
| `regex_findall` | Find all IPs in a string, all config keys, all latency values |
| `regex_replace` | Redact IPs, normalize hostnames, strip comments, back-references |
| `select('search')` | Filter log lines by severity |
| `map('regex_replace')` | Bulk redaction across a list of strings |

---

### [default_ternary_filters.yml](default_ternary_filters.yml) — Default, ternary, and type-test filters

Uses sparse server dicts and mixed-type variables to demonstrate safe variable handling and conditional value selection.

| Filter | Example use case |
|--------|-----------------|
| `default` | Fallback values for missing dict keys |
| `default(boolean=True)` | Trigger on any falsy value, not just undefined |
| `ternary` | Inline if/else for protocol selection, status labels |
| `omit` | Skip optional module parameters cleanly |
| `bool` / `int` / `string` | Safe type conversion |
