# Workflow Limits Example

Demonstrates using AAP workflow limits to control which hosts each workflow job step targets.

## Playbooks

### `basic_test.yml`
Baseline test playbook that prints `inventory_hostname`. Used to verify which hosts a workflow node is targeting.

### `test1_wfs1.yml` / `test1_wfs2.yml`
Workflow scenario 1: two-step workflow with different host limits applied at each step.

### `test2_wfs1.yml` / `test2_wfs2.yml`
Workflow scenario 2: demonstrates limit inheritance and override between workflow nodes.

### `test3_wfs1.yml` / `test3_wfs2.yml`
Workflow scenario 3: additional limit pattern variation.

## Purpose
Shows how AAP workflow node limits interact — useful for understanding how to target subsets of inventory at different stages of a multi-step workflow without creating separate inventories.
