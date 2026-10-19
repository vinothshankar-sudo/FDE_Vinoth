"""Ask Genie a question and a follow-up through the Genie Conversation API, and extract the generated SQL.

Credentials and ids come from environment variables only (never from the code or the repo):
    DATABRICKS_HOST      workspace URL, for example https://dbc-xxxx.cloud.databricks.com
    DATABRICKS_TOKEN     personal access token of the user who may run the Genie space
    GENIE_SPACE_ID       id of the Genie space (the part after /genie/rooms/ in the space URL)

Usage:  python3 genie_api_demo.py
Synthetic Fizzco data only. Output goes to stdout; progress and errors go to stderr.
"""
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
LOGGER = logging.getLogger("genie_api_demo")

QUESTION = "What were net sell-in sales by region?"
FOLLOW_UP = "Now show only the East region, broken down by retailer."

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"}
POLL_START_SECONDS = 2.0
POLL_MAX_SECONDS = 20.0
POLL_TIMEOUT_SECONDS = 600
HTTP_TIMEOUT_SECONDS = 30
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4


class GenieError(RuntimeError):
    """Raised when the Genie API call fails or returns an unusable answer."""


def load_config() -> Tuple[str, str, str]:
    """Read host, token and space id from the environment. Never logs the token."""
    host = os.environ.get("DATABRICKS_HOST", "").strip().rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    space_id = os.environ.get("GENIE_SPACE_ID", "").strip()
    missing = [name for name, value in (("DATABRICKS_HOST", host), ("DATABRICKS_TOKEN", token),
                                        ("GENIE_SPACE_ID", space_id)) if not value]
    if missing:
        raise GenieError("missing environment variables: " + ", ".join(missing))
    if not host.startswith(("http://", "https://")):
        host = "https://" + host
    return host, token, space_id


def call_api(host: str, token: str, method: str, path: str,
             body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call the REST API with retries and exponential backoff on 429 and 5xx."""
    url = host + path
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    delay = 1.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.request(method, url, headers=headers, json=body,
                                        timeout=HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            LOGGER.warning("request error on %s %s (attempt %d): %s", method, path, attempt, exc)
        else:
            if response.status_code not in RETRY_STATUSES:
                if response.status_code >= 400:
                    raise GenieError("%s %s returned HTTP %d: %s"
                                     % (method, path, response.status_code, response.text[:300]))
                return response.json() if response.content else {}
            LOGGER.warning("HTTP %d on %s %s (attempt %d)", response.status_code, method, path, attempt)
        if attempt < MAX_ATTEMPTS:
            time.sleep(delay)
            delay *= 2
    raise GenieError("gave up on %s %s after %d attempts" % (method, path, MAX_ATTEMPTS))


def wait_for_message(host: str, token: str, base: str, message_id: str) -> Dict[str, Any]:
    """Poll the message until it reaches a final status (1 to 5 s at first, backing off, 10 min limit)."""
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    delay = POLL_START_SECONDS
    while True:
        message = call_api(host, token, "GET", "%s/messages/%s" % (base, message_id))
        status = message.get("status", "UNKNOWN")
        LOGGER.info("message %s status: %s", message_id, status)
        if status in TERMINAL_STATUSES:
            return message
        if time.monotonic() > deadline:
            raise GenieError("timed out waiting for message %s (last status %s)" % (message_id, status))
        time.sleep(delay)
        delay = min(delay * 1.5, POLL_MAX_SECONDS)


def extract_queries(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the query attachments: the generated SQL, its title and its attachment id."""
    found = []
    for attachment in message.get("attachments") or []:
        query = attachment.get("query")
        if query and query.get("query"):
            found.append({"attachment_id": attachment.get("attachment_id") or query.get("attachment_id"),
                          "title": query.get("title", ""), "sql": query["query"]})
    return found


def fetch_rows(host: str, token: str, base: str, message_id: str,
               attachment_id: Optional[str]) -> Tuple[List[str], List[List[Any]]]:
    """Fetch the result of a query attachment: column names and rows."""
    if not attachment_id:
        return [], []
    path = "%s/messages/%s/attachments/%s/query-result" % (base, message_id, attachment_id)
    result = call_api(host, token, "GET", path).get("statement_response", {})
    columns = [c.get("name", "") for c in (result.get("manifest", {}).get("schema", {}).get("columns") or [])]
    return columns, result.get("result", {}).get("data_array") or []


def ask(host: str, token: str, space_id: str, question: str,
        conversation_id: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Send a question (new conversation, or a follow-up in the same thread) and wait for the answer."""
    spaces = "/api/2.0/genie/spaces/%s" % space_id
    if conversation_id is None:
        started = call_api(host, token, "POST", spaces + "/start-conversation", {"content": question})
        conversation_id = started.get("conversation_id") or started.get("message", {}).get("conversation_id")
        message_id = started.get("message_id") or started.get("message", {}).get("message_id") \
            or started.get("message", {}).get("id")
    else:
        sent = call_api(host, token, "POST", "%s/conversations/%s/messages" % (spaces, conversation_id),
                        {"content": question})
        message_id = sent.get("message_id") or sent.get("id")
    if not conversation_id or not message_id:
        raise GenieError("could not read conversation_id and message_id from the response")
    base = "%s/conversations/%s" % (spaces, conversation_id)
    message = wait_for_message(host, token, base, message_id)
    message["_base"], message["_message_id"] = base, message_id
    return conversation_id, message


def report(host: str, token: str, label: str, question: str, message: Dict[str, Any]) -> None:
    """Write the question, status, generated SQL and result rows to stdout."""
    out = sys.stdout.write
    out("=== %s ===\nQuestion: %s\nStatus: %s\n" % (label, question, message.get("status")))
    if message.get("status") != "COMPLETED":
        out("Error: %s\n\n" % (message.get("error") or "no answer produced"))
        return
    for attachment in message.get("attachments") or []:
        text = attachment.get("text")
        if text and text.get("content"):
            out("Genie says: %s\n" % text["content"])
    for query in extract_queries(message):
        out("Generated SQL:\n%s\n" % query["sql"])
        columns, rows = fetch_rows(host, token, message["_base"], message["_message_id"], query["attachment_id"])
        out("Result (%d rows): %s\n" % (len(rows), " | ".join(columns)))
        for row in rows[:20]:
            out("  %s\n" % " | ".join(str(v) for v in row))
    out("\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr)
    LOGGER.info("step start: Genie API demo")
    try:
        host, token, space_id = load_config()
        conversation_id, first = ask(host, token, space_id, QUESTION, None)
        LOGGER.info("conversation id: %s", conversation_id)
        report(host, token, "Question 1 (new conversation)", QUESTION, first)
        _, second = ask(host, token, space_id, FOLLOW_UP, conversation_id)
        report(host, token, "Question 2 (follow-up in the same conversation)", FOLLOW_UP, second)
    except GenieError as exc:
        LOGGER.error("%s", exc)
        return 1
    LOGGER.info("step end: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
