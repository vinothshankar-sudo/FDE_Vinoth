"""Offline tests for helpers.py. Run: python3 test_helpers.py"""
from types import SimpleNamespace as NS

import helpers as H


def check(name, condition):
    print(("PASS " if condition else "FAIL ") + name)
    if not condition:
        raise SystemExit(1)


chunks = H.rows_to_dicts(H.CHUNK_COLUMNS, [
    ["INC-1#c1", "INC-1", "sell_in", "incident", "Incident note", "off-by-one in the date filter"],
    ["RB-1#c3", "RB-1", "sell_in", "runbook", "Common causes", "make the end date inclusive"]])
check("rows_to_dicts keeps order and keys", chunks[0]["chunk_id"] == "INC-1#c1" and chunks[1]["section"] == "Common causes")

msgs = H.build_messages("Why?", chunks)
check("two messages, system first", [m["role"] for m in msgs] == ["system", "user"])
check("context labels S1 and S2", "[S1] (source: INC-1#c1" in msgs[1]["content"] and "[S2] (source: RB-1#c3" in msgs[1]["content"])
check("question at the end", msgs[1]["content"].endswith("Question: Why?"))

check("cited labels sorted numerically", H.cited_labels("a [S10] b [S2] c [S2]") == ["S2", "S10"])
ok = H.citation_check("Fact [S1]. Fix [S2].", 2)
check("valid citations", ok["all_valid"] and ok["has_citation"] and not ok["refused"])
bad = H.citation_check("Fact [S3].", 2)
check("invalid citation detected", not bad["all_valid"])
check("no citation detected", not H.citation_check("No labels.", 2)["has_citation"])
check("refusal detected", H.citation_check(H.NOT_FOUND_TEXT, 2)["refused"])

message = NS(attachments=[
    NS(attachment_id="a1", text=NS(content="West is higher."), query=None),
    NS(attachment_id="a2", text=None, query=NS(query="SELECT 1", description="demo"))])
parts = H.genie_parts(message)
check("genie text extracted", parts["texts"] == ["West is higher."])
check("genie sql extracted", parts["queries"][0]["sql"] == "SELECT 1" and parts["queries"][0]["attachment_id"] == "a2")
old_style = NS(attachments=[NS(id="a9", text=None, query=NS(query="SELECT 2", description=None))])
check("genie attachment with only `id` (older SDK)", H.genie_parts(old_style)["queries"][0]["attachment_id"] == "a9")
check("genie empty message", H.genie_parts(NS(attachments=None)) == {"texts": [], "queries": []})

resp = NS(statement_response=NS(manifest=NS(schema=NS(columns=[NS(name="region"), NS(name="net")])),
                                result=NS(data_array=[["West", "12463.04"], ["East", "9893.50"]])))
check("statement rows", H.statement_rows(resp) == {"columns": ["region", "net"], "rows": [["West", "12463.04"], ["East", "9893.50"]]})
check("statement rows empty", H.statement_rows(NS(statement_response=None)) == {"columns": [], "rows": []})

class NotFound(Exception):
    pass


class ResourceDoesNotExist(NotFound):
    pass


class TooManyRequests(Exception):
    pass


class Weird(Exception):
    pass


check("not found class is classified", H.classify_error(NotFound("x"))["kind"] == "not_found")
check("subclass is found through its parents", H.classify_error(ResourceDoesNotExist("x"))["kind"] == "not_found")
check("429 class is busy", H.classify_error(TooManyRequests("x"))["kind"] == "busy")
check("builtin TimeoutError is timeout", H.classify_error(TimeoutError("x"))["kind"] == "timeout")
check("unknown exception gets a safe message", H.classify_error(Weird("secret detail"))["kind"] == "unknown")
check("friendly text does not contain the raw message", "secret detail" not in str(H.classify_error(Weird("secret detail"))))
check("every kind has a title and advice", all(len(v) == 2 and all(v) for v in H.FRIENDLY.values()))
check("short() trims long text", len(H.short("a " * 500, 50)) == 50 and H.short("a  b") == "a b")
print("all tests passed")
