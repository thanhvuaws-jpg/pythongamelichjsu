"""Kết nối thế giới chung cho nhiều người chơi.

Trên web, trang chơi (web/js/play.js) giữ WebSocket tới máy chủ và để sẵn `window.SKNet` (send, take, status); game chạy
trong khung cùng nguồn nên đọc ghi qua `window.parent.SKNet` bằng chuỗi JSON. Ô gõ chat cũng nằm ở trang chơi
(`window.SKChat`: open, take) để gõ được tiếng Việt bằng bộ gõ của máy. Trên máy tính, hoặc mở game riêng không qua trang
chơi, thì không có mạng: mọi hàm thành không làm gì và game chơi một mình như cũ.
"""

from __future__ import annotations

import json

from core import platform_io

# Lời nói nhanh: các câu có sẵn, gửi theo số thứ tự. Chat gõ tự do đi riêng (tin "chat"), máy chủ lọc chữ và chặn gửi dồn.
PHRASES = (
    "Xin chào!", "Cùng đánh quái không?", "Cảm ơn bạn!", "Đi theo mình!", "Chờ mình một chút.", "Giỏi lắm!",
    "Mình đi báo cáo già làng đây.", "Bạn học di tích này chưa?", "Thách đấu không?", "Hẹn gặp lại!",
    "Cẩn thận, quái mạnh đấy!", "Cùng ôn bài nhé!",
)


CHANNELS = ("map", "world")
CHAT_KEEP = 40  # số tin chat giữ lại để vẽ
CHAT_LEN = 120
DUEL_MSGS = ("pvp", "pvp_hit", "pvp_over")  # để riêng cho cảnh thách đấu, màn chơi không lấy mất
DUEL_KEEP = 200


class WebPipe:
    """Ống nối tới `window.parent.SKNet` của trang chơi."""

    def __init__(self, obj):
        self.obj = obj

    def send(self, raw: str) -> None:
        self.obj.send(raw)

    def take(self) -> str:
        return str(self.obj.take())

    def status(self) -> str:
        return str(self.obj.status())


class ChatPipe:
    """Ống nối tới `window.parent.SKChat`: mở ô gõ chat và lấy các tin người chơi vừa gõ."""

    def __init__(self, obj):
        self.obj = obj

    def open(self, ch: str) -> None:
        self.obj.open(ch)

    def take(self) -> list[dict]:
        out = json.loads(str(self.obj.take()))
        return [m for m in out if isinstance(m, dict)] if isinstance(out, list) else []


def find_chat():
    if not platform_io.IS_WEB:
        return None
    try:
        import platform

        pipe = ChatPipe(platform.window.parent.SKChat)
        pipe.take()  # thử gọi một lần: không có SKChat thì ném lỗi ở đây
        return pipe
    except Exception:  # noqa: BLE001  mở game riêng, không qua trang chơi
        return None


def find_pipe():
    if not platform_io.IS_WEB:
        return None
    try:
        import platform

        obj = platform.window.parent.SKNet
        pipe = WebPipe(obj)
        pipe.status()  # thử gọi một lần: không có SKNet thì ném lỗi ở đây
        return pipe
    except Exception:  # noqa: BLE001  mở game riêng, không qua trang chơi
        return None


