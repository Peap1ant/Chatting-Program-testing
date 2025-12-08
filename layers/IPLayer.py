from .BaseLayer import BaseLayer
import struct
import random
import time

class IPLayer(BaseLayer):
    # 프로토콜 상수
    PROTOCOL_CHAT = 1
    PROTOCOL_FILE = 2

    IP_BROADCAST = b'\xFF\xFF\xFF\xFF'

    # MTU: 1024로 유지 (안전값)
    MTU = 1450
    IP_HEADER_SIZE = 20

    def __init__(self):
        super().__init__()
        self.src_ip = b'\x00\x00\x00\x00'
        self.dst_ip = b'\x00\x00\x00\x00'
        self.upper_protocols = {}
        self.rx_buffer = {}

    def register_upper(self, protocol_id, layer):
        self.upper_protocols[protocol_id] = layer
        layer.set_lower(self)

    def set_src_ip(self, ip_bytes: bytes):
        if len(ip_bytes) == 4:
            self.src_ip = ip_bytes

    def set_dst_ip(self, ip_bytes: bytes):
        if len(ip_bytes) == 4:
            self.dst_ip = ip_bytes

    def set_dst_mac(self, mac: bytes):
        if self.lower and hasattr(self.lower, 'set_dst_mac'):
            self.lower.set_dst_mac(mac)

    def send(self, data: bytes, protocol=PROTOCOL_CHAT):
        if not self.lower:
            return False

        pkt_id = random.randint(0, 65535)
        total_size = len(data)
        offset = 0
        max_payload_size = self.MTU - self.IP_HEADER_SIZE

        print(f"[IP] Start Sending. Size: {total_size}, ID: {pkt_id}, Protocol: {protocol}")

        while offset < total_size:
            chunk_size = min(max_payload_size, total_size - offset)
            chunk = data[offset : offset + chunk_size]
            mf = 1 if (offset + chunk_size) < total_size else 0

            header = struct.pack('!4s4sBHIIB',
                                 self.src_ip,
                                 self.dst_ip,
                                 protocol,
                                 pkt_id,
                                 offset,
                                 len(chunk),
                                 mf)

            self.lower.send(header + chunk)
            offset += chunk_size

            # 동영상 파일 전송 시 시간이 꽤 걸릴 것입니다.
            time.sleep(0.005)

        print(f"[IP] Finish Sending ID: {pkt_id}")
        return True

    def recv(self, data: bytes):
        if len(data) < 20:
            return False

        header = data[:20]
        try:
            src_ip, dst_ip, proto, pkt_id, offset, length, mf = struct.unpack('!4s4sBHIIB', header)
        except:
            return False

        payload = data[20:]

        if dst_ip != self.src_ip and dst_ip != self.IP_BROADCAST:
            return False

        key = (src_ip, pkt_id)

        if key not in self.rx_buffer:
            self.rx_buffer[key] = {
                'fragments': [],
                'received_len': 0,
                'total_len': None,
                'last_ts': time.time()
            }

        entry = self.rx_buffer[key]

        # 중복 패킷 방지 (간단한 체크)
        # 현재 오프셋이 이미 리스트에 있다면 스킵
        # (완벽하진 않으나 기본적인 중복 수신 방지)
        for frag in entry['fragments']:
            if frag[0] == offset:
                return True

        entry['fragments'].append((offset, payload))
        entry['received_len'] += len(payload)

        if mf == 0:
            entry['total_len'] = offset + len(payload)
            print(f"[IP] Last Fragment Received for ID:{pkt_id}. Total Size should be: {entry['total_len']}")

        # [디버깅] 진행 상황 출력 (10번째 패킷마다)
        if len(entry['fragments']) % 10 == 0:
            total_str = str(entry['total_len']) if entry['total_len'] else "???"
            print(f"[IP] Reassembling ID:{pkt_id}.. Current: {entry['received_len']} / Total: {total_str}")

        # 재조립 완료 조건 검사
        if entry['total_len'] is not None and entry['received_len'] == entry['total_len']:
            print(f"[IP] Reassembly Complete! ID:{pkt_id}. Calling Upper Protocol: {proto}")

            entry['fragments'].sort(key=lambda x: x[0])
            reassembled_data = b''.join(f[1] for f in entry['fragments'])
            del self.rx_buffer[key]

            # 상위 계층 전달
            if proto in self.upper_protocols:
                return self.upper_protocols[proto].recv(reassembled_data)
            else:
                print(f"[IP] Error: No layer registered for protocol ID {proto}")
                print(f"     Registered protocols: {list(self.upper_protocols.keys())}")

        return True