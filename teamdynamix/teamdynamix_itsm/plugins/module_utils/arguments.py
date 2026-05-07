# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import env_fallback


SHARED_SPECS = dict(
    instance=dict(
        type="dict",
        apply_defaults=True,
        options=dict(
            host=dict(
                type="str",
                required=True,
                fallback=(env_fallback, ["TDX_HOST"]),
            ),
            app_id=dict(
                type="int",
                required=True,
                fallback=(env_fallback, ["TDX_APP_ID"]),
            ),
            username=dict(
                type="str",
                fallback=(env_fallback, ["TDX_USERNAME"]),
            ),
            password=dict(
                type="str",
                no_log=True,
                fallback=(env_fallback, ["TDX_PASSWORD"]),
            ),
            token=dict(
                type="str",
                no_log=True,
                fallback=(env_fallback, ["TDX_TOKEN"]),
            ),
            timeout=dict(
                type="float",
                fallback=(env_fallback, ["TDX_TIMEOUT"]),
            ),
        ),
        required_together=[("username", "password")],
        required_one_of=[("username", "token")],
        mutually_exclusive=[("token", "username"), ("token", "password")],
    ),
    id=dict(type="int"),
    query=dict(type="dict"),
)


def get_spec(*param_names):
    return dict((name, SHARED_SPECS[name]) for name in param_names)
