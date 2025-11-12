import json

def lambda_handler(event, context):
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

import os
import json
import hmac
import hashlib
import base64

#check 
# Set this in Lambda console: Configuration → Environment variables
# Use the exact same secret string when you create the GitHub webhook.
SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

def _body_bytes(event):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body.encode("utf-8")

def _resp(code: int, body, content_type="application/json"):
    return {
        "statusCode": code,
        "headers": {"content-type": content_type},
        "body": body if isinstance(body, str) else json.dumps(body),
    }

def lambda_handler(event, context):
    # Require secret to mitigate spoofing
    if not SECRET:
        return _resp(500, {"error": "Missing GITHUB_WEBHOOK_SECRET"})

    # Normalize headers to lowercase
    headers = { (k or "").lower(): v for k, v in (event.get("headers") or {}).items() }
    sig_header = headers.get("x-hub-signature-256")
    gh_event   = headers.get("x-github-event")

    if not sig_header or not sig_header.startswith("sha256="):
        return _resp(401, {"error": "Missing/invalid signature"})

    # Compute HMAC over the exact raw body
    body_bytes = _body_bytes(event)
    digest = hmac.new(SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"sha256={digest}", sig_header):
        return _resp(401, {"error": "Bad signature"})

    # Respond fast to GitHub's test
    if gh_event == "ping":
        return _resp(200, {"msg": "pong"})

    # Parse JSON payload (GitHub sends application/json)
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return _resp(400, {"error": "Invalid JSON"})

    # === Your event-specific logic here ===
    # Example: react to Issues events
    if gh_event == "issues":
        action = payload.get("action")
        issue  = (payload.get("issue") or {})
        return _resp(200, {
            "status": "ok",
            "event": gh_event,
            "action": action,
            "issue_url": issue.get("html_url"),
            "title": issue.get("title"),
        })

    # Default: acknowledge other events
    return _resp(200, {"status": "ok", "event": gh_event})

