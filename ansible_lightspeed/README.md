# Lightspeed Demo Examples #

## Task Generation Example 1 ##
Open the task_suggestions1.yml and uncomment each of the tasks 1 by 1.

## Playbook Generation Example 2 ##
Open the task_suggestions2.yml, uncomment the play name, click to the end of the line, and hit enter. This will actually provide suggestions for the entire playbook.

## Playbook Generation Example 1 - Configure new AWS VPC and Deploy a VM ##

Go to the Ansible icon on the left hand side of the VSC window and select "Generate a playbook".  Drop the below, or just type these in.
"""
deploy a new AWS VPC, ensure a key pair exists using a public key I provide, create a security group that allows 22 and 443, define variables in a vars section of the playbook, and then deploy a new vm
"""

This should give you a couple of suggested steps:
1. Create a new VPC
2. Create a new key pair
3. Create a new security group
4. Deploy a new VM

Select Continue at the bottom and it will give you a reasonable playbook to start with.

<pre>
---
- name: Deploy a new AWS VPC
  hosts: localhost
  vars:
    aws_key_name: "{{ _aws_key_name_ }}"
    aws_sg_name: my-security-group
    aws_sg_description: My security group for my VPC
    aws_sg_rules:
      - proto: tcp
        from_port: 22
        to_port: 22
        cidr_ip: "0.0.0.0/0"
      - proto: tcp
        from_port: 443
        to_port: 443
        cidr_ip: "0.0.0.0/0"
  tasks:
    - name: Create a new VPC
      register: my_vpc
      amazon.aws.ec2_vpc_net:
        name: my-vpc
        cidr_block: 10.0.0.60/24
        region: us-west-2
        state: present
    - name: Create a new key pair
      with_file: ~/.ssh/id_rsa.pub
      amazon.aws.ec2_key:
        name: "{{ aws_key_name }}"
        region: us-west-2
        key_material: "{{ _key_material_ }}"
        state: present
    - name: Create a new security group
      amazon.aws.ec2_security_group:
        name: "{{ aws_sg_name }}"
        description: "{{ aws_sg_description }}"
        region: us-west-2
        rules: "{{ aws_sg_rules }}"
        state: present
    - name: Deploy a new VM
      ec2:
        key_name: "{{ _key_name_ }}"
        instance_type: t2.micro
        image: ami-01a834fd83ae239ff
        group: "{{ aws_sg_name }}"
        vpc_subnet_id: subnet-0e688067
        assign_public_ip: true
        wait: true
        region: us-west-2
        state: present
</pre>


## Playbook Generation Example 2: ##

Go to the Ansible icon on the left hand side of the VSC window and select "Generate a playbook".  Drop the below, or just type these in.
"""
deploy a postgresql server and configure firewalld
"""

This should give you a couple of suggested steps:
1. deploy postgresql server
2. configure firewalld

Select Continue at the bottom and it will give you a reasonable playbook to start with.

<pre>
---
- name: Deploy a postgresql server and configure firewalld
  hosts: all
  vars:
    postgresql_listen_addresses: "*"
    postgresql_port: 5433
  tasks:
    - name: deploy postgresql server
      ansible.builtin.import_role:
        name: geerlingguy.postgresql
    - name: configure firewalld
      ansible.posix.firewalld:
        port: "{{ postgresql_port }}/tcp"
        permanent: true
        state: enabled
        immediate: true
</pre>