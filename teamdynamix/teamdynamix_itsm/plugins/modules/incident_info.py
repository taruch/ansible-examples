#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
module: incident_info
short_description: List or look up TeamDynamix incident tickets
description:
  - Retrieve one or more TeamDynamix tickets via the TDX Web API.
  - Pass I(id) to fetch a single ticket. Pass I(query) to search. With neither,
    returns the requestor's open tickets (the TDX default for the search endpoint).

options:
  instance:
    description:
      - TDX connection parameters. See M(teamdynamix.itsm.incident).
      - Either I(username) + I(password) or I(token) must be provided.
    type: dict
    required: true
    suboptions:
      host:
        description:
          - TDX subdomain or full base URL. Falls back to C(TDX_HOST).
        type: str
        required: true
      app_id:
        description:
          - Ticketing application ID. Falls back to C(TDX_APP_ID).
        type: int
        required: true
      username:
        description:
          - TDX username. Falls back to C(TDX_USERNAME).
        type: str
      password:
        description:
          - TDX password. Falls back to C(TDX_PASSWORD).
        type: str
      token:
        description:
          - Pre-obtained TDX bearer token. Falls back to C(TDX_TOKEN).
        type: str
      timeout:
        description:
          - Per-request timeout in seconds. Falls back to C(TDX_TIMEOUT).
        type: float
  id:
    description:
      - TDX ticket ID. When set, all other lookup options are ignored and the
        result is a single-element list.
    type: int
  query:
    description:
      - Search criteria sent to TDX C(POST /tickets/search).
      - Keys may be Ansible-friendly snake_case names that get translated to
        TDX TicketSearch fields. Scalar values for list fields (e.g.
        C(status_id: 1)) are auto-wrapped to a one-element list
        (C(StatusIDs: [1])). Lists are passed through unchanged.
      - C(requestor) and C(responsible) accept a username or email and are
        resolved to UIDs via TDX C(/people/search).
      - Recognized snake_case keys, C(search_text), C(max_results),
        C(classification), C(ticket_id), C(type_id), C(status_id),
        C(status_class_id), C(priority_id), C(urgency_id), C(impact_id),
        C(account_id), C(source_id), C(location_id), C(location_room_id),
        C(service_id), C(service_offering_id), C(form_id), C(requestor),
        C(requestor_uid), C(responsible), C(responsible_uid),
        C(created_date_from), C(created_date_to), C(modified_date_from),
        C(modified_date_to), C(is_on_hold), C(is_assigned).
      - Any other key is passed through verbatim, so raw TDX PascalCase
        field names also work (e.g. C(StatusIDs: [333])).
    type: dict

author:
  - Todd Ruch (@taruch)

seealso:
  - module: teamdynamix.itsm.incident
"""

EXAMPLES = r"""
- name: Look up a single ticket by ID
  teamdynamix.itsm.incident_info:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
    id: 98765
  register: result

- name: Find all New + In Progress tickets containing "database"
  teamdynamix.itsm.incident_info:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
    query:
      status_id: [333, 555]
      search_text: database
      max_results: 50
  register: result

- name: Find tickets opened by a specific user (resolved by username)
  teamdynamix.itsm.incident_info:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
    query:
      requestor: jdoe@example.com
      status_id: 333
      max_results: 25
  register: result

- name: Default search (the requestor's open tickets)
  teamdynamix.itsm.incident_info:
    instance:
      host: myorg
      app_id: 35
      username: "{{ tdx_username }}"
      password: "{{ tdx_password }}"
  register: result
"""

RETURN = r"""
records:
  description: Matching ticket records, with keys translated to snake_case.
  type: list
  elements: dict
  returned: success
  sample:
    - id: 98765
      title: "Database server unreachable"
      status_id: 333
      status_name: "New"
      priority_id: 444
      priority_name: "High"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils import arguments, people, utils
from ..module_utils.client import Client, expect
from ..module_utils.errors import TeamDynamixError
from ..module_utils.incident import PAYLOAD_FIELDS_MAPPING, QUERY_FIELDS_MAPPING


def _list_via_search(client, app_id, query):
    response = client.post("{0}/tickets/search".format(app_id), query or {})
    return expect(response, 200) or []


def _get_one(client, app_id, ticket_id):
    response = client.get("{0}/tickets/{1}".format(app_id, ticket_id))
    if response.status == 404:
        return None
    return expect(response, 200)


def _build_search_payload(client, raw_query):
    """Translate the user's query dict into a TDX TicketSearch payload.

    Snake_case keys listed in QUERY_FIELDS_MAPPING are mapped to PascalCase
    and (where applicable) wrapped in a list. The aliases ``requestor`` and
    ``responsible`` accept a username/email and are resolved to UIDs.
    Anything else passes through unchanged so raw TDX PascalCase still works.
    """
    if not raw_query:
        return {}

    out = {}
    for key, value in raw_query.items():
        if value is None:
            continue

        if key == "requestor":
            tdx_key, is_list = "RequestorUids", True
            value = people.find_person_uid(client, value)
        elif key == "responsible":
            tdx_key, is_list = "ResponsibilityUids", True
            value = people.find_person_uid(client, value)
        elif key in QUERY_FIELDS_MAPPING:
            tdx_key, is_list = QUERY_FIELDS_MAPPING[key]
        else:
            # Unknown key -- assume the user is using a raw TDX field name.
            out[key] = value
            continue

        if is_list and not isinstance(value, list):
            value = [value]
        out[tdx_key] = value

    return out


def run(module, client):
    app_id = module.params["instance"]["app_id"]

    if module.params.get("id") is not None:
        record = _get_one(client, app_id, module.params["id"])
        records = [record] if record else []
    else:
        search = _build_search_payload(client, module.params.get("query"))
        records = _list_via_search(client, app_id, search)

    return [utils.to_ansible(r, PAYLOAD_FIELDS_MAPPING) for r in records]


def main():
    module = AnsibleModule(
        argument_spec=arguments.get_spec("instance", "id", "query"),
        supports_check_mode=True,
        mutually_exclusive=[("id", "query")],
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
        records = run(module, client)
        module.exit_json(changed=False, records=records)
    except TeamDynamixError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
