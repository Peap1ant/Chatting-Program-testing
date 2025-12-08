from .BaseLayer import BaseLayer
from .IPLayer import IPLayer
import json
import uuid
import os
import hashlib
from datetime import datetime

class ChatAppLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.gui = None
        self.logs_dir = './logs'
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        self.current_peer_mac = None
        self.current_peer_ip = None

    def set_gui(self, gui):
        self.gui = gui
        self.gui.set_send_callback(self.gui_send_handler)
        self.gui.set_mac_callback(self.gui_set_mac_handler)
        self.gui.set_ip_callback(self.gui_set_ip_handler)
        self.gui.set_delete_msg_callback(self.gui_delete_msg_handler)

    def _get_log_filepath(self, mac_str, ip_str):
        if not mac_str or not ip_str: return None
        raw_str = f"{mac_str} - {ip_str}"
        fname = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()
        return os.path.join(self.logs_dir, f"{fname}.json")

    def _read_log_file(self, fpath):
        if not os.path.exists(fpath): return []
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content: return []
                return json.loads(content)
        except: return []

    def _write_log_file(self, fpath, data_list):
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Log] Write Error: {e}")

    def _append_log(self, msg_data: dict):
        fpath = self._get_log_filepath(self.current_peer_mac, self.current_peer_ip)
        if not fpath: return
        current_logs = self._read_log_file(fpath)
        current_logs.append(msg_data)
        self._write_log_file(fpath, current_logs)

    def _delete_log_by_id(self, msg_id):
        fpath = self._get_log_filepath(self.current_peer_mac, self.current_peer_ip)
        if not fpath: return
        current_logs = self._read_log_file(fpath)
        new_logs = [msg for msg in current_logs if msg.get('id') != msg_id]
        if len(new_logs) != len(current_logs):
            self._write_log_file(fpath, new_logs)

    def _load_history(self):
        if not self.gui: return
        self.gui.clear_chat()

        fpath = self._get_log_filepath(self.current_peer_mac, self.current_peer_ip)
        if not fpath: return

        logs = self._read_log_file(fpath)
        for data in logs:
            sender = data.get('sender', 'Unknown')
            msg_id = data.get('id')
            msg_type = data.get('type', 'MSG') # MSG, FILE, IMG

            if msg_type == 'IMG':
                path = data.get('path', '')
                self.gui.display_image(sender, path, msg_id)
            elif msg_type == 'FILE':
                path = data.get('path', '')
                fname = os.path.basename(path)
                text = f"File: {fname} (Saved)"
                self.gui.display_message(sender, text, msg_id)
            else:
                text = data.get('text', '')
                self.gui.display_message(sender, text, msg_id)

    # --- [추가] 외부(FileAppLayer) 이벤트 로그 기록 메서드 ---
    def log_file_event(self, sender, file_rel_path, is_image=False):
        """GUI가 파일 송수신을 감지했을 때 호출"""
        msg_id = str(uuid.uuid4())

        msg_type = 'IMG' if is_image else 'FILE'

        log_data = {
            "id": msg_id,
            "sender": sender,
            "type": msg_type,
            "path": file_rel_path, # 상대 경로 저장
            "timestamp": datetime.now().isoformat()
        }

        self._append_log(log_data)

        # 화면에도 즉시 표시
        if self.gui:
            if is_image:
                self.gui.display_image(sender, file_rel_path, msg_id)
            else:
                fname = os.path.basename(file_rel_path)
                self.gui.display_message(sender, f"File: {fname} (Saved)", msg_id)

    # --- Handlers ---
    def gui_set_mac_handler(self, dst_mac_str: str):
        if self.lower:
            try:
                dst_mac = bytes.fromhex(dst_mac_str.replace(':', '').replace('-', ''))
                self.lower.set_dst_mac(dst_mac)
                self.current_peer_mac = dst_mac_str
                if self.current_peer_ip: self._load_history()
                return True
            except: return False
        return False

    def gui_set_ip_handler(self, dst_ip_str: str):
        if self.lower:
            try:
                parts = dst_ip_str.split('.')
                dst_ip = b''.join(int(p).to_bytes(1,'big') for p in parts)
                self.lower.set_dst_ip(dst_ip)
                self.current_peer_ip = dst_ip_str
                if self.current_peer_mac: self._load_history()
                return True
            except: return False
        return False

    def gui_send_handler(self, text: str):
        if not self.lower: return False

        msg_id = str(uuid.uuid4())
        packet_data = { "type": "MSG", "id": msg_id, "content": text }

        log_data = {
            "id": msg_id,
            "sender": "ME",
            "type": "MSG",
            "text": text,
            "timestamp": datetime.now().isoformat()
        }

        try:
            payload = json.dumps(packet_data).encode('utf-8')
            ok = self.lower.send(payload, protocol=IPLayer.PROTOCOL_CHAT)
            if ok and self.gui:
                self._append_log(log_data)
                self.gui.display_message('SEND', text, msg_id)
            return ok
        except Exception as e:
            print(f'[ChatApp] Send Error: {e}')
            return False

    def gui_delete_msg_handler(self, msg_id):
        if not self.lower: return

        packet_data = { "type": "DEL", "target_id": msg_id }
        try:
            payload = json.dumps(packet_data).encode('utf-8')
            self.lower.send(payload, protocol=IPLayer.PROTOCOL_CHAT)
        except Exception as e:
            print(f"[ChatApp] Failed to send delete req: {e}")
            return

        self._delete_log_by_id(msg_id)
        if self.gui:
            self.gui.remove_message_ui(msg_id)

    def recv(self, data: bytes):
        if not self.gui: return False
        try:
            decoded = data.decode('utf-8')
            if not decoded.strip().startswith('{'):
                self.gui.display_message('RCVD', decoded) # 구형 호환
                return True

            packet = json.loads(decoded)
            ptype = packet.get('type')

            if ptype == 'MSG':
                msg_id = packet.get('id')
                content = packet.get('content')
                log_data = {
                    "id": msg_id,
                    "sender": "PEER",
                    "type": "MSG",
                    "text": content,
                    "timestamp": datetime.now().isoformat()
                }
                self._append_log(log_data)
                self.gui.display_message('RCVD', content, msg_id)

            elif ptype == 'DEL':
                target_id = packet.get('target_id')
                self._delete_log_by_id(target_id)
                self.gui.remove_message_ui(target_id)

            return True
        except Exception as e:
            print(f'[ChatApp] Recv Error: {e}')
            return False