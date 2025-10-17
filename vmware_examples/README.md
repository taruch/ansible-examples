You can add these example playbooks to your Ansible Automation Platform by running
the setup_demo.yml playbook from the root of the repo.


Example:

Export your CONTROLLER variables:
export CONTROLLER_PASSWORD=<changeme>
export CONTROLLER_USERNAME=<changeme>
export CONTROLLER_HOST=<changeme>
export CONTROLLER_VERIFY_SSL=false
ansible-navigator run -mstdout setup_demo.yml --eei=quay.io/ansible-product-demos/apd-ee-25:latest --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL -e demo=vmware_examples