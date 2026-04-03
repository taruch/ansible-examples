oc login --token=<OC_LOGIN_TOKEN> --server=https://api.<CLUSTER_NAME>.<DOMAIN>:6443
oc create secret generic splunk-hec-token -n openshift-logging --from-literal=hec-token=<TOKEN HERE>
oc create sa log-collector -n openshift-logging
oc adm policy add-cluster-role-to-user logging-collector-logs-reader -z log-collector -n openshift-logging
oc logs -f $(oc get pods -n openshift-logging -l app.kubernetes.io/instance=instance -o name) -n openshift-logging -c collector


apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
spec:
  managementState: Managed
  outputs:
    - name: splunk-receiver
      splunk:
        authentication:
          token:
            key: hec-token
            secretName: splunk-hec-token
        index: main
        url: 'https://<SPLUNK_HOST>:<SPLUNK_HEC_PORT>'
      tls:
        insecureSkipVerify: true
      type: splunk
  pipelines:
    - inputRefs:
        - application
      name: aap-gateway-auth
      outputRefs:
        - splunk-receiver
  serviceAccount:
    name: log-collector