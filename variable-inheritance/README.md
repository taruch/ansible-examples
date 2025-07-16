Ansible example implementing the following SSH key management (layers as defined in earlier mail):
 
This is intended to demonstrate the following use cases (IT used loosely here):
 
Central administration of most systems, except where other SLAs exist.  Allow non-IT managed (peer org) systems to be administratively separated but share common configuration controls.  Allow IT admins to co-manage services with peer org where desired.

Common – root user public key, appropriate for “mainstream” hosts.
Group acc – override the Common key entirely, substituting their own.
Group epcot - 
Type datadomain – add (is adding twice ok?) Common key so that Common and acc (if present as an inherited default) are configured. 
Type epcot-odb – insert new root key required for intra-server cluster operations, maintain inherited defaults.

The two type demos are probably functionally identical, but are called out as separate examples for digestability.
 
Host general-1: Group banner, type AIS – should have Common key and no others.
Host acc-1:  Group acc, type common – should have acc key and no others.
Host datadomain-1:  Group acc, type datadomain – should have both keys.
Host epcotodb-1: Group epcot, type epcot-odb – Should have cluster and common keys only.
 
One thing we didn’t cover – is it possible for the configuration play to be told whether or not to purge unmanaged keys?  Ie, ensure that general-1 has not had the epcot cluster key deployed?
 
<TR> Do you have examples where a host is in multiple groups?

<TR> You can ensure that specific keys are not deployed. The second task  in the ssh_keys role shows removing an unauthorized key.
 name: "Remove unauthorized key"
  ansible.posix.authorized_key:
    user: ansible
    key: "{{ epcot_cluster_pubkey }}"
    state: absent
  when: inventory_hostname not in groups['type_epcotodb'] and epcot_cluster_pubkey is defined


General Configuration
There are hosts and groups, and then essentially "roles". So an organization or group might have multi


Additional groups




Group hierarchy
Common
  - Group-acc
  - Group-epcot