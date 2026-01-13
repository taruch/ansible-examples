curl -X POST https://<AAP_HOSTNAME>/api/controller/v2/job_templates/<TEMPLATE_ID>/launch/ \
    -H "Authorization: Bearer <YOUR_TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{
        "extra_vars": {
            "variable_1": "value1",
            "variable_2": "value2"
        }
    }'