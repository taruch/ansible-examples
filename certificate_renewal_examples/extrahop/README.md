# ExtraHop Appliance Certificate Renewal

Renews the SSL certificate on ExtraHop appliances (EDA, ECA, EXA, Reveal(x))
via the ExtraHop REST API. Supports two workflows: generating a CSR on the
appliance for external signing, or uploading a pre-signed certificate directly.

## What it does

1. **Option A (CSR):** Generates a Certificate Signing Request on the ExtraHop
   appliance via `POST /api/v1/extrahop/sslcert/signingrequest`, saves it
   locally for external CA signing, then ends the play. Re-run with the signed
   cert to complete the renewal.
2. **Option B (Direct upload):** Reads a pre-signed cert and key from the
   control node, combines them into a single PEM, and uploads via
   `PUT /api/v1/extrahop/sslcert`.
3. Waits for the appliance to apply the certificate.
4. Verifies the served certificate matches the uploaded one by comparing expiry
   dates.

## Requirements

- ExtraHop appliance with REST API access (all appliance types supported)
- API key with system and access administration privileges
- `community.crypto` collection

```bash
ansible-galaxy collection install -r requirements.yml
```

## Authentication

Generate an API key from the ExtraHop Administration UI:

1. Log in to your ExtraHop appliance
2. Navigate to **Administration > API Access > API Keys**
3. Click **Generate** and copy the key
4. Set it as an environment variable or vault variable:

```bash
export EXTRAHOP_API_KEY="your_api_key_here"
```

## Layout

```
extrahop/
├── README.md
├── renew_extrahop_cert.yml
├── requirements.yml
├── files/                          # drop cert material here
│   ├── eda01_example_com.pem       # signed certificate (PEM)
│   └── eda01_example_com.key       # private key (PEM)
└── inventory/
    └── hosts.yml
```

## Usage

### Generate a CSR on the appliance

```bash
ansible-playbook -i inventory/hosts.yml renew_extrahop_cert.yml \
  -e generate_csr=true \
  -e '{"csr_subject": {"common_name": "eda01.example.com", "organization_name": "My Org", "country_code": "US"}}'
```

Sign the CSR (`files/<hostname>.csr`) with your CA, then place the signed
cert at `files/<hostname>.pem`.

### Upload a pre-signed certificate

```bash
# Place cert and key in files/
cp signed_cert.pem files/eda01_example_com.pem
cp private_key.key files/eda01_example_com.key

# Run the playbook
ansible-playbook -i inventory/hosts.yml renew_extrahop_cert.yml
```

### Target a specific appliance

```bash
ansible-playbook -i inventory/hosts.yml renew_extrahop_cert.yml \
  --limit eda01.example.com
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `extrahop_api_key` | `$EXTRAHOP_API_KEY` | API key for authentication |
| `validate_certs` | `false` | Validate the appliance's current SSL cert |
| `generate_csr` | `false` | Generate a CSR instead of uploading a cert |
| `cert_src` | `files/<hostname>.pem` | Path to the signed certificate PEM |
| `key_src` | `files/<hostname>.key` | Path to the private key PEM |
| `csr_subject` | see playbook | Subject fields for CSR generation |
| `csr_sans` | `[]` | Subject Alternative Names for CSR |

## AAP / Controller

Create a Job Template with:
- **Credential:** Custom credential type for the ExtraHop API key (inject as
  `EXTRAHOP_API_KEY` environment variable)
- **Extra Variables:** Set `validate_certs`, `cert_src`, `key_src` as needed
- **Survey:** Add `generate_csr` as a boolean survey question for flexibility

## API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/extrahop/sslcert/signingrequest` | POST | Generate a CSR |
| `/api/v1/extrahop/sslcert` | PUT | Upload cert + key (PEM) |

Authentication header: `Authorization: ExtraHop apikey=<key>`

Applies to all ExtraHop appliance types (EDA, ECA, EXA, Reveal(x)). Each
appliance has its own API explorer at `https://<host>/api/v1/explore/`.
