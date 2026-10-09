# AI-Assisted Playbook Troubleshooting — Live Demo

A live demo of an AI assistant (Claude Code, using the AAP MCP tools) reading
a failed AAP job's output, diagnosing the root cause, and proposing a fix to
the playbook — with a human reviewing and approving every change before
anything reruns. Nothing here is automatic: the AI never edits, commits, or
relaunches anything on its own.

This is deliberately separate from `automation_orchestrator/` (Automation
Orchestrator / EDA incident-triage work) — different product, different
purpose. This demo is about troubleshooting a playbook during development,
not about automated incident response.

## The scenario

`deploy_webapp.yml` installs nginx, drops a vhost config from a template,
starts the service, and verifies the app responds on `web_app_port`
(`8080` by default). It ships with **two intentional, sequential bugs** — the
first must be fixed before the job gets far enough to hit the second. Don't
pre-fix them; that's the point of the demo.

## Setup (before *every* run — this is not a one-time step)

The demo fixes get committed and pushed for real, so running it once "spends"
the bugs — whatever branch AAP's project points at won't reproduce them again.
`master` must stay permanently broken as the pristine source of both bugs, so
each run happens on a **throwaway branch created fresh off `master`**, which
you reset or discard afterward:

1. Create (or reset) the demo branch from `master`:
   ```bash
   git checkout master && git pull
   git branch -D ai-troubleshooting-demo 2>/dev/null   # ignore error if it doesn't exist locally
   git checkout -b ai-troubleshooting-demo
   git push --force origin ai-troubleshooting-demo
   ```
   If the remote branch doesn't exist yet, drop `--force` on the first push.
2. Register the project and job template, pointing the project at that
   branch rather than `master` (extra-vars override `include_vars`, so you
   don't need to edit `setup.yml` itself):
   ```bash
   # from controller_setup/, with this file's contents as setup.yml
   ansible-playbook configure_aap.yml \
     -e aap_hostname=... -e aap_username=... -e aap_password=... \
     -e project_scm_branch=ai-troubleshooting-demo
   ```
   Requires a `machine_credential` and `target_inventory` to already exist in
   AAP — see the tunables at the top of `setup.yml`. Safe to re-run — it just
   updates the existing project's branch if you're resetting for another run.
3. Confirm the target host can reach its package repos (to install `nginx`)
   and that you (the presenter) have push access to `ai-troubleshooting-demo`
   — the fixes have to actually land on that branch for AAP to pick them up.

**After the demo**, leave `ai-troubleshooting-demo` as-is or delete it
(`git push origin --delete ai-troubleshooting-demo`) — step 1 above recreates
it from a clean `master` next time regardless of what state it was left in.
**Never commit a fix directly to `master`** — that would permanently remove
the bug from the fixture.

## Live demo script

1. **Launch and watch it fail.** Launch "AI DEMO / Deploy Web App" (via the
   AAP UI or `mcp__aap-job-mgmt__job_templates_launch_create`). It fails on
   the "Deploy nginx vhost config" task.
2. **Hand the failed job to the AI.** Ask it to pull the job's output
   (`jobs_stdout_retrieve` and/or `jobs_job_events_list` for the failing
   task) and explain what went wrong. It should identify an undefined
   Jinja2 variable (`app_port`) used in `templates/vhost.conf.j2`, and notice
   `deploy_webapp.yml` actually defines `web_app_port`.
3. **Review the proposed diff.** The AI proposes fixing the template to
   reference `web_app_port`. You review it — this is the human gate. Nothing
   has changed in AAP yet.
4. **Approve: commit and push.** Once you're satisfied, commit and push the
   change yourself to `ai-troubleshooting-demo` (not `master`). This is the
   actual enforcement mechanism of the gate: the project is git-backed with
   `scm_update_on_launch: true`, so a launch always runs exactly what's on
   the branch — the AI's suggestion has zero effect on anything until a human
   deliberately pushes it.
5. **Relaunch — it fails differently.** The template task now succeeds, but
   the play aborts with `ERROR! The requested handler 'restart nginx' was
   not found in any of the known handlers`.
6. **Diagnose again.** Ask the AI to read this job's output and explain it.
   It should spot the case mismatch between `notify: restart nginx` and
   `handlers: - name: Restart nginx`.
7. **Review, approve, push** the second fix the same way as step 3–4.
8. **Relaunch — success.** The job installs nginx, deploys the fixed config,
   restarts the service, and the final health check gets a 200 from
   `http://localhost:8080/`.

## Answer key (for the presenter — don't share before the reveal)

| # | Symptom in job output | Root cause | Fix |
|---|---|---|---|
| 1 | `'app_port' is undefined` while templating `vhost.conf.j2` | `deploy_webapp.yml` defines `web_app_port`, but the template references `app_port` | In `templates/vhost.conf.j2`, change `listen {{ app_port }};` to `listen {{ web_app_port }};` |
| 2 | `ERROR! The requested handler 'restart nginx' was not found in any of the known handlers` | The task notifies `restart nginx` (lowercase) but the handler is named `Restart nginx` (capital R) — handler name matching is exact-string | In `deploy_webapp.yml`, change `notify: restart nginx` to `notify: Restart nginx` (or rename the handler to match) |

## Talking points to emphasize

- **The AI never has write access to what actually runs.** It can read job
  output and propose a diff; a human has to review it and push it before
  AAP's git-backed project will ever see it. The gate isn't a policy someone
  has to remember to follow — it's structural, because the project syncs
  from the branch, not from the AI's workspace.
- **This generalizes.** The same read-output → diagnose → propose-diff →
  human-pushes loop works for any job failure: bad module args, missing
  dependencies, undefined variables, handler typos, templating errors —
  not just the two bugs staged here.
- **Nothing about this requires changing your existing patch process** — it's
  a troubleshooting aid for playbook development/maintenance, independent of
  whatever job templates and workflows you already run in production.
- **The demo branch is a disposable fixture, not a real workflow.** In
  practice a fix would go through a normal PR against a feature branch, same
  as any other change — the throwaway-branch-off-`master` reset here only
  exists so this specific demo can reproduce the same two bugs on repeat
  runs.
