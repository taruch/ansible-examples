#!/usr/bin/env python3
"""
TeamDynamix CMDB Dynamic Inventory Script
==========================================

Queries the TeamDynamix Asset/CMDB API and returns an Ansible-compatible
inventory. Assets are grouped by Location and Status.

Usage:
  ansible-playbook site.yml -i tdx_cmdb_inventory.py
  ansible-inventory -i tdx_cmdb_inventory.py --list
  ansible-inventory -i tdx_cmdb_inventory.py --host <hostname>

Configuration (environment variables):
  TDX_INSTANCE          TDX subdomain (e.g. "myorg" → myorg.teamdynamix.com)
  TDX_APP_ID            Asset application ID (integer)
  TDX_BEID              Service account BEID (GUID)
  TDX_WS_KEY            Service account Web Services Key (GUID)
  TDX_HOST_ATTR_ID      ID of the custom asset attribute containing the
                        hostname or IP address (integer). If unset, the
                        asset Name field is used as ansible_host.
  TDX_STATUS_FILTER     Comma-separated list of asset status names to include.
                        Default: "In Use" only.
                        Example: "In Use,In Maintenance"

In AAP:
  Add this script as a "Script" inventory source. Set the environment
  variables above in the credential or inventory source environment vars.
  Grant the service account "Assets" read access in TDX Admin.
"""

import json
import os
import sys
import urllib.request
import urllib.error


def env(key, default=None, required=False):
    val = os.environ.get(key, default)
    if required and not val:
        print(f"[ERROR] Required environment variable {key} is not set.", file=sys.stderr)
        sys.exit(1)
    return val


def tdx_auth(base_url, beid, wskey):
    payload = json.dumps({"BEID": beid, "WebServicesKey": wskey}).encode()
    req = urllib.request.Request(
        f"{base_url}/auth/loginadmin",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        # TDX returns the JWT as a quoted JSON string
        return json.loads(resp.read().decode())


def tdx_search_assets(base_url, app_id, token, status_filter):
    payload = json.dumps({"StatusIDs": [], "SearchText": ""}).encode()
    req = urllib.request.Request(
        f"{base_url}/{app_id}/assets/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assets = json.loads(resp.read().decode())

    if status_filter:
        allowed = {s.strip().lower() for s in status_filter.split(",")}
        assets = [a for a in assets if a.get("StatusName", "").lower() in allowed]

    return assets


def slugify(name):
    """Convert a display name to a safe Ansible group name."""
    return name.lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def build_inventory(assets, host_attr_id):
    inventory = {"_meta": {"hostvars": {}}, "all": {"hosts": [], "children": []}}

    for asset in assets:
        # Determine the hostname / ansible_host value
        hostname = asset.get("Name", "").strip()
        if not hostname:
            continue

        ansible_host = hostname

        # If a custom attribute ID is configured, prefer that as the connection target
        if host_attr_id:
            for attr in asset.get("Attributes", []):
                if str(attr.get("ID")) == str(host_attr_id) and attr.get("Value"):
                    ansible_host = attr["Value"].strip()
                    break

        hostvars = {
            "ansible_host": ansible_host,
            "tdx_asset_id": asset.get("ID"),
            "tdx_serial": asset.get("SerialNumber", ""),
            "tdx_manufacturer": asset.get("ManufacturerName", ""),
            "tdx_model": asset.get("ProductModelName", ""),
            "tdx_status": asset.get("StatusName", ""),
            "tdx_location": asset.get("LocationName", ""),
            "tdx_owner_dept": asset.get("OwningDepartmentName", ""),
        }

        inventory["_meta"]["hostvars"][hostname] = hostvars
        inventory["all"]["hosts"].append(hostname)

        # Group by location
        location = asset.get("LocationName") or "unknown_location"
        loc_group = f"loc_{slugify(location)}"
        if loc_group not in inventory:
            inventory[loc_group] = {"hosts": []}
            inventory["all"]["children"].append(loc_group)
        inventory[loc_group]["hosts"].append(hostname)

        # Group by status
        status = asset.get("StatusName") or "unknown_status"
        status_group = f"status_{slugify(status)}"
        if status_group not in inventory:
            inventory[status_group] = {"hosts": []}
            inventory["all"]["children"].append(status_group)
        inventory[status_group]["hosts"].append(hostname)

    # Deduplicate children list
    inventory["all"]["children"] = list(dict.fromkeys(inventory["all"]["children"]))

    return inventory


def main():
    instance = env("TDX_INSTANCE", required=True)
    app_id = env("TDX_APP_ID", required=True)
    beid = env("TDX_BEID", required=True)
    wskey = env("TDX_WS_KEY", required=True)
    host_attr_id = env("TDX_HOST_ATTR_ID")
    status_filter = env("TDX_STATUS_FILTER", default="In Use")

    base_url = f"https://{instance}.teamdynamix.com/TDWebApi/api"

    # Handle --host (return empty hostvars; _meta covers it)
    if len(sys.argv) == 3 and sys.argv[1] == "--host":
        print(json.dumps({}))
        return

    # --list or default
    try:
        token = tdx_auth(base_url, beid, wskey)
        assets = tdx_search_assets(base_url, app_id, token, status_filter)
        inventory = build_inventory(assets, host_attr_id)
        print(json.dumps(inventory, indent=2))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"[ERROR] TDX API returned HTTP {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
