"""StoreBot state + tickets (JSON files, no database needed)."""
import json
import os


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def get_state(path, user_id):
    return _load(path, {}).get(str(user_id), {"step": "idle"})


def set_state(path, user_id, state):
    data = _load(path, {})
    data[str(user_id)] = state
    _save(path, data)


def clear_state(path, user_id):
    data = _load(path, {})
    data.pop(str(user_id), None)
    _save(path, data)


def add_ticket(path, ticket):
    tickets = _load(path, [])
    tid = "T-%04d" % (len(tickets) + 1)
    ticket["id"] = tid
    tickets.append(ticket)
    _save(path, tickets)
    return tid
