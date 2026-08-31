## Deploying a sharded, production-ready MongoDB cluster with Ansible
------------------------------------------------------------------------------

- Requires Ansible 2.14+ (tested against ansible-core 2.16/2.17)
- Expects RHEL/CentOS 8 or 9 hosts with `dnf`, `systemd`, and `firewalld`
- Deploys MongoDB 7.0 Community Edition from the official `repo.mongodb.org` repository

### A Primer
---------------------------------------------

![Alt text](images/nosql_primer.png "Primer NoSQL")

The above diagram shows how MongoDB differs from the traditional relational
database model. In an RDBMS, the data associated with 'user' is stored in a
table, and the records of users are stored in rows and columns. In MongoDB, the
'table' is replaced by a 'collection' and the individual 'records' are called
'documents'. One thing to notice is that the data is stored as key/value pairs
in BSON format.

Another thing to notice is that NoSQL-style databases have a looser consistency
model. As an example, the second document in the users collection has an
additional field of 'last name'.

### Data Replication
------------------------------------

![Alt text](images/replica_set.png "Replica Set")

Data backup is achieved in MongoDB via _replica sets_. As the figure above shows,
a single replica set consists of a primary (active) member and several
secondary (passive) members. All the database write operations happen on the
primary, and the primary replicates the data to the secondary nodes. _mongod_
is the process responsible for all database activity as well as replication.
The minimum recommended number of voting members in a replica set is 3.

### Sharding (Horizontal Scaling)
------------------------------------------------

![Alt text](images/sharding.png "Sharding")

Sharding works by partitioning the data into separate chunks and allocating
different ranges of chunks to different shard servers. The figure above shows a
collection which has 90 documents which have been sharded across the three
servers: the first shard getting ranges from 1-29, and so on. When a client wants
to access a certain document, it contacts the query router (`mongos` process),
which in turn contacts the config servers (a `mongod` replica set running with
`sharding.clusterRole: configsvr`) that keep a record of which ranges of chunks
are distributed across which shards.

Every shard must itself be backed by a replica set, so that writes/reads have
redundant copies available. Since MongoDB 3.6, the config servers must also be
deployed as a replica set (a "CSRS") — a standalone config server is no longer
supported.

Here are the basic steps of how sharding works:

1) A new database is created, and collections are added.

2) New documents get inserted, and all new documents for a given shard key
range go into a single shard.

3) When the size of a collection's chunk in a shard exceeds `chunkSize` the
chunk is split and rebalanced across shards.

### Deploying MongoDB with Ansible
--------------------------------------------

#### Architecture

![Alt text](images/site.png "Site")

This example deploys the minimum recommended production topology:

- **`mongo_servers`** — members of a single shard replica set (`mongod_replica_set_name`)
- **`mongoc_servers`** — members of the config server replica set (`mongoc_replica_set_name`), co-located on the shard nodes
- **`mongos_servers`** — stateless query routers, also co-located on a subset of the shard nodes

All processes are secured with a shared internal-authentication keyfile plus
username/password (SCRAM) authentication for clients.

#### Prerequisites

1) Install the required collections:

   ```bash
   ansible-galaxy collection install -r collections/requirements.yml
   ```

2) Set real secrets in `group_vars/all/vault.yml` (a cluster keyfile and the
   admin password), then encrypt the file:

   ```bash
   openssl rand -base64 756   # use the output as vault_mongodb_keyfile_content
   ansible-vault encrypt group_vars/all/vault.yml
   ```

3) Review `group_vars/all/vars.yml` — in particular `mongodb_data_dir`
   (default `/var/lib/mongo`; make sure it has sufficient space, 10G+
   recommended) and the replica set names.

4) Edit `hosts` to reflect your actual server names. Every host in
   `mongo_servers` becomes a member of the same shard replica set, so add more
   hosts there to grow that replica set. Hosts can belong to more than one
   group (as `mongo1`-`mongo3` do below) to co-locate roles on the same node —
   the standard MongoDB ports (27017 mongos / 27018 mongod / 27019 config
   server, set in `group_vars/all/vars.yml`) keep colocated processes from
   conflicting.

### Deployment Example

The inventory file looks as follows:

    [mongo_servers]
    mongo1
    mongo2
    mongo3

    [mongoc_servers]
    mongo1
    mongo2
    mongo3

    [mongos_servers]
    mongos1
    mongos2

