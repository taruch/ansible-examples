# Curl to Job Template

Demonstrates passing extra variables into an AAP Job Template via the API (equivalent to a `curl` POST) and using them in a playbook.

## Playbooks

### `example_output.yml`
Accepts extra variables passed from a Job Template launch (e.g., via API or AAP survey) and prints all available variables. Creates a fact from `fact_1` for use in downstream plays or workflows.

## Usage
Launch this template via the AAP API with extra variables:

```bash
curl -X POST https://<controller>/api/v2/job_templates/<id>/launch/ \
  -H "Authorization: Bearer <token>" \
  -d '{"extra_vars": {"fact_1": "hello"}}'
```