class Net:
    def __init__(self, pipe=None, chat_pipe=None):
        self.pipe = pipe
        self.chat_pipe = chat_pipe
        self.chat: list[dict] = []  # tin chat đã nhận: kênh, người gửi, nội dung, đã hiện bao lâu
        self.me: dict | None = None
        self.peers: list[dict] = []
        self.peers_map: str | None = None
        self.party: dict | None = None
        self.allies: list[dict] = []
        self.invites: list[dict] = []
        self.events: list[dict] = []
        self.duel: list[dict] = []  # tin của trận thách đấu đang đánh (trạng thái đối thủ, đòn trúng, kết quả)

    @property
    def available(self) -> bool:
        return self.pipe is not None

    @property
    def online(self) -> bool:
        try:
            return self.pipe is not None and self.pipe.status() == "on" and self.me is not None
        except Exception:  # noqa: BLE001
            return False

    def status_text(self) -> str:
        if self.pipe is None:
            return "Chơi một mình (mở game qua trang chơi để gặp người khác)"
        try:
            st = self.pipe.status()
        except Exception:  # noqa: BLE001
            st = "off"
        return {"on": "Đã vào thế giới chung", "connecting": "Đang kết nối thế giới chung..."}.get(st, "Mất kết nối, đang thử lại...")

    def send(self, msg: dict) -> None:
        if self.pipe is None:
            return
        try:
            # thuần ASCII: chuỗi có dấu đi từ Python sang JavaScript trong pygbag bị đọc sai mã
            self.pipe.send(json.dumps(msg, ensure_ascii=True, separators=(",", ":")))
        except Exception:  # noqa: BLE001  mất kết nối thì bỏ tin, trang chơi tự nối lại
            return

    def poll(self) -> None:
        if self.pipe is None:
            return
        try:
            msgs = json.loads(self.pipe.take())
        except Exception:  # noqa: BLE001
            return
        for m in msgs if isinstance(msgs, list) else ():
            if isinstance(m, dict):
                self._apply(m)

    def _apply(self, m: dict) -> None:
        kind = m.get("t")
        if kind == "hello":
            self.me = {"id": m.get("you"), "name": m.get("name", "")}
        elif kind == "peers":
            self.peers = [p for p in m.get("list", []) if isinstance(p, dict)]
            self.peers_map = m.get("map")
        elif kind == "party":
            self.party = m.get("party")
        elif kind == "allies":
            self.allies = m.get("list", [])
        elif kind == "invite":
            self.invites = [i for i in self.invites if (i["kind"], i["from"]) != (m.get("kind"), m.get("from"))]
            self.invites.append(m)
        elif kind == "chat":
            if self._add_chat(m):
                self.events.append(m)  # để màn chơi vẽ bong bóng lời nói trên đầu người gửi
        elif kind == "chat_recent":
            for c in m.get("list", []) if isinstance(m.get("list"), list) else ():
                if isinstance(c, dict):
                    self._add_chat(c)
        elif kind == "error":
            self.me = None
        elif kind in DUEL_MSGS:
            self.duel.append(m)
            del self.duel[:-DUEL_KEEP]
        else:  # say, notice, share, pvp_start: để màn chơi xử lý
            self.events.append(m)

    def _add_chat(self, m: dict) -> bool:
        if m.get("ch") not in CHANNELS or not isinstance(m.get("text"), str):
            return False
        mine = bool(self.me) and m.get("from") == self.me.get("id")
        self.chat.append({"ch": m["ch"], "from": m.get("from"), "name": str(m.get("name", ""))[:32], "text": m["text"][:CHAT_LEN],
                          "mine": mine, "age": 0.0})
        del self.chat[:-CHAT_KEEP]
        return True

    # ----- ô gõ chat ở trang chơi -----
    @property
    def chat_available(self) -> bool:
        return self.chat_pipe is not None

    def open_chat(self, ch: str = "map") -> bool:
        if self.chat_pipe is None:
            return False
        try:
            self.chat_pipe.open(ch if ch in CHANNELS else "map")
            return True
        except Exception:  # noqa: BLE001
            return False

    def take_chat(self) -> list[dict]:
        if self.chat_pipe is None:
            return []
        try:
            return self.chat_pipe.take()
        except Exception:  # noqa: BLE001
            return []

    def take_duel(self, room: str) -> list[dict]:
        """Lấy các tin của trận `room`, bỏ tin của trận cũ còn sót."""
        out = [m for m in self.duel if m.get("room") == room]
        self.duel = []
        return out

    def answer(self, invite: dict, ok: bool) -> None:
        self.send({"t": "answer", "kind": invite["kind"], "from": invite["from"], "ok": ok})
        if invite in self.invites:
            self.invites.remove(invite)

    def invite(self, kind: str, uid: str) -> None:
        self.send({"t": "invite", "kind": kind, "to": uid})

    def in_party(self, uid: str) -> bool:
        return bool(self.party) and any(m.get("id") == uid for m in self.party.get("members", []))

    def is_ally(self, uid: str) -> bool:
        return any(a.get("id") == uid for a in self.allies)


_net: Net | None = None


def get() -> Net:
    """Một kết nối cho cả game; tìm ống nối lần đầu được gọi."""
    global _net
    if _net is None:
        _net = Net(find_pipe(), find_chat())
    return _net


def use(net: Net) -> None:
    """Đặt kết nối khác (kiểm thử)."""
    global _net
    _net = net
