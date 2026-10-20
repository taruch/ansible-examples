# Upgrading from AAP 2.4 (RHEL 8) to AAP 2.6 (RHEL 9)

This is a two-part move: first get your whole fleet (control node, hub, and both execution nodes) onto RHEL 9 while staying on AAP 2.4, then upgrade the whole thing straight to AAP 2.6 in one pass.

**Your current setup:** 1 control node, 1 private automation hub, 2 execution nodes. All four run AAP 2.4 on RHEL 8 today.

## The 5 rules — read these first

1. **Patch your current AAP 2.4 to its latest minor release before you do anything else** (e.g. 2.4.5, not 2.4.1). Red Hat only supports upgrading straight to 2.6 from the *latest* 2.4.z or 2.5.z — not from an arbitrary older minor. Do this before Step 1 of Part 1, since the backup you take will carry this version forward through the whole process. ([docs](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/planning_your_upgrade/upgrade-support-matrix))
2. **Every server must end up on RHEL 9. No exceptions.** This includes the execution nodes — there's no "it's just an execution node, it can stay on RHEL 8" option in the final state. ([docs](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/upgrade-ref_upgrade_rhel_support))
3. **The control node and hub keep the exact same name as the old servers they replace.** Don't rename `controller.example.com` to `controller-rhel9.example.com`. Some data only restores onto a server with the exact same hostname it was backed up from. ([docs](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/automation_controller_administration_guide/controller-backup-and-restore))
4. **You can skip AAP 2.5 entirely.** Go straight from 2.4 to 2.6 once the whole fleet is on RHEL 9. ([docs](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/planning_your_upgrade/upgrade-support-matrix))
5. **Keep the whole fleet on the same AAP version at every point in this process.** Don't let a 2.6 control node end up talking to 2.4 execution nodes, or vice versa, even briefly — that combination isn't something Red Hat documents as supported. That's why Part 1 moves *every* node (including both execution nodes) to RHEL 9 while keeping all of them on AAP 2.4, and Part 2 upgrades the entire fleet to 2.6 together, in one installer run.

---

## Part 1: Move the whole fleet to RHEL 9 (still AAP 2.4)

**Servers you'll touch:**

| Role | Name | What happens |
|---|---|---|
| Control node | `controller.example.com` | **New hardware.** Same hostname, data restored from backup. |
| Private automation hub | `hub.example.com` | **New hardware.** Same hostname, data restored from backup. |
| Execution node 1 | `exec1.example.com` | **Existing hardware, wiped and reinstalled.** Fresh RHEL 9 + AAP 2.4, rejoins the mesh. |
| Execution node 2 | `exec2.example.com` | **Existing hardware, wiped and reinstalled.** Fresh RHEL 9 + AAP 2.4, rejoins the mesh. |

The control node and hub hold real data (settings, job history, projects), so they need new hardware plus a backup/restore and a rollback plan. Execution nodes are ephemeral — they hold nothing of their own — so there's no reason to stand up new hardware or keep the old OS around "just in case." Just wipe each one and reinstall it on RHEL 9.

### Step 1 — Back up AAP 2.4

Run this on your current RHEL 8 setup. It saves everything — your settings, jobs, and configuration — into one backup file.

```bash
./setup.sh -i inventory -b
```

📖 [How backup and restore works](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/automation_controller_administration_guide/controller-backup-and-restore)

### Step 2 — Build 2 new RHEL 9 servers

Stand up 2 brand-new servers running RHEL 9.6 or later — one for the control node, one for the hub. Give them temporary names or IPs for now. Don't touch AAP on them yet.

(Leave the execution nodes alone for now — they get handled in Step 7, on their existing hardware.)

### Step 3 — Switch the control node and hub names over

Power down the old RHEL 8 control node and hub — **but don't wipe or decommission them yet.** Keep them intact as a rollback option in case the restore in Step 6 has problems; you can revert DNS back to them in minutes if something goes wrong. Plan to actually decommission them only after Step 7 confirms everything is healthy.

Then point each hostname at its new RHEL 9 replacement:
- `controller.example.com` → new control node
- `hub.example.com` → new hub


