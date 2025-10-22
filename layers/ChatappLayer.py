from .BaseLayer import BaseLayer

class ChatAppLayer(BaseLayer):
    def __init__(self, name: str):
        super().__init__()
        self.gui = None
        self.name = name

    def set_gui(self, gui):
        self.gui = gui
        self.gui.set_send_callback(self.gui_send_handler)

    def gui_send_handler(self, dst_mac_str: str, text: str):
        if not self.lower:
            return False
        try:
            dst = bytes.fromhex(dst_mac_str.replace(':', '').replace('-', ''))
            if len(dst) != 6:
                return False
            self.lower.set_dst_mac(dst)
            msg = f"[{self.name}] {text}".encode("utf-8")
            ok = self.lower.send(msg)
            if ok and self.gui:
                self.gui.display_message(self.name, text)
            return ok
        except Exception:
            return False

    def recv(self, data: bytes):
        if not self.gui:
            return False
        try:
            s = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            self.gui.display_message("SYSTEM", "[수신 디코딩 오류]")
            return False
        if s.startswith("[") and "]" in s:
            r = s.split("]", 1)
            sender = r[0].lstrip("[").strip()
            content = r[1].strip()
            self.gui.display_message(sender, content)
        else:
            self.gui.display_message("Unknown", s)
        return True

    def run(self):
        if self.lower:
            self.lower.start()
        if self.gui:
            self.gui.run()
        if self.lower:
            self.lower.stop()
