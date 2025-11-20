from .BaseLayer import BaseLayer
import os
import struct
import threading
from .IPLayer import IPLayer

class FileAppLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.gui = None
        self.recv_dir = './files'
        if not os.path.exists(self.recv_dir):
            os.makedirs(self.recv_dir)

    def set_gui(self, gui):
        self.gui = gui

    def send(self, file_path):
        """
        파일 전송 (스레드 처리)
        """
        if not self.lower:
            return False

        # 별도 스레드에서 전송 (GUI 멈춤 방지)
        t = threading.Thread(target=self._send_thread, args=(file_path,))
        t.start()
        return True

    def _send_thread(self, file_path):
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            name_bytes = file_name.encode('utf-8')
            name_len = len(name_bytes)

            # 어플리케이션 헤더: [파일명길이(4)][파일명(...)][파일내용]
            # 대용량 파일도 메모리에 올려서 IP로 보냅니다 (IPLayer가 단편화 처리)

            with open(file_path, 'rb') as f:
                content = f.read()

            # 헤더 생성
            app_header = struct.pack('!I', name_len) + name_bytes
            data = app_header + content

            print(f'[FileApp] Sending {file_name} ({file_size} bytes)...')
            if self.gui:
                self.gui.set_status(f'Sending file: {file_name}...')

            # IP 계층의 send 호출 시 프로토콜 타입을 FILE로 지정
            self.lower.send(data, protocol=IPLayer.PROTOCOL_FILE)

            print('[FileApp] Send complete.')
            if self.gui:
                self.gui.display_message('FILE_SENT', f'{file_name} ({file_size} B)')
                self.gui.set_status('File sent successfully.')

        except Exception as e:
            print(f'[FileApp] Error: {e}')
            if self.gui:
                self.gui.set_status(f'File send error: {e}')

    def recv(self, data: bytes):
        try:
            # 헤더 파싱: [파일명길이(4)]
            name_len = struct.unpack('!I', data[:4])[0]

            # 파일명 추출
            file_name = data[4 : 4 + name_len].decode('utf-8')

            # 파일 내용 추출
            content = data[4 + name_len :]

            save_path = os.path.join(self.recv_dir, file_name)

            # 파일 쓰기
            with open(save_path, 'wb') as f:
                f.write(content)

            print(f'[FileApp] Received {file_name} saved to {save_path}')

            if self.gui:
                self.gui.display_message('FILE_RCVD', f'{file_name} (saved)')
            return True

        except Exception as e:
            print(f'[FileApp] Recv error: {e}')
            return False