Build the site with the following command:

    ansible-playbook -i hosts site.yml --ask-vault-pass

### Deploying via Ansible Automation Platform (AAP)
---------------------------------------------

This example can be run from AAP instead of the CLI. It needs no custom
Execution Environment — `collections/requirements.yml` only pulls standard
`community.mongodb`/`ansible.posix` collections, which AAP's project sync
installs automatically.

`setup_aap_resources.yml` provisions everything below for you: a Project
pointed at this repo, an Inventory sourced from `mongodb/hosts`, a Vault
credential (and optionally a Machine credential), and three job templates
(deploy / upgrade / test-sharding) with surveys attached where needed.

#### Automated setup

```bash
ansible-galaxy collection install awx.awx

export CONTROLLER_HOST=your-aap-controller.example.com
export CONTROLLER_USERNAME=admin
export CONTROLLER_PASSWORD=your_password
export MONGODB_VAULT_PASSWORD=the_password_group_vars_all_vault_yml_was_encrypted_with

# Optional - omit to skip creating a Machine credential and add one by hand:
export MONGODB_SSH_PRIVATE_KEY_FILE=/path/to/private_key
export MONGODB_SSH_USER=ec2-user

# Optional - only needed if the project's SCM remote requires auth:
export MONGODB_SCM_CREDENTIAL="My GitHub SSH Key"

ansible-playbook mongodb/setup_aap_resources.yml
```

Before running, edit the `project_scm_url`, `organization_name`, and
`inventory_name` vars at the top of `setup_aap_resources.yml` if the
defaults (this repo's own remote, "Default" org) don't match your AAP
instance.

This creates:

| Resource | Detail |
|---|---|
| Project | `MongoDB Cluster Example`, SCM-synced from this repo |
| Inventory | `MongoDB Cluster`, sourced from `mongodb/hosts` (auto re-parsed on every project sync) |
| Credential (Vault) | `MongoDB Cluster - Vault` — replaces `--ask-vault-pass` |
| Credential (Machine) | `MongoDB Cluster - Machine` — only created if `MONGODB_SSH_PRIVATE_KEY_FILE` is set |
| Job Template | `MongoDB - Deploy Cluster` → `mongodb/site.yml`, no survey |
| Job Template | `MongoDB - Upgrade Cluster` → `mongodb/upgrade.yml`, survey for `mongodb_upgrade_version` |
| Job Template | `MongoDB - Test Sharding` → `mongodb/playbooks/testsharding.yml`, survey for `mongos_target` |

The `mongos_target` survey (`aap_survey_spec_testsharding.json`) defaults its
choices to `mongo1`/`mongo2` — edit that file before running the setup
playbook if your real `mongos_servers` hostnames differ.

Re-running `setup_aap_resources.yml` is safe — every resource is created
with `state: present`, so it updates in place rather than duplicating.

#### Manual setup

Prefer to click through the UI instead? Create the same resources by hand:

1. **Project** — SCM-synced from this repo; job templates reference
   playbooks by path, e.g. `mongodb/site.yml`.
2. **Inventory** — an inventory source of type **"Sourced from a Project"**
   pointed at `mongodb/hosts` (or add the `mongo_servers`/`mongoc_servers`/
   `mongos_servers` groups by hand to match that file).
3. **Credentials** — a **Machine** credential for SSH access (include a
   privilege escalation password if the hosts need one, since every play
   uses `become: true`), and a **Vault** credential holding the password
   `group_vars/all/vault.yml` was encrypted with.
4. **Job templates** — one per playbook, per the table above. Enable
   **Survey** on the upgrade and test-sharding templates using
   `aap_survey_spec_upgrade.json`/`aap_survey_spec_testsharding.json`, and
   leave "Prompt on Launch" for extra variables off so the survey is the
   only way to set them.

#### Verifying the Deployment
---------------------------------------------

Once configuration and deployment has completed, check replica set status by
connecting to a shard member with `mongosh`:

    mongosh --port 27018
    shard01 [direct: primary] test> rs.status()

We can check the status of the shards by connecting to a `mongos` router:

    mongosh --port 27017 -u admin -p --authenticationDatabase admin
    mongos> sh.status()

The above steps can be exercised with an automated playbook — pass one of the
`mongos_servers` hosts in the `mongos_target` variable:

    ansible-playbook -i hosts playbooks/testsharding.yml -e mongos_target=mongo1 --ask-vault-pass

Once it completes, check the chunk distribution from any `mongos`:

    mongos> use test
    mongos> db.test_collection.getShardDistribution()

### Scaling the Cluster
---------------------------------------

![Alt text](images/scale.png "scale")

To add a new member to the shard replica set, add it to `[mongo_servers]` in
the inventory and re-run `site.yml`. The `community.mongodb.mongodb_replicaset`
task reconciles replica set membership against the full group each run.

    [mongo_servers]
    mongo1
    mongo2
    mongo3
    mongo4

Then run:

    ansible-playbook -i hosts site.yml --ask-vault-pass

### Verification
-----------------------------

The newly added node can be verified by checking replica set status
(`rs.status()` from a shard member) and confirming chunks are being
rebalanced onto it over time (`sh.status()` from a `mongos`).

### Upgrading the Cluster
---------------------------------------

`upgrade.yml` performs a rolling major-version upgrade (e.g. MongoDB 7.0 →
8.0) while keeping the cluster available, following MongoDB's documented
sharded-cluster upgrade order:

1. Disable the balancer.
2. Upgrade the config server replica set — secondaries first, then step down
   and upgrade the primary.
3. Upgrade the shard replica set the same way (`mongo_servers`; a multi-shard
   cluster would repeat this per shard).
4. Upgrade the `mongos` routers one at a time.
5. Bump `featureCompatibilityVersion` cluster-wide via a single `mongos` (it
   propagates to the shards and config servers automatically).
6. Re-enable the balancer.

At every step, at most one voting member of a replica set is offline at a
time, and the primary is always stepped down (triggering an election among
already-upgraded secondaries) before its own binary is touched — so writes
briefly pause for an election, but the cluster never goes fully unavailable.
The reusable `mongodb_upgrade` role handles swapping the yum repo/package
version and polling a member's replica set state; `upgrade.yml` handles the
cluster-aware ordering (primary detection, stepdown, balancer, FCV).

Only one major version at a time is supported — the playbook asserts this,
matching MongoDB's own upgrade constraints (you can't jump 7.0 → 9.0
directly).

