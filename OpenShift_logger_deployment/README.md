# OpenShift Logging 6.0 Deployment with Splunk Forwarding

Deploys the OpenShift Logging 6.0 operator into an existing OpenShift cluster and configures log forwarding to a Splunk HTTP Event Collector (HEC) endpoint.

## Overview

OpenShift Logging 6.0 introduced a significant API change — the `ClusterLogForwarder` resource moved from `logging.openshift.io/v1` to `observability.openshift.io/v1`. This playbook targets the new 6.0 API and deploys using the `stable-6.0` operator channel from the Red Hat operator catalog.

The deployment flow is:

1. Creates the `openshift-logging` namespace
2. Creates an `OperatorGroup` scoped to that namespace
3. Subscribes to the Cluster Logging Operator via OLM (`stable-6.0` channel)
4. Waits for the operator to finish installing (~45 seconds)
5. Creates a Kubernetes `Secret` containing the Splunk HEC token
6. Creates a `log-collector` ServiceAccount
7. Grants the ServiceAccount three ClusterRoleBindings required for log collection:
   - `logging-collector-logs-reader`
   - `collect-application-logs`
   - `collect-infrastructure-logs`
8. Deploys a `ClusterLogForwarder` that forwards application logs to the Splunk HEC endpoint

## Requirements

- `kubernetes.core` collection (`kubernetes.core.k8s` module)
- An active `oc`/`kubectl` session or `KUBECONFIG` pointing at the target cluster
- A Splunk HEC endpoint with a valid token and the target index created

## Variables

| Variable | Description | Default |
|---|---|---|
| `logging_namespace` | Namespace to deploy logging into | `openshift-logging` |
| `hec_token` | Splunk HEC token | `vault_splunk_hec_token` / `SPLUNK_HEC_TOKEN` env var |
| `splunk_url` | Splunk HEC URL **including port** (e.g. `https://splunk.example.com:8088`) | `vault_splunk_url` / `SPLUNK_URL` env var |
| `splunk_index` | Splunk index to forward logs to | `main` |

The `hec_token` and `splunk_url` variables should be provided via an Ansible Vault file or environment variables — do not hardcode them.

## Usage

```bash
# Set credentials via environment
export SPLUNK_HEC_TOKEN=<your-hec-token>
export SPLUNK_URL=https://<SPLUNK_HOST>:8088   # HEC port — do not omit, omitting causes a 302 redirect and dropped events

# Log in to OpenShift
oc login --token=<OC_LOGIN_TOKEN> --server=https://api.<CLUSTER_NAME>.<DOMAIN>:6443

# Run the playbook
ansible-playbook deploy_logger.yml
```

Or with a vault file:

```bash
ansible-playbook deploy_logger.yml --ask-vault-pass
```

## Verifying the Deployment

Check that the collector pod is running and forwarding logs:

```bash
oc logs -f $(oc get pods -n openshift-logging -l app.kubernetes.io/instance=instance -o name) -n openshift-logging -c collector
```

## Notes

- `tls.insecureSkipVerify: true` is set on the Splunk output — replace with proper CA cert configuration for production use
- The `ClusterLogForwarder` is configured to forward `application` logs only; add `infrastructure` or `audit` to `inputRefs` as needed
- OLM installation timing varies; if the operator is not ready after 45 seconds, increase the pause duration
