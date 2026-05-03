# Slack Example

Sends Slack notifications from Ansible playbooks using the `community.general.slack` module.

## Playbooks

### `slack.yml`
Sends a success notification to a Slack channel (`#ansible`) with a green color indicator. Demonstrates standard job completion messaging from an AAP Job Template.

### `slack_warning.yml`
Sends a warning message to Slack, designed to be triggered from an Event-Driven Ansible (EDA) rulebook. Posts event data as a formatted warning to the configured channel.

## Required Variables
| Variable | Description |
|----------|-------------|
| `slack_token` | Slack API token (Bot token or legacy webhook token) |
| `slack_channel` | Target channel (e.g., `#ansible`) |

## Requirements
- `community.general` collection
- Slack app/bot token with `chat:write` permission
