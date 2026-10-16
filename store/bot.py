#!/usr/bin/env python3
"""StoreBot — Baran's storefront bot (all services, one place).

/start → catalog + buttons → /order guided flow (service → details/file)
→ ticket forwarded to admin → pay USDT → /paid TXID → admin delivers.

Secrets ONLY from .env (never committed):
    STORE_TG_TOKEN=...   (NEW bot from @BotFather)
    ADMIN_ID=...         (Baran's numeric id)

Run:  python3 bot.py   (or via launchd for 24/7, see README)
"""
import os
import time
from datetime import datetime

import requests

import state as store

TOKEN = os.environ.get("STORE_TG_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
BASE = "https://api.telegram.org/bot" + TOKEN
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "store_state.json")
TICKETS = os.path.join(HERE, "tickets.json")

SERVICES = [
    {"id": "clean", "name": "🧹 تنظيف ملفات Excel/CSV",
     "price": "من 5$ — أول 3 مجاناً عبر @BaranExcel_cleaner_bot",
     "desc": "بوت فوري ينظف ملفك خلال ثوانٍ."},
    {"id": "script", "name": "🐍 سكربت Python مخصص",
     "price": "من 15$ USDT",
     "desc": "أتمتة، كشط بيانات عامة، معالجة ملفات وتقارير."},
    {"id": "webaudit", "name": "🔍 فحص أمني لموقعك",
     "price": "من 20$ USDT",
     "desc": "رؤوس أمنية + SSL + ملفات مكشوفة + تقرير (موقعك وبإذنك فقط)."},
    {"id": "timeline", "name": "🕵️ تحليل نسخة/واتساب + خط زمني",
     "price": "من 15$ USDT",
     "desc": "SMS + واتساب + صور GPS ← خط زمني وتقرير (بياناتك فقط)."},
]

PAY_TEXT = (
    "💰 الدفع مقدماً USDT-TRC20:\n"
    "`TLWdTjqqogkXNEXGiPWsGdjFP6ioycxeWW`\n\n"
    "🔒 خصوصية؟ BTC:\n"
    "`bc1q8dhtdrndxsl70e97t8grydfe6pjue37zrhzf6c`\n\n"
    "بعد الدفع أرسل: /paid رقم_العملية"
)
START_TEXT = (
    "🏪 أهلاً بك في متجر Baran Avisat!\n"
    "مبرمج محترف — تسليم سريع — دفع كريبتو.\n\n"
    "اختر من الأزرار أو أرسل /order لطلب خدمة."
)


def api(method, **kw):
    r = requests.post(BASE + "/" + method, json=kw, timeout=40)
    return r.json()


def send_text(chat, text, keyboard=None):
    kw = {"chat_id": chat, "text": text, "parse_mode": "Markdown"}
    if keyboard:
        kw["reply_markup"] = {"inline_keyboard": keyboard}
    return api("sendMessage", **kw)


def answer_cb(cb_id, text=""):
    return api("answerCallbackQuery", callback_query_id=cb_id, text=text[:180])


def main_kb():
    return [[{"text": "📦 الخدمات", "callback_data": "show:services"},
             {"text": "💰 الدفع", "callback_data": "show:pay"}],
            [{"text": "📝 طلب جديد", "callback_data": "order:new"}]]


def services_kb():
    rows = [[{"text": s["name"], "callback_data": "order:" + s["id"]}]
            for s in SERVICES]
    rows.append([{"text": "💰 الدفع", "callback_data": "show:pay"}])
    return rows


def services_text():
    return "📦 *الخدمات:*\n\n" + "\n\n".join(
        "*%s*\n%s\n%s" % (s["name"], s["price"], s["desc"])
        for s in SERVICES)


def svc_by_id(sid):
    for s in SERVICES:
        if s["id"] == sid:
            return s
    return {"id": sid, "name": sid, "price": "", "desc": ""}


def notify_admin(text, fwd=None):
    if not ADMIN_ID:
        return
    api("sendMessage", chat_id=int(ADMIN_ID), text=text)
    if fwd:
        try:
            requests.post(BASE + "/forwardMessage", json={
                "chat_id": int(ADMIN_ID),
                "from_chat_id": fwd[0], "message_id": fwd[1]}, timeout=30)
        except Exception:
            pass


