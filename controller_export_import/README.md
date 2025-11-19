There are three playbooks in this repo:
 - one for exporting from an AAP 2.4 instance
 - one for exporting from an AAP 2.5/2.6 instance
 - one to import to an AAP 2.5 instance

To do an export from an Ansible Automation Platform system using the export playbooks, export the variables defined in the playbook vars (at the top)
export CONTROLLER_VERIFY_SSL=<true or false>
export CONTROLLER_HOST=<FQDN of 2.4 (or 2.5 respectively) controller>
export CONTROLLER_PASSWORD=<password>
export CONTROLLER_USERNAME=<username>

Run the playbook:
ansible-navigator run -mstdout filetree_export_24.yml -vvv --eei=quay.io/truch/export24:1.0 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL

or

ansible-navigator run -mstdout filetree_export_25.yml -vvv --eei=quay.io/truch/ee25:1.1 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL


To import to an Automation Platform 2.5 system, export the variables defined in the playbook vars for the AAP 2.5 system.

Run the playbook:
ansible-navigator run -mstdout filetree_import_25.yml -vvv --eei=quay.io/ansible-product-demos/apd-ee-25:latest --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL



Issues / Considerations:
If you had resources in the 2.4 system that were not assigned to an organization, you will run into issues importing those resources into the AAP 2.5 system.  You have a couple choices.
- Fix them in your 2.4 instance before you do the export (best)
- Change the ORGANIZATIONLESS resources to a viable organization (works): find ./<export directory> -type f -exec sed -i 's/ORGANIZATIONLESS/Default/g' {} +
- Remove the ORGANIZATIONLESS resources (probably not what you are looking for)

- Also be aware that if you overwrite a credential that you require (such as an Ansible Hub) for syncing collections, that can be a problem.  It might be a good idea to delete those, or to fix them.

- These exports will not export the actual secrets.  The 2.5 export is configured to change the "secret/encrypted" to a variable that can be imported from a vault.