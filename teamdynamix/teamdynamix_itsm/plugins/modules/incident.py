#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
module: incident
short_description: Manage TeamDynamix incident tickets
description:
  - Create, update, or delete a TeamDynamix incident ticket via the TDX Web API.
  - Idempotent — when an existing ticket already matches the requested fields,
    no update is sent.
  - Authenticates with either a TDX C(username) and C(password) (the module
    calls C(POST /auth) to obtain a bearer token), or a pre-obtained
    C(token) used as-is.

options:
  instance:
    description:
      - TDX connection parameters.
      - Each sub-option also accepts an environment variable as a fallback.
      - Either I(username) + I(password) or I(token) must be provided.
    type: dict
    required: true
    suboptions:
      host:
        description:
          - TDX host. Three accepted forms:
          - "C(myorg) -> C(https://myorg.teamdynamix.com/TDWebApi/api)
            (bare subdomain on the standard hosted-tenant URL)."
          - "C(https://myorg.teamdynamix.com) -> C(.../TDWebApi/api)
            (scheme + host; standard API path appended)."
          - "C(https://tdx.example.com/sbtdwebapi/api) -> used verbatim
            (full base URL including the API path; for sandboxes or
            custom-domain tenants whose API path differs from
            C(/TDWebApi/api))."
          - Falls back to C(TDX_HOST).
        type: str
        required: true
      app_id:
        description:
          - Ticketing application ID.
          - Falls back to C(TDX_APP_ID).
        type: int
        required: true
      username:
        description:
          - TDX username. Required unless I(token) is supplied.
          - Falls back to C(TDX_USERNAME).
        type: str
      password:
        description:
          - TDX password. Required unless I(token) is supplied.
          - Falls back to C(TDX_PASSWORD).
        type: str
      token:
        description:
          - Pre-obtained TDX bearer token. When set, no login call is made
            and I(username)/I(password) are ignored.
          - Falls back to C(TDX_TOKEN).
        type: str
      timeout:
        description:
          - Per-request timeout in seconds.
          - Falls back to C(TDX_TIMEOUT).
        type: float
  state:
    description:
      - Lifecycle of the ticket.
      - C(present) creates a new ticket if I(id) is not provided, otherwise updates the
        existing ticket identified by I(id).
      - C(absent) deletes the ticket identified by I(id).
    type: str
    choices: [present, absent]
    default: present
  id:
    description:
      - TDX ticket ID. Required for updates and for C(state=absent).
    type: int
  title:
    description: Ticket title (short summary). Required when creating.
    type: str
  description:
    description: Ticket long-form description.
    type: str
  type_id:
    description: TDX TypeID. Required when creating.
    type: int
  account_id:
    description: AccountID — the department/account owning the ticket.
    type: int
  status_id:
    description: StatusID. Required when creating.
    type: int
  priority_id:
    description: PriorityID. Required when creating.
    type: int
  requestor:
    description:
      - Requestor's username or email. Resolved to a UID via TDX
        C(/people/search). Mutually exclusive with I(requestor_uid).
    type: str
  requestor_uid:
    description:
      - Requestor UID (GUID). Defaults to the service account if omitted.
      - Mutually exclusive with I(requestor).
    type: str
  responsible:
    description:
      - Responsible/assigned user's username or email. Resolved to a UID via
        TDX C(/people/search). Mutually exclusive with I(responsible_uid).
    type: str
  responsible_uid:
    description:
      - Responsible/assigned user UID (GUID).
      - Mutually exclusive with I(responsible).
    type: str
  impact_id:
    description: ImpactID.
    type: int
  urgency_id:
    description: UrgencyID.
    type: int
  source_id:
    description: SourceID (how the ticket was reported).
    type: int
  location_id:
    description: LocationID.
    type: int
  location_room_id:
    description: LocationRoomID.
    type: int
  service_id:
    description: ServiceID.
    type: int
  service_offering_id:
    description: ServiceOfferingID.
    type: int
  form_id:
    description: FormID — TDX form to use for this ticket.
    type: int
  notify_requestor:
    description: Whether TDX should email the requestor on ticket creation/update.
    type: bool
    default: true
  other:
    description:
      - Optional escape-hatch for arbitrary TDX ticket fields not exposed by
        this module's named options. Keys are passed through unchanged, so
        use TDX PascalCase field names (e.g. C(Tags), C(ExternalID),
        C(EstimatedHours)).
      - Values set here override values produced by the named options if both
        target the same TDX field.
    type: dict

