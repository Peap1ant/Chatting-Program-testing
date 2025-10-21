# ------ Import module(if needs) ------
from layers import BaseLayer 
import threading
import sys
import time
from guilayer import GUI  
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


    def recv(self, data: bytes):
        if not self.gui:
            print("[경고] GUI가 연결되지 않아 수신 메시지를 표시할 수 없습니다.")
            return

        try:
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
        if self.gui:
            self.start()
            self.gui.run()
            self.stop() 
        else:
            print("GUI 인스턴스가 설정되지 않았습니다. set_gui()를 먼저 호출하세요.")
