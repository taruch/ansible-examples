Slow project syncs are one of the most common bottlenecks in Ansible Automation Platform (AAP). When a project sync takes minutes instead of seconds, it delays your entire automation pipeline because jobs sit in a "pending" or "waiting" state while the controller fetches data.

To radically speed up your project syncs, start by identifying the bottleneck, then apply the appropriate fix:

---

## 1. Identify the Bottleneck with profile_tasks

Before applying fixes, determine where your project sync is actually spending its time. Enable the `ansible.posix.profile_tasks` callback plugin in the `ansible.cfg` at the root of your project repository:

```ini
[defaults]
callbacks_enabled = ansible.posix.profile_tasks

[callback_profile_tasks]
sort_order = descending
output_limit = 30
```

This adds timing information to every task in the job output, showing exactly how long each step takes. Look at the project sync job stdout in AAP to identify whether the delay is in:

- **Galaxy/collection downloads** — long pauses during `ansible-galaxy collection install` (see fix #2)
- **Full git clone** — slow initial checkout (see fixes #4 and #5)
- **Network latency** — timeouts or slow transfers from remote SCM (see fix #3)
- **Waiting on SCM** — redundant Git fetches during concurrent launches (see fix #3)

**Important:** Adding `profile_tasks` to your project's `ansible.cfg` enables it for **all job templates** that use this project, not just the project sync. This adds overhead to every job run. Once you have identified the slow phase, remove or comment out the `callbacks_enabled` line and commit the change so it does not affect normal job execution.

---

## 2. Bake Collections into an Execution Environment (The #1 Speed Killer)

If your Git repository contains a `collections/requirements.yml` or `roles/requirements.yml` file, AAP executes an `ansible-galaxy` download **every single time the project syncs**. Downloading massive collections from Automation Hub or Galaxy at runtime is incredibly slow.

* **The Fix:** Move those dependencies out of your playbook repository. Use `ansible-builder` to compile those collections directly into a custom **Execution Environment (EE)** container image.
* **The Result:** Your project sync completely skips the download phase, dropping sync times from minutes down to a couple of seconds. The heavy lifting is done once during the image build, not during your automation runs.
* **Alternative:** If baking collections into an EE isn't feasible, upload them to your **Private Automation Hub (PAH)**. Configure your AAP projects to pull collections from PAH instead of the public Galaxy or Automation Hub. Since PAH is on your local network, downloads are significantly faster and not subject to internet latency or rate limits. This also gives you control over which collection versions are approved for use in your environment.

---

## 3. Leverage SCM Cache Timeout

Many teams check the **"Update Revision on Launch"** box on their Projects to guarantee they are always running the newest playbooks. However, if you trigger a workflow or launch 10 jobs back-to-back, AAP will hit Git 10 consecutive times, queueing up your jobs.

* **The Fix:** Set the **SCM Update Cache Timeout** (configured in seconds) on your Project settings.
* **How it works:** If you set this to `120` or `300` seconds, AAP will say: *"I know you asked to update on launch, but I literally just did a Git sync 45 seconds ago. I will reuse that cache and skip hitting Git."* This drastically prevents bottlenecking during concurrent job launches, but also means if an update was made the job won't get this update. If you are experiencing project sync issues, a much better solution is a proactive sync (directions below).

---

## 4. Disable "Delete on Update"

In your Project's advanced settings, there is a checkbox for **"Delete on Update"**.

* **The Fix:** Ensure this is **unchecked**.
* **Why it matters:** When checked, AAP deletes the entire local cache directory and performs a full `git clone` from scratch on every sync. When unchecked, AAP keeps a persistent local cache and performs a lightning-fast `git fetch` and `git reset` to align with the remote repository.

---

## 5. Keep Your Git Repository Lean

Because AAP has to pull the repository down to the controller's local environment, repository bloat directly correlates to sync lag.

* **The Fix:** Ensure your playbook repositories strictly contain text files (YAML, Jinja2 templates, bash scripts).
* **What to avoid:** Never commit large binary artifacts, virtual environments (`.venv`), heavy documentation, or large testing payload files directly to your playbook repo. Use a `.gitignore` file aggressively to keep the repository under a few megabytes.

---

## 6. Proactive Sync via Event-Driven Ansible (EDA)

Event-Driven Ansible provides a flexible way to trigger a project sync automatically whenever code is pushed to your repository. EDA can filter on branch, event type, and payload content before deciding whether to trigger a sync — giving you fine-grained control. By the time anyone launches a job, the sync is already done; this enables you to automatically update your project when a change is made, rather than using "update on launch" in AAP.

### Prerequisites

- AAP 2.5+ with Event-Driven Ansible controller enabled
- The `ansible.eda` collection installed in your EDA environment
- A **Controller API credential** (or Personal Access Token) so EDA can call back to the automation controller

### Step 1: Create a Workflow Job Template for Project Sync

1. Navigate to **Resources > Workflow Job Templates** and click **Add**
2. Name it something like `Project Sync - <your project name>`
3. Save, then click the **Visualizer** tab
4. Click **Start** to add a node
5. Set **Node Type** to **Project Sync**
6. Select the project you want to sync
7. Click **Save** on the node, then **Save** on the visualizer

This gives you a launchable workflow that does nothing but sync your project.

### Step 2: Create the EDA Rulebook

There are two approaches for receiving webhooks in EDA — direct port listening or using an Event Stream. Choose the one that fits your environment.

#### Option A: Direct Port (Simple)

The rulebook opens its own listener port. Simple to set up, but requires exposing an additional port on the EDA host and managing network/firewall rules for each activation.

Create a rulebook file (e.g., `rulebooks/project_sync_on_push.yml`):

```yaml
---
- name: Sync project on GitHub push to main
  hosts: all
  sources:
    - ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000

  rules:
    - name: Trigger project sync on push to main or master
      condition: >-
        event.meta.headers.X_GitHub_Event == "push"
        and (
          event.payload.ref == "refs/heads/main"
          or event.payload.ref == "refs/heads/master"
        )
      action:
        run_workflow_template:
          name: "Project Sync - <your project name>"
          organization: "<your organization>"
```

#### Option B: Event Stream (Recommended for AAP 2.5+)

Event Streams provide a centralized webhook endpoint managed by the EDA controller itself. Instead of each rulebook activation opening its own port, all webhooks flow through the EDA controller's gateway URL. This eliminates the need to expose extra ports and lets multiple rulebook activations share a single incoming endpoint.

**Step 2a: Create an Event Stream**

1. Navigate to **Event-Driven Ansible > Event Streams** and click **Add**
2. **Name**: `GitHub Push Events`
3. **Event stream type**: Select `Basic` or the appropriate type for your setup
4. **Credential**: Optional — create an **HMAC Event Stream** credential type if you want GitHub webhook secret validation:
   - Navigate to **Resources > Credentials** and click **Add**
   - **Credential Type**: `HMAC Event Stream`
   - **Secret**: Enter the same secret you will configure in GitHub
   - Save and select this credential on the event stream
5. Click **Save**
6. After saving, AAP generates the **Event Stream URL** — copy this (e.g., `https://<aap-gateway-host>/api/eda/v1/external_event_stream/<uuid>/post/`)

**Step 2b: Create the Rulebook using the Event Stream source**

Create a rulebook file (e.g., `rulebooks/project_sync_on_push_eventstream.yml`):

```yaml
---
- name: Sync project on GitHub push to main
  hosts: all
  sources:
    - ansible.eda.pg_listener:
        event_stream: "GitHub Push Events"

  rules:
    - name: Trigger project sync on push to main or master
      condition: >-
        event.meta.headers.X_GitHub_Event == "push"
        and (
          event.payload.ref == "refs/heads/main"
          or event.payload.ref == "refs/heads/master"
        )
      action:
        run_workflow_template:
          name: "Project Sync - <your project name>"
          organization: "<your organization>"
```

The only difference from Option A is the source — `ansible.eda.pg_listener` with an `event_stream` reference replaces the direct `ansible.eda.webhook` listener. The rules and conditions are identical.

### Step 3: Create an EDA Rulebook Activation in AAP

1. Navigate to **Event-Driven Ansible > Rulebook Activations** and click **Add**
2. **Name**: `GitHub Push - Project Sync`
3. **Project**: Select the EDA project containing your rulebook (or create one pointing to the repo with the rulebook file)
4. **Rulebook**: Select the appropriate rulebook (`project_sync_on_push.yml` for direct port, or `project_sync_on_push_eventstream.yml` for event stream)
5. **Decision Environment**: Select an appropriate decision environment with `ansible.eda` installed
6. **Controller Credential**: Select (or create) a credential that allows EDA to launch jobs on the automation controller — this is a **Red Hat Ansible Automation Platform** credential type with a URL and token/password for the controller API
7. **Event Stream** (Option B only): Select the `GitHub Push Events` event stream you created — this binds the activation to receive events from that stream
8. **Restart Policy**: Set to `Always` so the activation recovers if it stops
9. Click **Save**, then **Enable** the activation

### Step 4: Configure the Webhook in GitHub

1. Go to your GitHub repository > **Settings > Webhooks > Add webhook**
2. **Payload URL**:
   - **Option A (direct port)**: `https://<eda-host>:5000/endpoint`
   - **Option B (event stream)**: The Event Stream URL from step 2a (e.g., `https://<aap-gateway-host>/api/eda/v1/external_event_stream/<uuid>/post/`)
3. **Content type**: `application/json`
4. **Secret**:
   - **Option A**: Optional — add `token: <your-secret>` under the `ansible.eda.webhook` source in the rulebook
   - **Option B**: Enter the same secret configured in the HMAC Event Stream credential
5. **Which events would you like to trigger this webhook?**: Select **Just the push event**
6. Check **Active** and click **Add webhook**

### How It Works

**Option A — Direct Port:**
```
Developer pushes to main
    → GitHub sends POST to EDA webhook listener (port 5000)
    → EDA evaluates the rulebook condition (branch == main or master?)
    → If matched, EDA calls the controller API to launch the Project Sync workflow
    → Project is synced and cached before any job needs it
```

**Option B — Event Stream:**
```
Developer pushes to main
    → GitHub sends POST to AAP Gateway event stream URL
    → EDA controller receives the event and routes it to bound rulebook activations
    → EDA evaluates the rulebook condition (branch == main or master?)
    → If matched, EDA calls the controller API to launch the Project Sync workflow
    → Project is synced and cached before any job needs it
```

### Direct Port vs Event Stream

| | Direct Port (Option A) | Event Stream (Option B) |
|---|---|---|
| **Network** | Requires opening a custom port on the EDA host per activation | Uses the existing AAP gateway port (443) — no extra ports |
| **Scalability** | Each activation manages its own listener | Multiple activations can share one event stream endpoint |
| **Secret validation** | Configured in the rulebook source | Managed centrally via an HMAC credential on the event stream |
| **Setup** | Simpler — fewer AAP objects to create | More steps but cleaner architecture |
| **Best for** | Development, testing, single-activation setups | Production, multiple projects, environments behind load balancers |


---

## 7. Proactive Sync via Built-in GitHub Webhook

If you don't have EDA available, AAP's built-in webhook support provides a simpler alternative. It has less filtering capability but requires no additional components.

### Step 1: Create a Workflow Job Template for Project Sync

Follow the same steps from option 6, step 1 — create a workflow job template with a single Project Sync node.

### Step 2: Enable the Webhook on the Workflow Job Template

1. Edit the workflow job template you just created
2. Check **Enable Webhook**
3. Set **Webhook Service** to **GitHub**
4. **Save** the template
5. After saving, AAP generates two values — copy both:
   - **Webhook URL** — the endpoint GitHub will POST to (e.g., `https://<aap-host>/api/controller/v2/workflow_job_templates/<id>/github/`)
   - **Webhook Key** — the secret used to sign and verify payloads

### Step 3: Configure the Webhook in GitHub

1. Go to your GitHub repository > **Settings > Webhooks > Add webhook**
2. **Payload URL**: Paste the Webhook URL from AAP
3. **Content type**: `application/json`
4. **Secret**: Paste the Webhook Key from AAP
5. **Which events would you like to trigger this webhook?**: Select **Just the push event**
6. Check **Active** and click **Add webhook**

### Step 4: Filter to Main/Master Branch Only (Optional)

AAP will trigger the workflow on every push event regardless of branch. To limit syncs to only main or master pushes, add a branch filter in the workflow:

1. Edit the workflow job template
2. In the **Extra Variables** field or via a survey, you can use **Webhook Payload** data — AAP automatically provides the webhook payload as `tower_webhook_payload`
3. Alternatively, in your GitHub webhook settings, you can use **branch filter patterns** (GitHub Enterprise) or rely on the AAP project's default branch setting to only sync the relevant branch

### How It Works

```
Developer pushes to main
    → GitHub sends POST to AAP webhook URL
    → AAP launches the Project Sync workflow
    → Project is synced and cached before any job needs it
    → Next job launch uses the already-synced project (instant)
```

### EDA vs Built-in Webhook — When to Use Which

| | EDA (Option 6) | Built-in Webhook (Option 7) |
|---|---|---|
| **Setup complexity** | Requires EDA controller, rulebook, decision environment | Simple — checkbox in AAP |
| **Branch filtering** | Native — filter on branch, event type, file paths, etc. | Limited — fires on all push events |
| **Multiple actions** | One rulebook can trigger multiple workflows based on different conditions | One workflow per webhook |
| **Payload inspection** | Full condition engine — filter on changed files, commit messages, authors, etc. | Payload available as extra var but no pre-launch filtering |
| **Use case** | Multiple projects, complex event routing, audit trail | Single project, simple push-to-sync |


