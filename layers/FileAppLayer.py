from .BaseLayer import BaseLayer
import os
import struct
import threading
from .IPLayer import IPLayer

class FileAppLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.gui = None

        # [수정] 실행되는 main.py가 있는 위치(cwd) 기준 'files' 폴더 지정
        # (프로젝트 루트에 files 폴더가 생성됩니다)
        self.recv_dir = os.path.join(os.getcwd(), 'files')

        if not os.path.exists(self.recv_dir):
            try:
                os.makedirs(self.recv_dir)
                print(f"[FileApp] Created download directory: {self.recv_dir}")
            except Exception as e:
                print(f"[FileApp] Failed to create dir: {e}")

    def set_gui(self, gui):
        self.gui = gui

    def send(self, file_path):
        """파일 전송 (스레드 처리)"""
        if not self.lower:
            print("[FileApp] Error: Lower layer is missing!")
            return False

        if not os.path.exists(file_path):
            print(f"[FileApp] Error: File not found {file_path}")
            return False

        t = threading.Thread(target=self._send_thread, args=(file_path,))
        t.start()
        return True

    def _send_thread(self, file_path):
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            name_bytes = file_name.encode('utf-8')
            name_len = len(name_bytes)

            with open(file_path, 'rb') as f:
                content = f.read()

            # 헤더: [이름길이(4byte)][이름(가변)][내용]
            app_header = struct.pack('!I', name_len) + name_bytes
            data = app_header + content

            print(f'[FileApp] Sending "{file_name}" ({file_size} bytes)...')
            if self.gui:
                self.gui.set_status(f'Sending file: {file_name}...')

            # IPLayer로 전송
            self.lower.send(data, protocol=IPLayer.PROTOCOL_FILE)

            print(f'[FileApp] Sent "{file_name}" successfully.')
            if self.gui:
                self.gui.set_status('File sent successfully.')
                # 보낸 파일도 로그에 남기기 위해 콜백 호출
                if hasattr(self.gui, 'on_file_sent_msg'):
                    self.gui.on_file_sent_msg(file_path)

        except Exception as e:
            print(f'[FileApp] Send Exception: {e}')
            if self.gui:
                self.gui.set_status(f'File send error: {e}')

    def recv(self, data: bytes):
        """데이터 수신 및 파일 저장"""
        # [디버깅] 수신 시작 알림
        print(f"[FileApp] Received data packet ({len(data)} bytes). Processing...")

        try:
            # 1. 헤더 길이 확인
            if len(data) < 4:
                print("[FileApp] Error: Data too short to contain header.")
                return False

            # 2. 파일명 길이 파싱
            name_len = struct.unpack('!I', data[:4])[0]

            # 3. 전체 데이터 길이 검증
            if len(data) < 4 + name_len:
                print(f"[FileApp] Error: Data truncated. Expected name len {name_len}, but data left is {len(data)-4}.")
                return False

            # 4. 파일명 및 내용 추출
            file_name_raw = data[4 : 4 + name_len].decode('utf-8', errors='ignore')
            file_name = os.path.basename(file_name_raw) # 경로 조작 방지

            # 파일명이 비어있거나 이상한 경우 기본값 처리
            if not file_name or file_name.strip() == '':
                file_name = 'unknown_file.bin'

            content = data[4 + name_len :]

            # 5. 저장 경로 설정 (절대 경로)
            save_path = os.path.join(self.recv_dir, file_name)

            # [디버깅] 저장 위치 출력
            print(f"[FileApp] Attempting to save file to: {save_path}")

            # 6. 파일 쓰기
            with open(save_path, 'wb') as f:
                f.write(content)

            print(f'[FileApp] SUCCESS: Saved "{file_name}" ({len(content)} bytes).')

            # 7. GUI 알림
            if self.gui:
                if hasattr(self.gui, 'on_file_received_msg'):
                    # GUI에 절대 경로 전달
                    self.gui.on_file_received_msg(save_path)
                else:
                    self.gui.display_message('FILE_RCVD', f'{file_name} (saved)')
            return True

        except Exception as e:
            # 상세 에러 출력
            print(f'[FileApp] CRITICAL RECV ERROR: {e}')
            import traceback
            traceback.print_exc()
            return False