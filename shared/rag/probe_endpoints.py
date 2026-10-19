"""Check which Databricks model endpoints a Free Edition workspace offers, and test one embedding and one chat call.

Run:  python3 probe_endpoints.py
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment. Makes 1 list call, 1 embedding call and 1 short chat call.
Override the endpoint names with RAG_EMBED_ENDPOINT and RAG_CHAT_ENDPOINT if the defaults are not available.
"""
import sys

import rag_lib as R


def main() -> int:
    R.setup_logging()
    R.LOGGER.info("step start: endpoint probe")
    client = R.DatabricksClient()
    R.write_out(f"Host: {client.host}")
    R.write_out(f"Token check (no token shown): length {client.token_length} after cleaning (raw length {client.raw_token_length}), starts with dapi and has no spaces = {client.token_looks_ok}")
    try:
        me = client.get("/api/2.0/preview/scim/v2/Me")
        R.write_out(f"Token accepted by the workspace: yes (user record has {len(me)} fields)")
    except Exception as exc:
        R.write_out(f"Token accepted by the workspace: NO ({exc})")
    try:
        listing = client.get("/api/2.0/serving-endpoints")
        names = sorted(e.get("name", "?") for e in listing.get("endpoints", []))
        R.write_out(f"Serving endpoints visible to this token ({len(names)}):")
        for name in names:
            R.write_out(f"  {name}")
    except Exception as exc:  # report any failure, then still try the two direct calls
        R.LOGGER.warning("could not list endpoints: %s", exc)
    embedder = R.DatabricksEmbedder(client)
    chat = R.DatabricksChat(client)
    ok = True
    try:
        vectors = embedder.embed(["probe: reconciliation mismatch"])
        R.write_out(f"Embedding endpoint {embedder.endpoint}: OK, vector length {vectors.shape[1]}")
    except Exception as exc:
        ok = False
        R.write_out(f"Embedding endpoint {embedder.endpoint}: FAILED ({exc})")
    try:
        dummy = [R.Hit(R.Chunk("T#c1", "T", "Test", "test", "all", "Test", "Fizzco uses the container fizzco-landing.", 6), 1.0, 1)]
        reply = chat.answer("Which container does Fizzco use?", dummy)
        R.write_out(f"Chat endpoint {chat.endpoint}: OK, reply: {reply[:120]}")
    except Exception as exc:
        ok = False
        R.write_out(f"Chat endpoint {chat.endpoint}: FAILED ({exc})")
    R.write_out(f"Endpoint calls made: {client.calls}")
    R.LOGGER.info("step end: done")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
