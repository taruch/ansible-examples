"""
Fixture-based test harness for metrics-utility's RENEWAL_GUIDANCE deduplicators.

Runs the *actual* dedup classes (DedupRenewal, DedupRenewalHostname,
DedupRenewalExperimental) from renewal_guidance.py against synthetic
HostMetric-shaped rows -- no live Controller DB required.

Usage:
    python3 test_renewal_dedup.py
"""
import pandas as pd

from renewal_guidance import DedupRenewal, DedupRenewalHostname, DedupRenewalExperimental


class MockHostMetricSource:
    """Stands in for dataframes['host_metric'], which the real code calls .build_dataframe() on."""

    def __init__(self, df):
        self._df = df

    def build_dataframe(self):
        return self._df.copy()


def build_fixture():
    rows = [
        # --- Scenario A: exact same hostname automated twice (trivial re-run dupe) ---
        dict(scenario='A-same-hostname', hostname='web01', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-01', last_automation='2025-06-01',
             automated_counter=10, deleted_counter=0, last_deleted=None),
        dict(scenario='A-same-hostname', hostname='web01', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-01', last_automation='2025-07-01',
             automated_counter=5, deleted_counter=0, last_deleted=None),

        # --- Scenario B: same machine reached via IP / short hostname / FQDN, unified by ansible_host ---
        dict(scenario='B-ansible-host-var', hostname='10.0.0.5', ansible_host_variable='10.0.0.5',
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-02-01', last_automation='2025-05-01',
             automated_counter=3, deleted_counter=0, last_deleted=None),
        dict(scenario='B-ansible-host-var', hostname='web02', ansible_host_variable='10.0.0.5',
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-02-15', last_automation='2025-06-15',
             automated_counter=4, deleted_counter=0, last_deleted=None),
        dict(scenario='B-ansible-host-var', hostname='web02.example.com', ansible_host_variable='10.0.0.5',
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-03-01', last_automation='2025-08-01',
             automated_counter=2, deleted_counter=0, last_deleted=None),

        # --- Scenario C: host renamed/rebuilt; no shared hostname/var, but same machine_id ---
        dict(scenario='C-renamed-machine-id', hostname='db01', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id='MID-123', deleted=True,
             first_automation='2025-01-10', last_automation='2025-03-01',
             automated_counter=8, deleted_counter=1, last_deleted='2025-03-02'),
        dict(scenario='C-renamed-machine-id', hostname='db01-renamed', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id='MID-123', deleted=False,
             first_automation='2025-03-05', last_automation='2025-08-10',
             automated_counter=6, deleted_counter=0, last_deleted=None),

        # --- Scenario D: 3-way transitive chain via mixed keys (a<->b via serial, b<->c via machine_id) ---
        dict(scenario='D-transitive-chain', hostname='node-a', ansible_host_variable=None,
             ansible_product_serial='SN-999', ansible_machine_id=None, deleted=False,
             first_automation='2025-01-01', last_automation='2025-02-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='D-transitive-chain', hostname='node-b', ansible_host_variable=None,
             ansible_product_serial='SN-999', ansible_machine_id='MID-777', deleted=False,
             first_automation='2025-02-01', last_automation='2025-04-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='D-transitive-chain', hostname='node-c', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id='MID-777', deleted=False,
             first_automation='2025-04-01', last_automation='2025-08-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),

        # --- Scenario E: genuinely independent host; must never merge with anything above ---
        dict(scenario='E-independent', hostname='standalone01', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-01', last_automation='2025-08-01',
             automated_counter=20, deleted_counter=0, last_deleted=None),

        # --- Scenario F: null-like placeholders ('NA', '') must NOT be treated as a shared key ---
        dict(scenario='F-null-placeholders', hostname='ephemeral01', ansible_host_variable=None,
             ansible_product_serial='NA', ansible_machine_id='', deleted=False,
             first_automation='2025-05-01', last_automation='2025-05-02',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='F-null-placeholders', hostname='ephemeral02', ansible_host_variable=None,
             ansible_product_serial='NA', ansible_machine_id='', deleted=False,
             first_automation='2025-05-03', last_automation='2025-05-04',
             automated_counter=1, deleted_counter=0, last_deleted=None),

        # --- Scenario G: same physical host as IP / shortname / FQDN, but NO ansible_host_variable
        #     set and NO shared hardware facts either -- nothing at all ties these together ---
        dict(scenario='G-bare-ip-short-fqdn-no-facts', hostname='10.0.0.9', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-01', last_automation='2025-03-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='G-bare-ip-short-fqdn-no-facts', hostname='app03', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-05', last_automation='2025-04-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='G-bare-ip-short-fqdn-no-facts', hostname='app03.example.com', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-10', last_automation='2025-05-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),

        # --- Scenario H: same as G, but hardware facts (machine_id) WERE gathered and match ---
        dict(scenario='H-bare-ip-short-fqdn-with-facts', hostname='10.0.0.10', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id='MID-555', deleted=False,
             first_automation='2025-01-01', last_automation='2025-03-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='H-bare-ip-short-fqdn-with-facts', hostname='app04', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id='MID-555', deleted=False,
             first_automation='2025-01-05', last_automation='2025-04-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='H-bare-ip-short-fqdn-with-facts', hostname='app04.example.com', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id='MID-555', deleted=False,
             first_automation='2025-01-10', last_automation='2025-05-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),

        # --- Scenario I: same host, different hostname casing (WEB05 vs web05), no
        #     ansible_host_variable and no shared facts -- matching is case-sensitive ---
        dict(scenario='I-case-sensitivity', hostname='WEB05', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-01-01', last_automation='2025-02-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
        dict(scenario='I-case-sensitivity', hostname='web05', ansible_host_variable=None,
             ansible_product_serial=None, ansible_machine_id=None, deleted=False,
             first_automation='2025-03-01', last_automation='2025-04-01',
             automated_counter=1, deleted_counter=0, last_deleted=None),
    ]
    df = pd.DataFrame(rows)
    for col in ('first_automation', 'last_automation', 'last_deleted'):
        df[col] = pd.to_datetime(df[col])
    df['deleted'] = df['deleted'].astype(bool)
    # Mirrors the 'index' column the real build_dataframe() output carries,
    # which DedupRenewal/DedupRenewalHostname read via dupes['index'].
    df = df.reset_index(drop=True).reset_index()
    return df


def run_strategy(name, cls, df):
    dataframes = {'host_metric': MockHostMetricSource(df)}
    extra_params = {'report_renewal_guidance_dedup_iterations': '3'}
    result = cls(dataframes, extra_params).run()['host_metric']
    print(f'\n=== {name} ===')
    if result.empty:
        print('(no rows)')
        return result
    cols = ['hostname', 'hostnames', 'hostmetric_record_count']
    print(result[cols].to_string(index=False))
    return result


def scenario_group_counts(result_df):
    """For each fixture scenario, how many output groups does its raw hostnames map to?"""
    counts = {}
    for _, row in result_df.iterrows():
        merged_hostnames = {h.strip() for h in row['hostnames'].split(',') if h.strip()}
        counts[frozenset(merged_hostnames)] = counts.get(frozenset(merged_hostnames), 0) + 1
    return counts


def main():
    df = build_fixture()
    raw_scenario_hostnames = df.groupby('scenario')['hostname'].apply(set).to_dict()
    print('Raw fixture: {} records across {} scenarios'.format(len(df), df['scenario'].nunique()))
    for scenario, hostnames in raw_scenario_hostnames.items():
        print(f'  {scenario}: {sorted(hostnames)}')

    strategies = [
        ('DedupRenewal (default)', DedupRenewal),
        ('DedupRenewalHostname', DedupRenewalHostname),
        ('DedupRenewalExperimental', DedupRenewalExperimental),
    ]

    results = {}
    for name, cls in strategies:
        results[name] = run_strategy(name, cls, df.drop(columns=['scenario']))

    print('\n=== Summary: raw records -> deduped groups per strategy ===')
    for name, result in results.items():
        print(f'{name}: {len(df)} raw -> {len(result)} groups')

    # --- Assertions for behavior we are confident about from reading the source ---
    print('\n=== Assertions ===')

    def assert_true(label, condition):
        status = 'PASS' if condition else 'FAIL'
        print(f'[{status}] {label}')

    renewal = results['DedupRenewal (default)']
    hostname_only = results['DedupRenewalHostname']

    # A, B, C, D, E, F should each fully collapse under DedupRenewal's transitive expansion,
    # except F, which must NOT merge (its shared 'NA'/'' values are nulled out, not real matches).
    assert_true(
        'DedupRenewal: scenario A (same hostname) collapses to 1 group',
        any(row['hostnames'].count(',') == 0 and 'web01' in row['hostnames'] for _, row in renewal.iterrows())
        or any({'web01'} == {h.strip() for h in row['hostnames'].split(',')} for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario B (ansible_host_variable) collapses IP/host/FQDN into 1 group',
        any({'10.0.0.5', 'web02', 'web02.example.com'} == {h.strip() for h in row['hostnames'].split(',')}
            for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario C (renamed host, shared machine_id) collapses to 1 group',
        any({'db01', 'db01-renamed'} == {h.strip() for h in row['hostnames'].split(',')}
            for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario D (3-way transitive chain) fully collapses to 1 group',
        any({'node-a', 'node-b', 'node-c'} == {h.strip() for h in row['hostnames'].split(',')}
            for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario F (NA/empty placeholders) does NOT merge -- stays 2 separate groups',
        not any({'ephemeral01', 'ephemeral02'} == {h.strip() for h in row['hostnames'].split(',')}
                for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewalHostname: scenario C (renamed host) is NOT merged (no shared hostname/ansible_host)',
        not any({'db01', 'db01-renamed'} == {h.strip() for h in row['hostnames'].split(',')}
                for _, row in hostname_only.iterrows()),
    )
    assert_true(
        'DedupRenewalHostname: scenario B (shared ansible_host_variable) IS merged',
        any({'10.0.0.5', 'web02', 'web02.example.com'} == {h.strip() for h in row['hostnames'].split(',')}
            for _, row in hostname_only.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario G (IP/shortname/FQDN, no ansible_host_variable, no shared facts) '
        'does NOT merge -- stays 3 separate hosts',
        not any({'10.0.0.9', 'app03', 'app03.example.com'}.issubset({h.strip() for h in row['hostnames'].split(',')})
                for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario H (IP/shortname/FQDN, no ansible_host_variable, '
        'but shared ansible_machine_id) DOES merge to 1 group',
        any({'10.0.0.10', 'app04', 'app04.example.com'} == {h.strip() for h in row['hostnames'].split(',')}
            for _, row in renewal.iterrows()),
    )
    assert_true(
        'DedupRenewalHostname: scenario H (shared machine_id only, no ansible_host_variable) '
        'does NOT merge -- it ignores hardware facts entirely',
        not any({'10.0.0.10', 'app04', 'app04.example.com'}.issubset({h.strip() for h in row['hostnames'].split(',')})
                for _, row in hostname_only.iterrows()),
    )
    assert_true(
        'DedupRenewal: scenario I (WEB05 vs web05, no shared variable/facts) does NOT merge '
        '-- all matching is case-sensitive',
        not any({'WEB05', 'web05'} == {h.strip() for h in row['hostnames'].split(',')}
                for _, row in renewal.iterrows()),
    )

    print('\nExperimental strategy scenario D result printed above for manual inspection --')
    print('mixed-type transitive chains (serial + machine_id spanning 3 hosts) are the edge')
    print('case most worth eyeballing before trusting renewal-experimental on real data.')


if __name__ == '__main__':
    main()
