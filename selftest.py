"""Offline test of store bot flows (Telegram API stubbed)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "store"))

os.environ["STORE_TG_TOKEN"] = "DUMMY"
os.environ["ADMIN_ID"] = "999"

import bot

CALLS = []
UID, MID = 111, 1


def fake_post(url, **kw):
    CALLS.append((url, kw.get("json", {})))
    class R:
        def json(self):
            if url.endswith("/getMe"):
                return {"ok": True, "result": {"username": "testbot"}}
            if url.endswith("/getFile"):
                return {"ok": True, "result": {"file_path": "x/y.csv"}}
            return {"ok": True, "result": {}}
    return R()


bot.requests.post = fake_post
# stub file download
bot.requests.get = lambda *a, **k: type("R", (), {"content": b"a,b\n1,2"})()


def msg(text=None, doc=None, mid=None):
    global MID
    MID += 1
    m = {"message_id": mid or MID, "chat": {"id": UID},
         "from": {"id": UID, "username": "tester"}}
    if text is not None:
        m["text"] = text
    if doc:
        m["document"] = {"file_id": "FID", "file_name": doc, "file_size": 100}
    return {"update_id": MID, "message": m}


def cb(data):
    return {"update_id": 9000, "callback_query": {
        "id": "cb1", "data": data,
        "message": {"message_id": 5, "chat": {"id": UID}}}}


def sent_to(uid):
    return [c for _, c in CALLS if c.get("chat_id") == uid]


def main():
    global UID
    for f in (bot.STATE, bot.TICKETS):
        if os.path.exists(f):
            os.remove(f)

    bot.handle_update(msg("/start"))
    assert any("متجر" in c.get("text", "") for c in sent_to(UID)), "start"

    bot.handle_update(cb("order:script"))
    bot.handle_update(msg("أريد سكربت يجمع أسعار"))
    bot.handle_update(msg("تم"))
    admin = sent_to(999)
    assert any("T-0001" in c.get("text", "") for c in admin), "ticket notify"
    assert any("T-0001" in c.get("text", "") for c in sent_to(UID)), "ticket ack"
    tickets = json.load(open(bot.TICKETS, encoding="utf-8"))
    assert tickets[0]["service"] == "script" and "أسعار" in tickets[0]["details"]

    bot.handle_update(msg("/paid abc123"))
    assert any("abc123" in c.get("text", "") for c in sent_to(999)), "paid fwd"

    bot.handle_update(cb("order:clean"))
    assert any("BaranExcel_cleaner_bot" in c.get("text", "") for c in sent_to(UID))

    bot.handle_update(msg(None, doc="data.csv"))
    bot.handle_update(msg("نظفه"))
    bot.handle_update(msg("تم"))
    tickets = json.load(open(bot.TICKETS, encoding="utf-8"))
    assert tickets[1]["service"] == "file", tickets[1]
    fwd = [u for u, c in CALLS if u.endswith("/forwardMessage")]
    assert fwd, "file forwarded to admin"

    # guard: hacking request refused, no ticket, logged
    UID = 222
    bot.handle_update(msg("/order"))
    bot.handle_update(cb("order:script"))
    bot.handle_update(msg("اريد سكربت لتجاوز المصادقة الثنائية للفيسبوك"))
    assert any("⛔" in c.get("text", "") for c in sent_to(222)), "refusal"
    tickets = json.load(open(bot.TICKETS, encoding="utf-8"))
    assert len(tickets) == 2, tickets
    assert not any("T-" in c.get("text", "") for c in sent_to(999)
                   if "تجاوز" in c.get("text", "")), "leaked to admin"
    assert os.path.exists(bot.REJECTED_LOG), "rejected log"
    # legit request still passes
    bot.handle_update(msg("/order"))
    bot.handle_update(cb("order:script"))
    bot.handle_update(msg("اريد سكربت تنظيف ملفات"))
    bot.handle_update(msg("تم"))
    tickets = json.load(open(bot.TICKETS, encoding="utf-8"))
    assert len(tickets) == 3 and tickets[2]["id"] == "T-0003", tickets

    print("STOREBOT TEST PASS — tickets:", len(tickets))


if __name__ == "__main__":
    main()
