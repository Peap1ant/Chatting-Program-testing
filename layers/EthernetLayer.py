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

        # ARP(0x0806)와 IP/Chat(0xFFFF) 모두 허용
        if et != b'\xFF\xFF' and et != b'\x08\x06':
            return False

        bcast = b'\xFF' * 6
        if not (dst == bcast or dst == bytes(self.src_mac)):
            return False

        # [수정] rstrip(b'\x00')을 삭제하여 바이너리 데이터 손상 방지
        # 뒤에 붙은 패딩(0x00)은 상위 계층(IPLayer)에서 길이 정보를 보고 잘라내야 함
        payload = data[14:]

        if not payload:
            return False

        if self.upper:
            self.upper.recv(payload)
            return True
        return False