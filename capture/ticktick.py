r"""Small requests-based client for the TickTick Open API (open/v1).

Token lives in D:\vibecoding\_secrets\ticktick-token.json under
"access_token" (scope tasks:read tasks:write). The token is NEVER printed
or logged; errors carry only the HTTP status.

Every function accepts an optional `token` (tests / callers that already
hold one); None -> read the file. Timeout 15 s on every call.
"""

import json
import os

import requests

API_BASE = "https://api.ticktick.com/open/v1"
TOKEN_PATH = r"D:\vibecoding\_secrets\ticktick-token.json"
TIMEOUT = 15

# The three fixed list names (owner-facing, Uzbek). G'oyalar already exists
# in the owner's account (owner 11-08) and is matched by exact name - do not
# decorate it, that would create a duplicate list.
KIRUVCHI = "📥 Kiruvchi"
GOYALAR = "G'oyalar"
VAZIFALAR = "✅ Vazifalar"


class TickTickError(Exception):
    """Non-2xx TickTick answer; .status is the HTTP code."""

    def __init__(self, status, message=""):
        super().__init__(message or ("TickTick error %s" % status))
        self.status = status


class TokenExpired(TickTickError):
    """401: the token must be re-authorized (owner clicks Allow once)."""

    def __init__(self, message="TickTick token expired (401)"):
        super().__init__(401, message)


def load_token(path=TOKEN_PATH):
    """Read access_token from the secrets file. Raises OSError/ValueError."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["access_token"]
    if not isinstance(token, str) or not token:
        raise ValueError("ticktick-token.json: access_token is empty")
    return token


def _request(method, path, token=None, **kwargs):
    """One HTTP call with auth; raises TokenExpired on 401, TickTickError on
    any other non-2xx. Returns parsed JSON, or None for an empty body."""
    if token is None:
        token = load_token()
    headers = {"Authorization": "Bearer " + token}
    if "json" in kwargs:
        headers["Content-Type"] = "application/json"
    try:
        resp = requests.request(
            method, API_BASE + path, headers=headers, timeout=TIMEOUT, **kwargs
        )
    except requests.RequestException as e:
        err = TickTickError(0, type(e).__name__)
        raise err from None
    if resp.status_code == 401:
        raise TokenExpired()
    if not 200 <= resp.status_code < 300:
        # never include the body: it can echo the Authorization header back
        raise TickTickError(resp.status_code)
    if resp.status_code == 204 or not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        raise TickTickError(resp.status_code, "invalid JSON") from None


def list_projects(token=None):
    """GET /project -> list of project dicts."""
    return _request("GET", "/project", token=token) or []


def find_or_create_project(name, token=None):
    """Return the project id for `name`, creating the project when missing."""
    for p in list_projects(token=token):
        if p.get("name") == name:
            return p.get("id")
    body = {"name": name}
    created = _request("POST", "/project", token=token, json=body)
    if not created or not created.get("id"):
        raise TickTickError(0, "create project: no id in reply")
    return created["id"]


def project_tasks(project_id, token=None):
    """GET /project/{id}/data -> its task list."""
    data = _request("GET", "/project/%s/data" % project_id, token=token)
    return (data or {}).get("tasks", [])


def create_task(project_id, title, content="", token=None):
    """POST /task in project_id. Returns the created task dict."""
    body = {"title": title, "projectId": project_id}
    if content:
        body["content"] = content
    return _request("POST", "/task", token=token, json=body)


def update_task(task_id, project_id, fields, token=None):
    """POST /task/{id}: body must carry id + projectId alongside `fields`."""
    body = dict(fields)
    body["id"] = task_id
    body["projectId"] = project_id
    return _request("POST", "/task/%s" % task_id, token=token, json=body)


def move_task(task_id, from_project_id, to_project_id, token=None):
    """POST /task/move with the single-element move body."""
    body = [{
        "fromProjectId": from_project_id,
        "toProjectId": to_project_id,
        "taskId": task_id,
    }]
    return _request("POST", "/task/move", token=token, json=body)


def complete_task(project_id, task_id, token=None):
    """POST /project/{pid}/task/{tid}/complete."""
    return _request(
        "POST", "/project/%s/task/%s/complete" % (project_id, task_id), token=token
    )