### Step 4 — Install AAP 2.4 fresh on the control node and hub

The restore in Step 6 only works if AAP is already installed and running. So install it fresh first — same version (2.4), pointing at your 2 renamed servers.

```bash
./setup.sh -i inventory
```

📖 [How to install AAP 2.4](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/red_hat_ansible_automation_platform_installation_guide/assembly-platform-install-scenario)

### Step 5 — Copy the backup file over

```bash
scp /path/to/aap-backup-*.tar.gz root@controller.example.com:/tmp/
```

### Step 6 — Restore the backup

This loads your old settings, jobs, and configuration into the new control node and hub. (The execution nodes aren't part of this — they join the mesh fresh, with nothing to restore.)

```bash
./setup.sh -i inventory -e 'restore_backup_file=/tmp/aap-backup-*.tar.gz' -r
```

📖 [How backup and restore works](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/automation_controller_administration_guide/controller-backup-and-restore)

### Step 7 — Rebuild the execution nodes in place

Now that the control node is restored and running on RHEL 9, rebuild the 2 execution nodes on their **existing hardware** — no new servers needed, and no backup/restore, since there's nothing on them worth keeping:

1. Reinstall the execution nodes with RHEL 9.6 or later.
2. Install AAP 2.4 on it.

### Step 8 — Double-check everything

- Log in and confirm the control node and hub look right.
- Confirm both execution nodes show up healthy in the control node's instance list.
- Once you're satisfied everything is healthy, it's safe to decommission the old RHEL 8 control node and hub hardware you set aside in Step 3.

**✅ End of Part 1:** Control node, hub, and both execution nodes are now running AAP 2.4 entirely on RHEL 9.6 or later.

---

## Part 2: Upgrade the whole fleet to AAP 2.6

**New in this part:** AAP 2.5/2.6 added a new required component called the **Gateway** — it handles login and the unified UI. You need one new server for it. As we have validated that the platform is healthy in a previous step, you can reuse that hardware for the Gateway node.

**Before you start:**
- **If you use Event-Driven Ansible (EDA):** its database can't carry forward automatically. Remove/reset the EDA database before continuing. ([docs](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/rpm_upgrade/aap-upgrading-platform))
- **Check your database version.** If you use your own external PostgreSQL server, it must be version 15, 16, or 17 — upgrade it now if it's older. If AAP manages its own database for you, it upgrades this automatically, so skip this. ([docs](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/install-ref_postgresql_requirements))

### Step 1 — Build the Gateway server

Stand up one more clean RHEL 9 server: `gateway.example.com`. This is brand new, so there's no old server or hostname to worry about here.

### Step 2 — Write the upgrade inventory file

This file tells the installer about every server in the fleet — control node, hub, both execution nodes, gateway, and database — all upgraded together in one pass:

```ini
[automationgateway]
gateway.example.com

[automationcontroller]
controller.example.com

[automationhub]
hub.example.com

[execution_nodes]
exec1.example.com
exec2.example.com

[database]
postgres-db.example.com
```

📖 [About the inventory file](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/red_hat_ansible_automation_platform_planning_guide/about_the_installer_inventory_file)

### Step 3 — Run the AAP 2.6 installer

Download the **latest AAP 2.6** installer (not 2.5), then run:

```bash
./setup.sh -i inventory
```

This upgrades the control node, hub, gateway, and both execution nodes straight from 2.4 to 2.6 together, in one run — nothing is left behind on an older version.

📖 [How to upgrade to AAP 2.6](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/rpm_upgrade/aap-upgrading-platform)

### Step 4 — Double-check everything

- Confirm the control node, hub, and gateway all show AAP 2.6 in the UI.
- Confirm both execution nodes show up healthy in the instance list.

**✅ End of Part 2:** You're running AAP 2.6 on RHEL 9 — control node, hub, gateway, and both execution nodes, all upgraded together.

---

## One thing to plan ahead for

AAP 2.6 is the **last** version with an RPM installer. Starting with AAP 2.7, Red Hat only supports containerized or OpenShift-based installs — so start thinking about that move after this upgrade.