def handle_message(msg):
    chat = (msg.get("chat") or {}).get("id")
    user = msg.get("from") or {}
    text = (msg.get("text") or "").strip()
    st = store.get_state(STATE, chat)

    if text.startswith("/start"):
        store.clear_state(STATE, chat)
        send_text(chat, START_TEXT, main_kb())
        return
    if text.startswith("/cancel"):
        store.clear_state(STATE, chat)
        send_text(chat, "❌ أُلغي الطلب. /order لطلب جديد.", main_kb())
        return
    if text.startswith("/order"):
        store.set_state(STATE, chat, {"step": "service"})
        send_text(chat, "📝 اختر الخدمة:", services_kb())
        return
    if text.startswith("/paid"):
        txid = text[5:].strip() or "—"
        notify_admin("💸 دفعة جديدة\nuser=%s (@%s) chat=%s\ntxid=%s" % (
            user.get("id"), user.get("username"), chat, txid))
        send_text(chat, "✅ استلمنا الدفعة، نراجعها ونبدأ التنفيذ قريباً.")
        return

    doc = msg.get("document")
    if doc and st.get("step") in ("idle", "details", "service"):
        # file starts/continues an order
        if st.get("step") == "idle":
            store.set_state(STATE, chat, {
                "step": "details", "service": "file",
                "file_msg": msg.get("message_id")})
            send_text(chat, "📎 استلمت الملف! اكتب الآن: ما المطلوب فيه؟ "
                            "(مثال: نظفه وارجعه Excel)")
        else:
            st["file_msg"] = msg.get("message_id")
            store.set_state(STATE, chat, st)
            send_text(chat, "📎 أُرفق الملف. أرسل باقي التفاصيل أو اكتب (تم).")
        return

    if st.get("step") == "details" and text:
        if text == "تم" and not st.get("details"):
            send_text(chat, "✏️ اكتب المطلوب أولاً ثم (تم).")
            return
        if text == "تم":
            ticket = {"user": user.get("id"), "username": user.get("username"),
                      "service": st.get("service"), "details": st.get("details", ""),
                      "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                      "status": "new"}
            tid = store.add_ticket(TICKETS, ticket)
            s = svc_by_id(st.get("service"))
            notify_admin(
                "🧾 طلب %s\nservice=%s\nuser=%s (@%s)\ndetails=%s" % (
                    tid, s["name"], user.get("id"), user.get("username"),
                    ticket["details"][:800]),
                fwd=(chat, st["file_msg"]) if st.get("file_msg") else None)
            store.clear_state(STATE, chat)
            send_text(chat, "✅ طلبك %s وصل! ادفع مقدماً ثم أرسل /paid:\n\n%s"
                            % (tid, PAY_TEXT), main_kb())
        else:
            st["details"] = (st.get("details", "") + "\n" + text).strip()[:1500]
            store.set_state(STATE, chat, st)
            send_text(chat, "📝 سُجّل. أضف تفاصيل أو اكتب (تم) للإرسال."
                            + (" (يمكنك إرفاق ملف أيضاً)" if not st.get("file_msg") else ""))
        return

    send_text(chat, "أرسل /order لطلب خدمة أو اختر من الأزرار.", main_kb())


def handle_callback(cb):
    data = cb.get("data", "")
    chat = (cb.get("message") or {}).get("chat", {}).get("id")
    cb_id = cb.get("id")
    if data == "show:services":
        send_text(chat, services_text(), services_kb())
    elif data == "show:pay":
        send_text(chat, PAY_TEXT, main_kb())
    elif data == "order:new":
        store.set_state(STATE, chat, {"step": "service"})
        send_text(chat, "📝 اختر الخدمة:", services_kb())
    elif data.startswith("order:"):
        sid = data.split(":", 1)[1]
        s = svc_by_id(sid)
        if sid == "clean":
            send_text(chat, "🧹 التنظيف فوري هنا:\n@BaranExcel_cleaner_bot\n"
                            "أول 3 ملفات مجاناً!", main_kb())
        else:
            store.set_state(STATE, chat, {"step": "details", "service": sid})
            send_text(chat, "اخترت: *%s*\n%s\n\n✏️ اكتب المطلوب بالتفصيل "
                            "(ويمكنك إرفاق ملف)، ثم اكتب (تم)." % (
                                s["name"], s["price"]))
    answer_cb(cb_id)


def handle_update(u):
    if u.get("callback_query"):
        try:
            handle_callback(u["callback_query"])
        except Exception as ex:
            print("callback error:", ex)
        return
    if u.get("message"):
        try:
            handle_message(u["message"])
        except Exception as ex:
            print("update error:", ex)


def main():
    if not TOKEN:
        print("Set STORE_TG_TOKEN env var (see .env.example).")
        raise SystemExit(1)
    me = api("getMe")
    print("storebot: @%s — polling..." % (me.get("result") or {}).get("username"))
    offset = 0
    while True:
        try:
            r = requests.post(BASE + "/getUpdates",
                              json={"offset": offset, "timeout": 30},
                              timeout=40).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                handle_update(u)
        except KeyboardInterrupt:
            print("\nstopped.")
            return
        except Exception as ex:
            print("poll error:", type(ex).__name__, "— retry in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
