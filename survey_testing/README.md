# Survey Testing

Demonstrates using AAP Job Template surveys to pass host lists and other input into playbooks at launch time.

## Playbooks

### `survery_test.yml`
Accepts a `_hosts` variable from an AAP survey prompt, splits the comma-separated string into a list, and prints the result. Shows how to handle the survey host variable pattern used in AAP Job Templates with a custom host prompt.

## Usage in AAP
1. Create a Job Template with a survey question that sets `_hosts`.
2. At launch, the user enters a comma-separated list of hostnames.
3. The playbook splits and uses the list as its target hosts.