author:
  - Todd Ruch (@taruch)
"""

EXAMPLES = r"""
- name: Create a new incident (username + password auth)
  teamdynamix.itsm.incident:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
    state: present
    title: "Database server unreachable"
    description: "Primary DB host stopped responding at 14:30 UTC."
    type_id: 111
    account_id: 222
    status_id: 333
    priority_id: 444
  register: created

- name: Update an existing incident's status (pre-obtained token)
  teamdynamix.itsm.incident:
    instance:
      host: myorg
      app_id: 35
      token: "{{ tdx_token }}"
    id: "{{ created.record.id }}"
    status_id: 555  # In Progress

- name: Close (delete) an incident
  teamdynamix.itsm.incident:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
    state: absent
    id: 98765

- name: Create an incident with requestor lookup and extra TDX fields
  teamdynamix.itsm.incident:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
    title: "VPN access request"
    type_id: 111
    status_id: 333
    priority_id: 444
    requestor: jdoe@example.com    # resolved to UID via /people/search
    responsible: helpdesk-tier1    # resolved by username
    other:
      Tags: ["vpn", "remote-access"]
      EstimatedHours: 2
"""

RETURN = r"""
record:
  description: The resulting ticket record (Ansible-friendly snake_case keys).
  type: dict
  returned: success
  sample:
    id: 98765
    title: "Database server unreachable"
    status_id: 333
    status_name: "New"
    priority_id: 444
    priority_name: "High"
diff:
  description: Before/after state of the ticket.
  type: dict
  returned: success
  contains:
    before:
      description: Ticket as it existed before the change (null if creating).
      type: dict
    after:
      description: Ticket after the change (null if deleting).
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils import arguments, people, utils
from ..module_utils.client import Client, expect
from ..module_utils.errors import TeamDynamixError
from ..module_utils.incident import PAYLOAD_FIELDS_MAPPING


# Fields the user can set directly on a ticket. Keys are the ansible-facing names;
# they map to TDX field names via PAYLOAD_FIELDS_MAPPING.
SETTABLE_FIELDS = (
    "title",
    "description",
    "type_id",
    "account_id",
    "status_id",
    "priority_id",
    "requestor_uid",
    "responsible_uid",
    "impact_id",
    "urgency_id",
    "source_id",
    "location_id",
    "location_room_id",
    "service_id",
    "service_offering_id",
    "form_id",
)

# Fields that must be present when creating a new ticket.
REQUIRED_FOR_CREATE = ("title", "type_id", "status_id", "priority_id")


def _ticket_path(app_id, ticket_id=None):
    if ticket_id is None:
        return "{0}/tickets".format(app_id)
    return "{0}/tickets/{1}".format(app_id, ticket_id)


def _get_ticket(client, app_id, ticket_id):
    response = client.get(_ticket_path(app_id, ticket_id))
    if response.status == 404:
        return None
    return expect(response, 200)


def _create_ticket(client, app_id, payload, notify_requestor, check_mode):
    if check_mode:
        return dict(payload)
    query = {"NotifyRequestor": str(notify_requestor).lower()}
    response = client.post(_ticket_path(app_id), payload, query=query)
    return expect(response, 200, 201)


def _update_ticket(client, app_id, ticket_id, payload, check_mode):
    if check_mode:
        return None  # caller will merge
    response = client.post(_ticket_path(app_id, ticket_id), payload)
    return expect(response, 200)


def _delete_ticket(client, app_id, ticket_id, check_mode):
    if check_mode:
        return
    response = client.delete(_ticket_path(app_id, ticket_id))
    if response.status not in (200, 204):
        expect(response, 200, 204)


def _build_payload(params):
    payload = utils.to_tdx(
        utils.filter_dict(params, *SETTABLE_FIELDS),
        PAYLOAD_FIELDS_MAPPING,
    )
    extras = params.get("other")
    if extras:
        payload.update(extras)
    return payload


