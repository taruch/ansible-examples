from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
    name: tdx_cmdb
    short_description: TeamDynamix CMDB dynamic inventory plugin
    description:
      - Fetches assets from the TeamDynamix Asset/CMDB API.
      - Returns an Ansible inventory with hosts grouped by I(location) and I(status).
      - Authenticates with either I(username) + I(password) (calls C(POST /auth)
        to obtain a bearer token) or a pre-obtained I(token).
    version_added: "1.0.0"
    author: Your Name (@yourhandle)
    options:
      plugin:
        description: Must be C(teamdynamix.itsm.tdx_cmdb) to activate this plugin.
        required: true
        choices: ["teamdynamix.itsm.tdx_cmdb"]
      instance:
        description: TDX subdomain (e.g. C(myorg) for myorg.teamdynamix.com).
        required: true
        type: str
        env:
          - name: TDX_INSTANCE
      app_id:
        description: Asset application ID in TDX (integer shown in the Admin URL).
        required: true
        type: int
        env:
          - name: TDX_APP_ID
      username:
        description:
          - TDX username. Required unless I(token) is supplied.
          - Use a vault-encrypted variable or env var.
        required: false
        type: str
        env:
          - name: TDX_USERNAME
      password:
        description:
          - TDX password. Required unless I(token) is supplied.
        required: false
        type: str
        env:
          - name: TDX_PASSWORD
      token:
        description:
          - Pre-obtained TDX bearer token. When set, no login call is made
            and I(username)/I(password) are ignored.
        required: false
        type: str
        env:
          - name: TDX_TOKEN
      host_attr_id:
        description:
          - Custom asset attribute ID whose value holds the hostname or IP address.
          - When omitted, the asset C(Name) field is used as C(ansible_host).
        required: false
        type: int
        env:
          - name: TDX_HOST_ATTR_ID
      status_filter:
        description:
          - List of asset status names to include. Assets with other statuses are skipped.
          - Comparison is case-insensitive.
        required: false
        type: list
        elements: str
        default:
          - "In Use"
        env:
          - name: TDX_STATUS_FILTER
'''

EXAMPLES = r'''
# File: tdx_cmdb.yml  (pass with -i tdx_cmdb.yml)
# Username + password auth
plugin: teamdynamix.itsm.tdx_cmdb
instance: myorg
app_id: 40
username: "{{ lookup('env', 'TDX_USERNAME') }}"
password: "{{ lookup('env', 'TDX_PASSWORD') }}"
status_filter:
  - "In Use"
  - "In Maintenance"

# Pre-obtained bearer token (skips /auth)
plugin: teamdynamix.itsm.tdx_cmdb
instance: myorg
app_id: 40
token: "{{ lookup('env', 'TDX_TOKEN') }}"
host_attr_id: 9876
'''

RETURN = r'''  # Nothing returned directly; hosts and groups are added to the inventory.'''

import json
import urllib.request
import urllib.error

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin


class InventoryModule(BaseInventoryPlugin):

    NAME = 'teamdynamix.itsm.tdx_cmdb'

    # Only activate for config files that match these suffixes
    _VALID_EXTENSIONS = ('tdx_cmdb.yml', 'tdx_cmdb.yaml', 'tdx.yml', 'tdx.yaml')

    def verify_file(self, path):
        if super().verify_file(path):
            if path.endswith(self._VALID_EXTENSIONS):
                return True
        return False

    def parse(self, inventory, loader, path, cache=False):
        super().parse(inventory, loader, path, cache)

        try:
            self._read_config_data(path)
        except Exception as exc:
            raise AnsibleParserError(f"Failed to read {path}: {exc}") from exc

        instance = self.get_option('instance')
        app_id = self.get_option('app_id')
        username = self.get_option('username')
        password = self.get_option('password')
        token = self.get_option('token')
        host_attr_id = self.get_option('host_attr_id')
        status_filter = [s.lower() for s in (self.get_option('status_filter') or [])]

        if not token and not (username and password):
            raise AnsibleParserError(
                "tdx_cmdb requires either 'token', or both 'username' and 'password'"
            )

        base_url = f"https://{instance}.teamdynamix.com/TDWebApi/api"

        try:
            if not token:
                token = self._auth(base_url, username, password)
            assets = self._search_assets(base_url, app_id, token)
        except urllib.error.HTTPError as exc:
            raise AnsibleError(
                f"TDX API returned HTTP {exc.code}: {exc.read().decode()}"
            ) from exc
        except Exception as exc:
            raise AnsibleError(f"Failed to query TDX: {exc}") from exc

        for asset in assets:
            # Apply status filter
            if status_filter and asset.get('StatusName', '').lower() not in status_filter:
                continue

            hostname = (asset.get('Name') or '').strip()
            if not hostname:
                continue

            # Determine connection target
            ansible_host = hostname
            if host_attr_id:
                for attr in asset.get('Attributes', []):
                    if attr.get('ID') == host_attr_id and attr.get('Value'):
                        ansible_host = attr['Value'].strip()
                        break

            self.inventory.add_host(hostname)
            self.inventory.set_variable(hostname, 'ansible_host', ansible_host)
            self.inventory.set_variable(hostname, 'tdx_asset_id', asset.get('ID'))
            self.inventory.set_variable(hostname, 'tdx_serial', asset.get('SerialNumber', ''))
            self.inventory.set_variable(hostname, 'tdx_manufacturer', asset.get('ManufacturerName', ''))
            self.inventory.set_variable(hostname, 'tdx_model', asset.get('ProductModelName', ''))
            self.inventory.set_variable(hostname, 'tdx_status', asset.get('StatusName', ''))
            self.inventory.set_variable(hostname, 'tdx_location', asset.get('LocationName', ''))
            self.inventory.set_variable(hostname, 'tdx_owner_dept', asset.get('OwningDepartmentName', ''))

            # Group: location
            location = asset.get('LocationName') or 'unknown_location'
            loc_group = 'loc_' + self._slugify(location)
            self.inventory.add_group(loc_group)
            self.inventory.add_child(loc_group, hostname)

            # Group: status
            status = asset.get('StatusName') or 'unknown_status'
            status_group = 'status_' + self._slugify(status)
            self.inventory.add_group(status_group)
            self.inventory.add_child(status_group, hostname)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _slugify(name):
        return name.lower().replace(' ', '_').replace('-', '_').replace('/', '_')

    @staticmethod
    def _auth(base_url, username, password):
        """Authenticate against TDX /auth and return a bearer token."""
        payload = json.dumps({'username': username, 'password': password}).encode()
        req = urllib.request.Request(
            f"{base_url}/auth",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req) as resp:
            # TDX returns the JWT as a quoted JSON string value
            return json.loads(resp.read().decode())

    @staticmethod
    def _search_assets(base_url, app_id, token):
        """Return all assets from the TDX asset search endpoint."""
        payload = json.dumps({'SearchText': ''}).encode()
        req = urllib.request.Request(
            f"{base_url}/{app_id}/assets/search",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
            method='POST',
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
