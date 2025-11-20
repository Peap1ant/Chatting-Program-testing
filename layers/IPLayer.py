from .BaseLayer import BaseLayer
import struct
import random

class IPLayer(BaseLayer):
    # 프로토콜 상수
    PROTOCOL_CHAT = 1
    PROTOCOL_FILE = 2

    IP_BROADCAST = b'\xFF\xFF\xFF\xFF'

    # 단편화 설정
    MTU = 1450 # Ethernet MTU(1500) - IP Header 여유분

    def __init__(self):
        super().__init__()
        self.src_ip = b'\x00\x00\x00\x00'
        self.dst_ip = b'\x00\x00\x00\x00'
        self.upper_protocols = {} # { protocol_id : layer_object }

        # 재조립 버퍼: { (src_ip, pkt_id): {'fragments': [], 'total_len': None} }
        self.rx_buffer = {}

    def register_upper(self, protocol_id, layer):
        """상위 계층 등록 (프로토콜 ID 별로 구분)"""
        self.upper_protocols[protocol_id] = layer
        layer.set_lower(self)

    def set_src_ip(self, ip_bytes: bytes):
        if len(ip_bytes) == 4:
            self.src_ip = ip_bytes

    def set_dst_ip(self, ip_bytes: bytes):
        if len(ip_bytes) == 4:
            self.dst_ip = ip_bytes

    def set_dst_mac(self, mac: bytes):
        # ARP 계층으로 바이패스
        if self.lower and hasattr(self.lower, 'set_dst_mac'):
            self.lower.set_dst_mac(mac)

    def send(self, data: bytes, protocol=PROTOCOL_CHAT):
        """
        데이터를 MTU 단위로 쪼개서(Fragmentation) 전송
        """
        if not self.lower:
            return False

        # 패킷 식별자 (0~65535)
        pkt_id = random.randint(0, 65535)
        total_size = len(data)
        offset = 0

        # 단편화 루프
        while offset < total_size:
            # 이번에 보낼 데이터 크기 계산
            chunk_size = min(self.MTU, total_size - offset)
            chunk = data[offset : offset + chunk_size]

            # More Fragments (MF) 플래그: 뒤에 더 보낼 게 있으면 1, 없으면 0
            mf = 1 if (offset + chunk_size) < total_size else 0

            # IP 헤더 생성 (20 바이트)
            # Src(4) | Dst(4) | Proto(1) | ID(2) | Offset(4) | Len(4) | MF(1)
            header = struct.pack('!4s4sBHIIB',
                                 self.src_ip,
                                 self.dst_ip,
                                 protocol,
                                 pkt_id,
                                 offset,
                                 len(chunk),
                                 mf)

            packet = header + chunk
            self.lower.send(packet)

            offset += chunk_size

        return True

    def recv(self, data: bytes):
        if len(data) < 20:
            return False

        # 헤더 파싱
        header = data[:20]
        src_ip, dst_ip, proto, pkt_id, offset, length, mf = struct.unpack('!4s4sBHIIB', header)
        payload = data[20:]

        # IP 필터링
        if dst_ip != self.src_ip and dst_ip != self.IP_BROADCAST:
            return False

        # 재조립 키
        key = (src_ip, pkt_id)

        if key not in self.rx_buffer:
            self.rx_buffer[key] = {'fragments': [], 'received_len': 0, 'is_complete': False}

        entry = self.rx_buffer[key]

        # 조각 저장 (offset, data)
        entry['fragments'].append((offset, payload))
        entry['received_len'] += len(payload)

        # 마지막 조각인지 확인
        if mf == 0:
            entry['total_len'] = offset + len(payload)
            entry['is_complete'] = True

        # 모든 조각이 다 왔는지 확인 (간이 검사: 수신된 길이 == 전체 길이)
        if entry.get('is_complete') and entry['received_len'] == entry['total_len']:
            # 재조립 수행
            entry['fragments'].sort(key=lambda x: x[0]) # offset 순 정렬
            reassembled_data = b''.join(f[1] for f in entry['fragments'])

            # 버퍼 정리
            del self.rx_buffer[key]

            # 상위 계층으로 전달
            if proto in self.upper_protocols:
                return self.upper_protocols[proto].recv(reassembled_data)

        return True