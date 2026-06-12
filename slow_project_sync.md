Slow project syncs are one of the most common bottlenecks in Ansible Automation Platform (AAP). When a project sync takes minutes instead of seconds, it delays your entire automation pipeline because jobs sit in a "pending" or "waiting" state while the controller fetches data.

To radically speed up your project syncs, apply these high-impact optimizations:

---

## 1. Bake Collections into an Execution Environment (The #1 Speed Killer)

If your Git repository contains a `collections/requirements.yml` or `roles/requirements.yml` file, AAP executes an `ansible-galaxy` download **every single time the project syncs**. Downloading massive collections from Automation Hub or Galaxy at runtime is incredibly slow.

* **The Fix:** Move those dependencies out of your playbook repository. Use `ansible-builder` to compile those collections directly into a custom **Execution Environment (EE)** container image.
* **The Result:** Your project sync completely skips the download phase, dropping sync times from minutes down to a couple of seconds. The heavy lifting is done once during the image build, not during your automation runs.

---

## 2. Leverage SCM Cache Timeout

Many teams check the **"Update Revision on Launch"** box on their Projects to guarantee they are always running the newest playbooks. However, if you trigger a workflow or launch 10 jobs back-to-back, AAP will hit Git 10 consecutive times, queueing up your jobs.

* **The Fix:** Set the **SCM Update Cache Timeout** (configured in seconds) on your Project settings.
* **How it works:** If you set this to `120` or `300` seconds, AAP will say: *"I know you asked to update on launch, but I literally just did a Git sync 45 seconds ago. I will reuse that cache and skip hitting Git."* This drastically prevents bottlenecking during concurrent job launches.

---

## 3. Disable "Delete on Update"

In your Project's advanced settings, there is a checkbox for **"Delete on Update"**.

* **The Fix:** Ensure this is **unchecked**.
* **Why it matters:** When checked, AAP deletes the entire local cache directory and performs a full `git clone` from scratch on every sync. When unchecked, AAP keeps a persistent local cache and performs a lightning-fast `git fetch` and `git reset` to align with the remote repository.

---

## 4. Keep Your Git Repository Lean

Because AAP has to pull the repository down to the controller's local environment, repository bloat directly correlates to sync lag.

* **The Fix:** Ensure your playbook repositories strictly contain text files (YAML, Jinja2 templates, bash scripts).
* **What to avoid:** Never commit large binary artifacts, virtual environments (`.venv`), heavy documentation, or large testing payload files directly to your playbook repo. Use a `.gitignore` file aggressively to keep the repository under a few megabytes.

---

Are your project syncs currently hanging during the `ansible-galaxy` dependency installation phase, or is the lag strictly due to network overhead pulling down a massive Git repository?
