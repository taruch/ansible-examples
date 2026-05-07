# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.six.moves.urllib.parse import urlencode
from ansible.module_utils.urls import Request

from .errors import TeamDynamixError, AuthError, UnexpectedAPIResponse


DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class Response(object):
    def __init__(self, status, data, headers=None):
        self.status = status
        self.data = data
        self.headers = (
            dict((k.lower(), v) for k, v in dict(headers).items()) if headers else {}
        )
        self._json = None

    @property
    def json(self):
        if self._json is None:
            try:
                self._json = json.loads(self.data) if self.data else None
            except ValueError:
                raise TeamDynamixError(
                    "Received invalid JSON response: {0}".format(self.data)
                )
        return self._json


class Client(object):
    """Thin REST client for the TeamDynamix Web API.

    Auth supports two modes:

    * **username + password** -- POST /auth, returns a bearer token cached on
      the instance for the lifetime of module execution.
    * **token** -- a pre-obtained bearer token used as-is; no login call is
      made.
    """

    def __init__(self, host, app_id, username=None, password=None,
                 token=None, timeout=None):
        if not host:
            raise TeamDynamixError("instance.host is required")
        if not token and not (username and password):
            raise TeamDynamixError(
                "instance must supply either token, or username and password"
            )

        if "://" not in host:
            host = "https://{0}.teamdynamix.com".format(host)
        self.host = host.rstrip("/")
        self.base_url = "{0}/TDWebApi/api".format(self.host)
        self.app_id = app_id
        self.username = username
        self.password = password
        self.timeout = timeout

        self._token = token or None
        self._client = Request()

    @property
    def auth_header(self):
        if self._token is None:
            self._token = self._login()
        return {"Authorization": "Bearer {0}".format(self._token)}

    def _login(self):
        body = json.dumps(
            {"username": self.username, "password": self.password}
        )
        url = "{0}/auth".format(self.base_url)
        try:
            raw = self._client.open(
                "POST",
                url,
                data=body,
                headers=DEFAULT_HEADERS,
                timeout=self.timeout,
                validate_certs=True,
            )
        except HTTPError as e:
            raise AuthError(
                "TDX login failed: {0} {1}".format(e.code, e.reason)
            )
        except URLError as e:
            raise AuthError("TDX login failed: {0}".format(e.reason))

        token = raw.read().decode("utf-8").strip()
        # The token comes back as a bare quoted string; strip the quotes if present.
        if token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        if not token:
            raise AuthError("TDX login returned empty token")
        return token

    def _request(self, method, path, query=None, data=None):
        url = "{0}/{1}".format(self.base_url, path.lstrip("/"))
        if query:
            url = "{0}?{1}".format(url, urlencode(query))

        headers = dict(DEFAULT_HEADERS)
        headers.update(self.auth_header)

        body = None
        if data is not None:
            body = json.dumps(data)

        try:
            raw = self._client.open(
                method,
                url,
                data=body,
                headers=headers,
                timeout=self.timeout,
                validate_certs=True,
            )
        except HTTPError as e:
            return Response(e.code, e.read(), e.headers)
        except URLError as e:
            raise TeamDynamixError("Request to {0} failed: {1}".format(url, e.reason))

        return Response(raw.status, raw.read(), raw.headers)

    def get(self, path, query=None):
        return self._request("GET", path, query=query)

    def post(self, path, data, query=None):
        return self._request("POST", path, query=query, data=data)

    def patch(self, path, data, query=None):
        return self._request("PATCH", path, query=query, data=data)

    def delete(self, path, query=None):
        return self._request("DELETE", path, query=query)


def expect(response, *ok_statuses):
    """Return the JSON body if the response status is in ok_statuses, else raise."""
    if response.status in ok_statuses:
        return response.json
    raise UnexpectedAPIResponse(response.status, response.data)
