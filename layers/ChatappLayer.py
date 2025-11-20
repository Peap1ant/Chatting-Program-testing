from .BaseLayer import BaseLayer
from .IPLayer import IPLayer # 상수 사용을 위해 import

class ChatAppLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.gui = None

    def set_gui(self, gui):
        self.gui = gui
        self.gui.set_send_callback(self.gui_send_handler)
        self.gui.set_mac_callback(self.gui_set_mac_handler)
        self.gui.set_ip_callback(self.gui_set_ip_handler)

    # ... (set_mac_handler, set_ip_handler 등 기존 코드는 동일) ...
    def gui_set_mac_handler(self, dst_mac_str: str):
        if self.lower:
            try:
                dst_mac = bytes.fromhex(dst_mac_str.replace(':', '').replace('-', ''))
                self.lower.set_dst_mac(dst_mac)
                return True
            except: return False
        return False

    def gui_set_ip_handler(self, dst_ip_str: str):
        if self.lower:
            try:
                parts = dst_ip_str.split('.')
                dst_ip = b''.join(int(p).to_bytes(1,'big') for p in parts)
                self.lower.set_dst_ip(dst_ip)
                return True
            except: return False
        return False

    def gui_send_handler(self, text: str):
        """수정된 send 호출"""
        if not self.lower:
            return False
        try:
            msg = f'[SEND] {text}'.encode('utf-8')
            # 프로토콜 타입을 CHAT으로 명시
            ok = self.lower.send(msg, protocol=IPLayer.PROTOCOL_CHAT)

            if ok and self.gui:
                self.gui.display_message('SEND', text)
            return ok
        except Exception as e:
            print(f'[ChatApp] 전송 오류: {e}')
            return False

    def recv(self, data: bytes):
        # ... (기존과 동일) ...
        if not self.gui: return False
        try: s = data.decode('utf-8')
        except: s = '[Decode Error]'
        if s.startswith('[') and ']' in s:
            content = s.split(']', 1)[1].strip()
            self.gui.display_message('RCVD', content)
        else:
            self.gui.display_message('RCVD', s)
        return True