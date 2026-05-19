#!/usr/bin/env python3
"""
Jenkins REST helper (Python 3 stdlib only).

Use for scripted/headless calls or alongside MCP: typical QE setups have the jenkins MCP
in both Cursor and Claude Code — prefer MCP there; use this
script when you need urllib/curl parity without loading the MCP.

Reads ~/.jenkins/config.json by default (same keys as acm-environment-finder refresh script).
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
from base64 import b64encode
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def job_api_path(job_path: str) -> str:
    parts = job_path.strip("/").split("/")
    return "/".join(f"job/{quote(p, safe='')}" for p in parts)


def ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def jenkins_request(
    base_url: str,
    user: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    form: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    url = base_url.rstrip("/") + path
    auth = b64encode(f"{user}:{token}".encode()).decode()
    headers: dict[str, str] = {"Authorization": f"Basic {auth}"}
    if extra_headers:
        headers.update(extra_headers)
    body: bytes | None = None
    if form is not None:
        body = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(url, data=body, headers=headers, method=method)
    with urlopen(req, context=ssl_ctx(), timeout=300) as resp:
        raw = resp.read()
    text = raw.decode(errors="replace")
    if path.endswith("consoleText") or path.endswith("consoleText/"):
        return text
    if path.endswith("/progressiveText"):
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def load_config(path: str) -> tuple[str, str, str]:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    base = cfg.get("jenkins_url") or cfg.get("url")
    user = cfg.get("jenkins_user") or cfg.get("user")
    token = cfg.get("jenkins_token") or cfg.get("token")
    if not base or not user or not token:
        print("Config needs jenkins_url, jenkins_user, jenkins_token (or url/user/token)", file=sys.stderr)
        raise SystemExit(2)
    return str(base), str(user), str(token)


def cmd_api(ns: argparse.Namespace) -> int:
    base, user, token = load_config(ns.config)
    path = ns.path
    if not path.startswith("/"):
        path = "/" + path
    try:
        out = jenkins_request(base, user, token, path, method="GET")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(repr(e), file=sys.stderr)
        return 1
    if isinstance(out, (dict, list)):
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(out)
    return 0


def cmd_console(ns: argparse.Namespace) -> int:
    base, user, token = load_config(ns.config)
    jpath = "/" + job_api_path(ns.job) + f"/{int(ns.build)}/consoleText"
    try:
        text = jenkins_request(base, user, token, jpath, method="GET")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(repr(e), file=sys.stderr)
        return 1
    assert isinstance(text, str)
    if ns.tail and ns.tail > 0:
        lines = text.splitlines()
        text = "\n".join(lines[-ns.tail :]) + ("\n" if lines else "")
    sys.stdout.write(text)
    return 0


def cmd_crumb(ns: argparse.Namespace) -> int:
    base, user, token = load_config(ns.config)
    try:
        data = jenkins_request(base, user, token, "/crumbIssuer/api/json", method="GET")
    except HTTPError as e:
        if e.code == 404:
            print("Crumb issuer not enabled (404). POST may work without crumb.", file=sys.stderr)
            return 0
        print(repr(e), file=sys.stderr)
        return 1
    except (URLError, TimeoutError, OSError) as e:
        print(repr(e), file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(data, file=sys.stderr)
        return 1
    field = data.get("crumbRequestField", "Jenkins-Crumb")
    crumb = data.get("crumb", "")
    print(f"{field}: {crumb}")
    return 0


def cmd_poll(ns: argparse.Namespace) -> int:
    base, user, token = load_config(ns.config)
    jpath = "/" + job_api_path(ns.job) + f"/{int(ns.build)}/api/json?tree=building,result,number,url"
    deadline = time.time() + ns.timeout
    while time.time() < deadline:
        try:
            data = jenkins_request(base, user, token, jpath, method="GET")
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            print(repr(e), file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print(data, file=sys.stderr)
            return 1
        building = data.get("building")
        result = data.get("result")
        if building is False and result is not None:
            json.dump(data, sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0
        time.sleep(ns.interval)
    print("Timeout waiting for build to finish", file=sys.stderr)
    return 124


def main() -> int:
    parser = argparse.ArgumentParser(description="Jenkins REST helper (stdlib)")
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.jenkins/config.json"),
        help="JSON with jenkins_url, jenkins_user, jenkins_token",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_api = sub.add_parser("api", help="GET JSON from a path (must start with /)")
    p_api.add_argument("path", help="e.g. /job/CI-Jobs/job/foo/lastSuccessfulBuild/api/json")
    p_api.set_defaults(func=cmd_api)

    p_con = sub.add_parser("console", help="GET consoleText for a job + build number")
    p_con.add_argument("job", help="e.g. CI-Jobs/ocp_deploy_and_acm_install")
    p_con.add_argument("build", help="Build number")
    p_con.add_argument("--tail", type=int, default=0, help="If >0, print only last N lines")
    p_con.set_defaults(func=cmd_console)

    p_cr = sub.add_parser("crumb", help="Print Jenkins-Crumb header line for curl")
    p_cr.set_defaults(func=cmd_crumb)

    p_po = sub.add_parser("poll", help="Poll build until building=false and result set")
    p_po.add_argument("job", help="e.g. CI-Jobs/ocp_deploy_and_acm_install")
    p_po.add_argument("build", help="Build number")
    p_po.add_argument("--interval", type=int, default=20, help="Seconds between polls")
    p_po.add_argument("--timeout", type=int, default=7200, help="Max seconds to wait (default 2h)")
    p_po.set_defaults(func=cmd_poll)

    ns = parser.parse_args()
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