def _resolve_people(client, params):
    """Translate ``requestor``/``responsible`` (name/email) into ``*_uid`` params."""
    if params.get("requestor"):
        params["requestor_uid"] = people.find_person_uid(client, params["requestor"])
    if params.get("responsible"):
        params["responsible_uid"] = people.find_person_uid(client, params["responsible"])


def _validate_for_create(params):
    missing = [f for f in REQUIRED_FOR_CREATE if not params.get(f)]
    if missing:
        raise TeamDynamixError(
            "Missing required parameters for ticket creation: {0}".format(
                ", ".join(missing)
            )
        )


def ensure_present(module, client):
    app_id = module.params["instance"]["app_id"]
    ticket_id = module.params.get("id")
    payload = _build_payload(module.params)

    if ticket_id is None:
        # Create
        _validate_for_create(module.params)
        new_raw = _create_ticket(
            client,
            app_id,
            payload,
            module.params["notify_requestor"],
            module.check_mode,
        )
        new = utils.to_ansible(new_raw, PAYLOAD_FIELDS_MAPPING)
        return True, new, dict(before=None, after=new)

    # Update
    existing_raw = _get_ticket(client, app_id, ticket_id)
    if existing_raw is None:
        raise TeamDynamixError("Ticket {0} not found".format(ticket_id))

    if utils.is_superset(existing_raw, payload):
        before = utils.to_ansible(existing_raw, PAYLOAD_FIELDS_MAPPING)
        return False, before, dict(before=before, after=before)

    updated_raw = _update_ticket(client, app_id, ticket_id, payload, module.check_mode)
    if updated_raw is None:
        # check_mode: synthesize the projected after-state by merging
        merged = dict(existing_raw)
        merged.update(payload)
        updated_raw = merged

    before = utils.to_ansible(existing_raw, PAYLOAD_FIELDS_MAPPING)
    after = utils.to_ansible(updated_raw, PAYLOAD_FIELDS_MAPPING)
    return True, after, dict(before=before, after=after)


def ensure_absent(module, client):
    app_id = module.params["instance"]["app_id"]
    ticket_id = module.params["id"]
    existing_raw = _get_ticket(client, app_id, ticket_id)
    if existing_raw is None:
        return False, None, dict(before=None, after=None)

    _delete_ticket(client, app_id, ticket_id, module.check_mode)
    before = utils.to_ansible(existing_raw, PAYLOAD_FIELDS_MAPPING)
    return True, None, dict(before=before, after=None)


def run(module, client):
    if module.params["state"] == "absent":
        return ensure_absent(module, client)
    _resolve_people(client, module.params)
    return ensure_present(module, client)


def main():
    module_args = dict(
        arguments.get_spec("instance", "id"),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        title=dict(type="str"),
        description=dict(type="str"),
        type_id=dict(type="int"),
        account_id=dict(type="int"),
        status_id=dict(type="int"),
        priority_id=dict(type="int"),
        requestor=dict(type="str"),
        requestor_uid=dict(type="str"),
        responsible=dict(type="str"),
        responsible_uid=dict(type="str"),
        impact_id=dict(type="int"),
        urgency_id=dict(type="int"),
        source_id=dict(type="int"),
        location_id=dict(type="int"),
        location_room_id=dict(type="int"),
        service_id=dict(type="int"),
        service_offering_id=dict(type="int"),
        form_id=dict(type="int"),
        notify_requestor=dict(type="bool", default=True),
        other=dict(type="dict"),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ("id",)),
        ],
        mutually_exclusive=[
            ("requestor", "requestor_uid"),
            ("responsible", "responsible_uid"),
        ],
    )

    try:
        instance = module.params["instance"]
        client = Client(
            host=instance["host"],
            app_id=instance["app_id"],
            username=instance.get("username"),
            password=instance.get("password"),
            token=instance.get("token"),
            timeout=instance.get("timeout"),
        )
        changed, record, diff = run(module, client)
        module.exit_json(changed=changed, record=record, diff=diff)
    except TeamDynamixError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
