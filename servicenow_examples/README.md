# ServiceNow CMDB Demo Playbooks

End-to-end demo that registers a VM and its application service in the ServiceNow CMDB, then uses incident enrichment to automatically report failed services.

## Prerequisites

- ServiceNow instance with ITSM plugin
- `servicenow.itsm` collection installed (`ansible-galaxy collection install servicenow.itsm`)
- `ansible.windows` collection installed
- Environment variables set for ServiceNow connectivity:
  - `SN_HOST` — ServiceNow instance URL (e.g., `https://instance.service-now.com`)
  - `SN_USERNAME` — ServiceNow username
  - `SN_PASSWORD` — ServiceNow password
- Windows target host with WinRM configured
- WAR file at `../certificate_renewal_examples/tomcat_windows/files/hello.war` (built by the `demo_prep` role)

## Demo Story Flow

### Step 1: Register the VM in the CMDB

```bash
ansible-playbook itsm_ci_create.yml -e _hosts=aws_win1
```

Gathers facts from the target host and creates (or updates) a VM Configuration Item in the `cmdb_ci_vm_instance` table.

### Step 2: Install Tomcat and register the service in the CMDB

```bash
ansible-playbook itsm_service_setup.yml -e _hosts=aws_win1
```

- Installs Java (Temurin JDK 21) and Apache Tomcat 10 via the `tomcat_windows_install` role
- Deploys a sample web application
- Sets the Tomcat service to auto-start
- Creates a `cmdb_ci_service` CI for Tomcat in ServiceNow
- Creates a "Runs on" relationship between the service CI and the VM CI

### Step 3: Simulate a service failure

```bash
ansible-playbook simulate_failure.yml -e _hosts=aws_win1
```

Stops the Tomcat10 Windows service, simulating an outage.

### Step 4: Create an incident in ServiceNow

Manually create an incident in the ServiceNow UI, referencing the Tomcat service. Note the incident number (e.g., `INC0010042`).

### Step 5: Enrich the incident with failed service details

```bash
ansible-playbook incident_enrichment.yml -e _hosts=aws_win1 -e req_number=INC0010042
```

Detects services that are set to auto-start but are not running, then updates the incident's work notes with the findings.

## Playbook Reference

| Playbook | Purpose |
|----------|---------|
| `itsm_ci_create.yml` | Register a VM as a CI in the CMDB |
| `itsm_ci_get.yml` | Query and display a CI from the CMDB |
| `itsm_service_setup.yml` | Install Tomcat, register as a service CI, link to VM |
| `simulate_failure.yml` | Stop Tomcat to simulate an outage |
| `incident_enrichment.yml` | Detect failed services and enrich a ServiceNow incident |
| `schedule_create.yml` | Create Ansible Controller schedules for Change Requests |
