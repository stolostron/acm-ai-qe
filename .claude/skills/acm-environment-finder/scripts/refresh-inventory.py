#!/usr/bin/env python3
"""
Refresh ~/.acm-env-inventory/inventory.json from Jenkins provisioning jobs.

Requires VPN for Red Hat Jenkins. Credentials: ~/.jenkins/config.json
  jenkins_url, jenkins_user, jenkins_token
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
from base64 import b64encode
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_JOBS = [
    "CI-Jobs/ocp_deploy_and_acm_install",
    "CI-Jobs/ocp_deploy_and_mce_install",
]


def job_api_path(job_path: str) -> str:
    parts = job_path.strip("/").split("/")
    return "/".join(f"job/{quote(p, safe='')}" for p in parts)


def jenkins_get(base_url: str, user: str, token: str, path: str, ctx: ssl.SSLContext) -> dict:
    url = base_url.rstrip("/") + path
    auth = b64encode(f"{user}:{token}".encode()).decode()
    req = Request(url, headers={"Authorization": f"Basic {auth}"})
    with urlopen(req, context=ctx, timeout=120) as resp:
        return json.load(resp)


def extract_parameters(actions: list | None) -> dict[str, str]:
    for a in actions or []:
        if not isinstance(a, dict):
            continue
        if a.get("_class") == "hudson.model.ParametersAction":
            out: dict[str, str] = {}
            for p in a.get("parameters") or []:
                if isinstance(p, dict) and "name" in p:
                    v = p.get("value")
                    out[p["name"]] = "" if v is None else str(v)
            return out
    return {}


def extract_artifact_paths(build_obj: dict) -> list[str]:
    arts = build_obj.get("artifacts") or []
    paths: list[str] = []
    for a in arts:
        if isinstance(a, dict) and a.get("relativePath"):
            paths.append(a["relativePath"])
    return paths


def kubeconfig_present(paths: list[str]) -> bool:
    for p in paths:
        if p.endswith("kubeconfig") or p == "ocp_credentials/kubeconfig" or p.endswith("/kubeconfig"):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh ACM env inventory from Jenkins")
    parser.add_argument("--config", default=os.path.expanduser("~/.jenkins/config.json"))
    parser.add_argument("--out-dir", default=os.path.expanduser("~/.acm-env-inventory"))
    parser.add_argument("--max-builds", type=int, default=25)
    parser.add_argument("--jobs", nargs="*", default=DEFAULT_JOBS)
    parser.add_argument("--dry-run", action="store_true", help="Print JSON to stdout only")
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print(f"Missing {args.config}", file=sys.stderr)
        return 2

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    base = cfg.get("jenkins_url") or cfg.get("url")
    user = cfg.get("jenkins_user") or cfg.get("user")
    token = cfg.get("jenkins_token") or cfg.get("token")
    if not base or not user or not token:
        print("jenkins_url, jenkins_user, jenkins_token required in config", file=sys.stderr)
        return 2

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    entries: list[dict] = []
    errors: list[dict] = []

    for job_path in args.jobs:
        jpath = "/" + job_api_path(job_path) + "/api/json"
        try:
            job = jenkins_get(base, user, token, jpath + "?tree=builds[number,url,result,timestamp]", ctx)
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            errors.append({"job": job_path, "error": repr(e)})
            continue

        builds = job.get("builds") or []
        for b in builds[: args.max_builds]:
            num = b.get("number")
            if num is None:
                continue
            bpath = "/" + job_api_path(job_path) + f"/{num}/api/json"
            try:
                bd = jenkins_get(base, user, token, bpath, ctx)
            except (HTTPError, URLError, TimeoutError, OSError) as e:
                errors.append({"job": job_path, "build": num, "error": repr(e)})
                continue

            params = extract_parameters(bd.get("actions"))
            rel_arts = extract_artifact_paths(bd)

            entry = {
                "jenkins_job_path": job_path,
                "jenkins_build_number": bd.get("number"),
                "jenkins_build_url": bd.get("url"),
                "build_result": bd.get("result"),
                "build_timestamp": bd.get("timestamp"),
                "cluster_name": params.get("OCP_CLUSTER_NAME") or None,
                "cloud_provider": params.get("CLOUD_PROVIDER") or None,
                "ocp_version": params.get("OCP_VERSION") or None,
                "ocp_release": params.get("OCP_RELEASE") or None,
                "region": params.get("REGION") or None,
                "rhacm_snapshot_tag": params.get("RHACM_SNAPSHOT_TAG") or None,
                "acm_channel": params.get("ACM_CHANNEL") or None,
                "mce_snapshot_tag": params.get("MCE_SNAPSHOT_TAG") or None,
                "skip_acm_install": str(params.get("SKIP_ACM_INSTALL", "")).lower() == "true",
                "fips_enabled": str(params.get("FIPS_ENABLED", "")).lower() == "true",
                "has_kubeconfig_artifact": kubeconfig_present(rel_arts),
                "artifact_relative_paths": rel_arts,
                "last_health_check": None,
                "health_status": None,
            }
            entries.append(entry)

    payload = {
        "generated_at_ms": int(time.time() * 1000),
        "entries": entries,
        "errors": errors,
    }

    if args.dry_run:
        sys.stdout.write(json.dumps(payload, indent=2))
        sys.stdout.write("\n")
        return 0

    os.makedirs(args.out_dir, exist_ok=True)
    out_json = os.path.join(args.out_dir, "inventory.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    stamp = os.path.join(args.out_dir, "last-refresh.txt")
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(str(int(time.time())))
    print(f"Wrote {len(entries)} entries to {out_json}")
    if errors:
        print(f"Warnings: {len(errors)} fetch errors", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
