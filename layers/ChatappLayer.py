from .BaseLayer import BaseLayer

class ChatAppLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.gui = None

    def set_gui(self, gui):
        self.gui = gui
        # 3개의 콜백을 모두 등록
        self.gui.set_send_callback(self.gui_send_handler)
        self.gui.set_mac_callback(self.gui_set_mac_handler)
        self.gui.set_ip_callback(self.gui_set_ip_handler)

    def gui_set_mac_handler(self, dst_mac_str: str):
        """GUI의 'Set MAC' 버튼 콜백"""
        if not self.lower:
            return False
        try:
            # L2 MAC 주소 파싱
            dst_mac = bytes.fromhex(dst_mac_str.replace(':', '').replace('-', ''))
            if len(dst_mac) != 6:
                return False

            # 하위 계층(IPLayer)의 set_dst_mac 호출
            self.lower.set_dst_mac(dst_mac)
            return True
        except Exception as e:
            print(f"[ChatApp] MAC 설정 오류: {e}")
            return False

    def gui_set_ip_handler(self, dst_ip_str: str):
        """GUI의 'Set IP' 버튼 콜백"""
        if not self.lower:
            return False
        try:
            # L3 IP 주소 파싱 (예: "1.2.3.4" -> b'\x01\x02\x03\x04')
            parts = dst_ip_str.split('.')
            if len(parts) != 4:
                raise ValueError("IP 주소는 4부분이어야 합니다.")
            dst_ip = b''
            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    raise ValueError("IP 주소 값은 0-255 사이여야 합니다.")
                dst_ip += num.to_bytes(1, 'big')

            # 하위 계층(IPLayer)의 set_dst_ip 호출
            self.lower.set_dst_ip(dst_ip)
            return True
        except Exception as e:
            print(f"[ChatApp] IP 설정 오류: {e}")
            return False

    def gui_send_handler(self, text: str):
        """
        GUI Send 콜백 핸들러 (이제 text만 받음)
        이전에 설정된 MAC/IP 주소를 사용합니다.
        """
        if not self.lower:
            return False
        try:
            # 4. 데이터 전송
            msg = f"[SEND] {text}".encode("utf-8")

            ok = self.lower.send(msg) # IPLayer.send() 호출

            if ok and self.gui:
                self.gui.display_message("SEND", text)
            return ok
        except Exception as e:
            print(f"[ChatApp] 전송 오류: {e}")
            if self.gui:
                self.gui.display_message("SYSTEM", f"[전송 오류] {e}")
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
            content = r[1].strip()
            self.gui.display_message("RCVD", content)
        else:
            self.gui.display_message("RCVD", s)
        return True

    def run(self):
        if self.lower:
            self.lower.start()
        if self.gui:
            self.gui.run()
        if self.lower:
            self.lower.stop()