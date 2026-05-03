# Create Email Report

Generates an HTML system report and delivers it via email.

## Playbooks

### `generate_report_email.yml`
Gathers system facts (disk usage, OS info, hardware details), builds an HTML-formatted report, and sends it using the `community.general.mail` module over SMTP with TLS/SSL. Supports configurable recipients, subject lines, and SMTP server settings via variables.

## Variables
| Variable | Description |
|----------|-------------|
| `smtp_host` | SMTP server hostname |
| `smtp_port` | SMTP port (e.g., 587 for STARTTLS, 465 for SSL) |
| `smtp_user` | SMTP authentication username |
| `smtp_password` | SMTP authentication password |
| `email_to` | Recipient address(es) |
| `email_subject` | Email subject line |

## Requirements
- `community.general` collection
- SMTP server accessible from the Ansible controller
