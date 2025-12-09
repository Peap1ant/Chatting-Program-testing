from .BaseLayer import BaseLayer

class EthernetLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.src_mac = bytearray(6)
        self.dst_mac = bytearray(6)

    def set_src_mac(self, mac: bytes):
        mac_str = ':'.join(f'{b:02x}' for b in mac)
        print(f'[ETH] Source MAC set to: {mac_str}')
        self.src_mac[:] = mac

    def set_dst_mac(self, mac: bytes):
        mac_str = ':'.join(f'{b:02x}' for b in mac)
        print(f'[ETH] Destination MAC set to: {mac_str}')
        self.dst_mac[:] = mac

    def send(self, data: bytes):
        if not self.lower:
            return False
        ether_type = b'\xFF\xFF'
        header = bytes(self.dst_mac) + bytes(self.src_mac) + ether_type
        payload = data
        if len(payload) < 46:
            payload = payload + b'\x00' * (46 - len(payload))
        frame = header + payload
        return self.lower.send(frame)

    def recv(self, data: bytes):
        if len(data) < 14:
            return False
        dst = data[0:6]
        src = data[6:12]
        et = data[12:14]

        # [수정] 0xFFFF(채팅) 외에 0x0806(ARP)도 허용
        if et != b'\xFF\xFF' and et != b'\x08\x06':
            return False

        bcast = b'\xFF' * 6
        if not (dst == bcast or dst == bytes(self.src_mac)):
            return False

        # [수정] ARP 패킷은 0x00을 제거하면 안 됨 (IP 주소 끝자리가 0일 수 있음)
        # 채팅 패킷(0xFFFF)만 패딩 제거 수행
        if et == b'\x08\x06':
            payload = data[14:]
        else:
            payload = data[14:].rstrip(b'\x00')

        if not payload:
            return False

        if self.upper:
            self.upper.recv(payload)
            return True
        return False