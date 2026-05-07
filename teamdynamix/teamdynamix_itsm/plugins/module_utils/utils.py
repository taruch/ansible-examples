# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


def filter_dict(source, *keys):
    """Return a new dict with only the listed keys whose values are not None."""
    return dict((k, source[k]) for k in keys if k in source and source[k] is not None)


def is_superset(superset, candidate):
    """True if every (key, value) in candidate is present and equal in superset.

    Used to detect "no-op updates": if the existing record already contains
    everything we'd send, the update is skipped.
    """
    for k, v in candidate.items():
        if k not in superset:
            return False
        if superset[k] != v:
            return False
    return True


def to_ansible(record, mapping):
    """Translate a TDX API record into the Ansible-friendly key set."""
    if record is None:
        return None
    return dict((ansible_key, record.get(tdx_key)) for ansible_key, tdx_key in mapping.items())


def to_tdx(payload, mapping):
    """Translate an Ansible-friendly payload into TDX API field names."""
    out = dict()
    for ansible_key, tdx_key in mapping.items():
        if ansible_key in payload and payload[ansible_key] is not None:
            out[tdx_key] = payload[ansible_key]
    return out