Running this from AAP instead of the CLI? See "Deploying via Ansible
Automation Platform (AAP)" above — the job template for this playbook needs
a Survey field for `mongodb_upgrade_version` in place of `-e`.

Before upgrading a real cluster: read the target version's release notes for
breaking changes, and take a backup.

    ansible-playbook -i hosts upgrade.yml -e mongodb_upgrade_version=8.0 --ask-vault-pass

After it completes, update `mongodb_version` in `group_vars/all/vars.yml` to
the new version (the playbook reminds you) so future `site.yml` runs — e.g.
adding a new shard member — provision at the correct version instead of
reinstalling the old one.

**Limitations of this example, called out rather than glossed over:** the
cluster only has one shard, so this doesn't exercise upgrading multiple
shards in sequence (the shard play would simply repeat per shard group);
there's no TLS; and this playbook has been validated with
`ansible-playbook --syntax-check`, `yamllint`, and `ansible-lint`, plus a
standalone test of the dynamic "target the elected primary" pattern it
relies on — it has not been run against a live MongoDB cluster, since none
was available to test against here.

### What changed from the original example

This example previously targeted Ansible 1.2 and RHEL/CentOS 6, installed
MongoDB from the long-retired `10gen` yum repo, ran everything through SysV
init scripts and `iptables`, and stored the admin password and keyfile as
plaintext files in git. It has been modernized to:

- Install MongoDB 7.0 from the official `repo.mongodb.org` repo, managed with `dnf`
- Use `systemd` units instead of hand-written `/etc/init.d` scripts
- Use YAML-format `mongod.conf`/`mongos.conf` instead of the legacy `key=value` format
- Use `firewalld` instead of raw `iptables` rules
- Use the `community.mongodb` collection (`mongodb_replicaset`, `mongodb_shard`,
  `mongodb_user`) instead of hand-rolled `mongo` shell scripts
- Vault the admin password and cluster keyfile (`group_vars/all/vault.yml`) instead of committing them in plaintext
- Fix the config server connection string in `mongos.conf` to include the
  replica set name (`configReplSetName/host:port,...`) — required since
  MongoDB 3.6 and missing from the original template, which would have failed
  against any modern `mongos`
- Drop the redundant `replication_servers` inventory group (it always
  duplicated `mongo_servers`) and standardize on the default MongoDB ports
  (27017/27018/27019) instead of arbitrary ones
