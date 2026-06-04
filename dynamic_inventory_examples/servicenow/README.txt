This requires the servicenow.itsm collection, which can be imported to your Ansible Private Hub or pulled in from cloud.redhat.com.

This requires you to create a custom credential in Tower that provides environment variables with the below configuration:

Input configuration
"""
fields:
  - id: SN_USERNAME
    type: string
    label: Username
  - id: SN_PASSWORD
    type: string
    label: Password
    secret: true
  - id: SN_HOST
    type: string
    label: Snow Host
required:
  - SN_USERNAME
  - SN_PASSWORD
  - SN_HOST
"""


Injector configuration
"""
env:
  SN_HOST: '{{ SN_HOST }}'
  SN_PASSWORD: '{{ SN_PASSWORD }}'
  SN_USERNAME: '{{ SN_USERNAME }}'
extra_vars:
  SN_HOST: '{{ SN_HOST }}'
  SN_PASSWORD: '{{ SN_PASSWORD }}'
  SN_USERNAME: '{{ SN_USERNAME }}'
"""

You can also set environment variables if you want to test with `ansible-inventory -i servicenow.yml --graph --vars`
export SN_HOST='fqdn of servicenow host'
export SN_PASSWORD=
export SN_USERNAME=

Create a credential based on that type:
Input the following information into the new Credential:
- Name of the credential
- SN Host
- SN Password
- SN Username

Create a Project:
Input the following information into the new Project:
- Name - I called mine ServiceNow_Inventory
- Source Control Type - Git
- Source Control URL - Insert your url, or use this one

create a new inventory:
Once you have the credential, you can go "Inventories" -> "New", and create a "ServiceNow Inventory".  You really only need to put in the Name of the Inventory, and then save it.  After you have saved it, you can go to "Sources", and "Add" a new source.

In the inventory source:
Inventories > ServiceNow > Sources > ServiceNow_Source
Input the following information:
- Name of the source
- Execution Environment
- Source - Sourced from a Project
- Credential - use what you just created
- (Project) Source - use what you just created
- Inventory file - servicenow.yml
- click update on launch button

Save the Source, and run it (click the sync button at the bottom of the source)
The job status for this should be "Successful".
You can click on Sources at the top of the page, and go to Hosts and Groups and see both.
