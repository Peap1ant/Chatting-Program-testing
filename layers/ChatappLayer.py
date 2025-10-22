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
            dst_mac = bytes.fromhex(dst_mac_str.replace(':', ''))
        except ValueError:
            if self.gui:
                self.gui.display_message("SYSTEM", "잘못된 MAC 주소 형식입니다.")
            return False
        msg = f"[{self.name}]: {text}".encode('utf-8')
        from .EthernetLayer import EthernetLayer
        self.lower.set_dst_mac(dst_mac)
        self.lower.send(msg)
        if self.gui:
            self.gui.display_message("나", text)
        return True

    def recv(self, data: bytes):
        if not self.gui:
            return
        try:
            data = data.rstrip(b'\x00')
            full_message = data.decode('utf-8')
            if full_message.startswith('[') and ':' in full_message:
                parts = full_message.split(':', 1)
                sender = parts[0].strip('[]')
                content = parts[1].strip()
                self.gui.display_message(sender, content)
            else:
                self.gui.display_message("Unknown", full_message)
        except UnicodeDecodeError:
            self.gui.display_message("SYSTEM", "[오류] 수신된 데이터를 디코딩할 수 없습니다.")

    def run(self):
        if self.lower:
            self.lower.start()
        if self.gui:
            self.gui.run()
        if self.lower:
            self.lower.stop()
