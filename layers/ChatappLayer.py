# ------ Import module(if needs) ------

from layers.BaseLayer import BaseLayer
import threading
from layers.GUILayer import GUI

# ------ Main code ------
class ChatAppLayer(BaseLayer):
    
    def __init__(self, nickname="User"):
        super().__init__()
        self.nickname = nickname
        self.gui: GUI = None         
        self.stop_event = threading.Event()
        
    def set_gui(self, gui_instance: GUI):

        self.gui = gui_instance
        self.gui.set_send_callback(self.gui_send_handler)
        self.gui.set_my_mac(self.nickname) 

    def gui_send_handler(self, dst_mac_str: str, message: str) -> bool:
        if not message.strip():
            return False

        full_message = f"[{self.nickname}]: {message}"
        encoded_data = full_message.encode('utf-8')

        try:
            dst_mac_bytes = bytes.fromhex(dst_mac_str.replace(':', ''))
            if len(dst_mac_bytes) != 6:
                raise ValueError("MAC 주소 길이가 잘못되었습니다.")
        except ValueError:
            self.gui.display_message("SYSTEM", f"[오류] 잘못된 MAC 주소 형식입니다: {dst_mac_str}")
            return False

        if self.lower:
            self.lower.set_dst_mac(dst_mac_bytes) 
            self.lower.send(encoded_data)
            self.gui.display_message("나", message) 
            return True
        else:
            self.gui.display_message("SYSTEM", "[경고] 하위 계층이 설정되지 않았습니다. 전송 실패.")
            return False


    def recv(self, data):
        try:
            msg = data.decode(errors='ignore')
            if not msg:
                return
            self.gui.display_message("Peer", msg)
        except Exception:
            if not hasattr(self, "_last_error_time"):
                self._last_error_time = 0
            import time
            now = time.time()
            if now - self._last_error_time > 3:
                if self.gui:
                    self.gui.display_message("SYSTEM", "오류: 수신된 데이터를 디코딩할 수 없습니다.")
                self._last_error_time = now


    def run(self):
        if self.gui:
            self.start()
            self.gui.run()
            self.stop() 
        else:
            print("GUI 인스턴스가 설정되지 않았습니다. set_gui()를 먼저 호출하세요.")