ansible-navigator run test_example.yml -m stdout -vvv --execution-environment-image=localhost/ee_servicenow:v1.0 -e SN_HOST=$SN_HOST -e SN_PASSWORD=$SN_PASSWORD -e SN_USERNAME=admin -e SN_TABLE=cmdb_ci_computer -e SN_SEARCH=ALDWXP

