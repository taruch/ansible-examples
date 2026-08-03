This project requires a RHEL-9 host called `ca-host` in the workshop inventory, which
contains the network devices in the workshop.  This host is used to generate certificates
for the network devices.  If you use another project, such as Ansible Product-Demos 
(github.com/ansible/product-demos) to create the VM, it will be located in the Demo inventory
and won't be usable in this demo; this will require you to manually create the inventory host
in the workshop inventory.


Update the credential	"CA Host Credential"
 - Host: Host for the CA host (FQDN or IP)
 - Username: ca-admin
 - Password: password for CA host
 - CA Secret: private key password

Update the credential "ServiceNow ITSM"
 - Password: password for PSA ServiceNow instance

Update the hostname for the ca-host in the workshop inventory
 - Change the "Change Me" to be the ca host ip or FQDN

Run the `CA Server Setup` template to configure the RHEL-9 CA Host if you haven't already 

=====CISCO=====
Show the rtr beforehand - no trustpoints, no certificates:
sho crypto pki certificates verbose

Show the workflow run with below survey answers, it should run without issue.
  "trustpoint": "CACERT",
  "renewal_days": "12",
  "minumum_days": "10"
then run it again (from the same job), this time it should succeed and stop at checking the certificate.
Run the workflow again but this time change the min days to 15

Show the rtr after with trustpoints and certificates:
sho crypto pki certificates verbose

=====JUNIPER=====
Update the number of date variable attributes - done - check
Add the CA credential to the juniper 

## Return to Demo Menu
 - [Menu of Demos](../README.md)