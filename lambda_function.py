# import json

# def lambda_handler(event, context):
#     # TODO implement
#     return {
#         'statusCode': 200,
#         'body': json.dumps('Hello from Lambda!')
#     }

# import os
# import json
# import hmac
# import hashlib
# import base64

# #check 
# # Set this in Lambda console: Configuration → Environment variables
# # Use the exact same secret string when you create the GitHub webhook.
# SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# def _body_bytes(event):
#     body = event.get("body") or ""
#     if event.get("isBase64Encoded"):
#         return base64.b64decode(body)
#     return body.encode("utf-8")

# def _resp(code: int, body, content_type="application/json"):
#     return {
#         "statusCode": code,
#         "headers": {"content-type": content_type},
#         "body": body if isinstance(body, str) else json.dumps(body),
#     }

# def lambda_handler(event, context):
#     # Require secret to mitigate spoofing
#     if not SECRET:
#         return _resp(500, {"error": "Missing GITHUB_WEBHOOK_SECRET"})

#     # Normalize headers to lowercase
#     headers = { (k or "").lower(): v for k, v in (event.get("headers") or {}).items() }
#     sig_header = headers.get("x-hub-signature-256")
#     gh_event   = headers.get("x-github-event")

#     if not sig_header or not sig_header.startswith("sha256="):
#         return _resp(401, {"error": "Missing/invalid signature"})

#     # Compute HMAC over the exact raw body
#     body_bytes = _body_bytes(event)
#     digest = hmac.new(SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
#     if not hmac.compare_digest(f"sha256={digest}", sig_header):
#         return _resp(401, {"error": "Bad signature"})

#     # Respond fast to GitHub's test
#     if gh_event == "ping":
#         return _resp(200, {"msg": "pong"})

#     # Parse JSON payload (GitHub sends application/json)
#     try:
#         payload = json.loads(body_bytes.decode("utf-8"))
#     except Exception:
#         return _resp(400, {"error": "Invalid JSON"})

#     # === Your event-specific logic here ===
#     # Example: react to Issues events
#     if gh_event == "issues":
#         action = payload.get("action")
#         issue  = (payload.get("issue") or {})
#         return _resp(200, {
#             "status": "ok",
#             "event": gh_event,
#             "action": action,
#             "issue_url": issue.get("html_url"),
#             "title": issue.get("title"),
#         })

#     # Default: acknowledge other events
#     return _resp(200, {"status": "ok", "event": gh_event})

import json
import os
import logging
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SLACK_URL = os.environ.get("SLACK_URL")  # set in Lambda → Configuration → Environment variables

def _post_to_slack(text: str) -> tuple[bool, str]:
    if not SLACK_URL:
        return False, "Missing SLACK_URL"
    data = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return (200 <= resp.status < 300), resp.read().decode("utf-8")

def lambda_handler(event, context):
    # Log a truncated view of the incoming event
    try:
        logger.info("FunctionHandler received: %s", json.dumps(event)[:2000])
    except Exception:
        logger.info("FunctionHandler received (non-serializable event)")

    # Accept either API Gateway proxy format (event["body"]) or a direct JSON payload
    payload = event
    if isinstance(event, dict) and "body" in event:
        try:
            payload = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except Exception:
            payload = {}

    # Try to grab issue.html_url from the payload
    issue_url = None
    if isinstance(payload, dict):
        issue = payload.get("issue") or {}
        issue_url = issue.get("html_url")

    # Fallback: sometimes callers send the GitHub JSON directly in event
    if not issue_url and isinstance(event, dict):
        issue_url = (event.get("issue") or {}).get("html_url")

    # Build Slack message
    text = f"Issue Created: {issue_url}" if issue_url else "Issue Created (no html_url found in payload)"

    ok, resp_body = _post_to_slack(text)
    status = 200 if ok else 500

    return {
        "statusCode": status,
        "body": resp_body if isinstance(resp_body, str) else json.dumps({"status": "ok" if ok else "error"})
    }
