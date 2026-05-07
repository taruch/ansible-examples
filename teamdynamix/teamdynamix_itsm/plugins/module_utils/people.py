# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

from .client import expect
from .errors import TeamDynamixError


_UID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def looks_like_uid(value):
    return bool(value) and bool(_UID_RE.match(value))


def find_person_uid(client, identifier, must_exist=True):
    """Resolve a person identifier to a TDX UID.

    `identifier` may be a UID (returned unchanged), a username, or an email
    address. The /people/search endpoint is used to look the person up; if
    multiple active people match, an exact match on UserName, PrimaryEmail,
    or AlternateEmail is preferred. If still ambiguous, raises.
    """
    if not identifier:
        return None
    if looks_like_uid(identifier):
        return identifier

    body = {"SearchText": identifier, "IsActive": True, "MaxResults": 25}
    response = client.post("people/search", body)
    people = expect(response, 200) or []

    needle = identifier.lower()
    exact = []
    for p in people:
        for field in ("UserName", "PrimaryEmail", "AlternateEmail"):
            if (p.get(field) or "").lower() == needle:
                exact.append(p)
                break

    candidates = exact if exact else people

    if not candidates:
        if must_exist:
            raise TeamDynamixError(
                "No active TDX person matched {0!r}".format(identifier)
            )
        return None
    if len(candidates) > 1:
        names = ", ".join(
            (p.get("UserName") or p.get("PrimaryEmail") or p.get("UID") or "?")
            for p in candidates[:5]
        )
        raise TeamDynamixError(
            "Multiple active TDX people matched {0!r}: {1}".format(identifier, names)
        )
    return candidates[0].get("UID")
