# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


# Maps the ansible-friendly key (snake_case) to the TDX API field name (PascalCase).
# Add fields here as the modules grow — both modules read this same mapping.
PAYLOAD_FIELDS_MAPPING = dict(
    id="ID",
    title="Title",
    description="Description",
    type_id="TypeID",
    account_id="AccountID",
    status_id="StatusID",
    status_name="StatusName",
    priority_id="PriorityID",
    priority_name="PriorityName",
    requestor_uid="RequestorUid",
    responsible_uid="ResponsibleUid",
    impact_id="ImpactID",
    urgency_id="UrgencyID",
    source_id="SourceID",
    location_id="LocationID",
    location_room_id="LocationRoomID",
    service_id="ServiceID",
    service_offering_id="ServiceOfferingID",
    form_id="FormID",
    created_date="CreatedDate",
    modified_date="ModifiedDate",
)


# Maps Ansible-friendly query keys to TDX TicketSearch fields.
# Each value is (tdx_field, is_list) -- when is_list is True, scalar input
# values get auto-wrapped in a one-element list before sending.
QUERY_FIELDS_MAPPING = dict(
    # Single-value fields
    ticket_id=("TicketID", False),
    classification=("TicketClassification", False),
    search_text=("SearchText", False),
    max_results=("MaxResults", False),
    created_date_from=("CreatedDateFrom", False),
    created_date_to=("CreatedDateTo", False),
    modified_date_from=("ModifiedDateFrom", False),
    modified_date_to=("ModifiedDateTo", False),
    is_on_hold=("IsOnHold", False),
    is_assigned=("IsAssigned", False),
    # List fields -- scalar input is wrapped to [value]
    type_id=("TypeIDs", True),
    status_id=("StatusIDs", True),
    status_class_id=("StatusClassIDs", True),
    priority_id=("PriorityIDs", True),
    urgency_id=("UrgencyIDs", True),
    impact_id=("ImpactIDs", True),
    account_id=("AccountIDs", True),
    source_id=("SourceIDs", True),
    location_id=("LocationIDs", True),
    location_room_id=("LocationRoomIDs", True),
    service_id=("ServiceIDs", True),
    service_offering_id=("ServiceOfferingIDs", True),
    form_id=("FormIDs", True),
    requestor_uid=("RequestorUids", True),
    responsible_uid=("ResponsibilityUids", True),
)
