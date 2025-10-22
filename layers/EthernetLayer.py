from layers.BaseLayer import BaseLayer
from scapy.all import Ether, Raw

CHAT_ETHER_TYPE = 0x88B5

class EthernetLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.src_mac = bytearray(6)
        self.dst_mac = bytearray(6)

    def set_src_mac(self, mac: bytes):
        self.src_mac[:] = mac

    def set_dst_mac(self, mac: bytes):
        self.dst_mac[:] = mac

    def send(self, payload: bytes):
        if not self.lower:
            return False
        if len(self.src_mac) != 6 or len(self.dst_mac) != 6:
            return False
        src = self.src_mac.hex(':')
        dst = self.dst_mac.hex(':')
        frame = Ether(src=src, dst=dst, type=CHAT_ETHER_TYPE) / Raw(payload)
        raw = bytes(frame)
        return self.lower.send(raw)

    def recv(self, data: bytes):
        if len(data) < 14:
            return False
        dst = data[0:6]
        bcast = b'\xff\xff\xff\xff\xff\xff'
        if not (dst == self.src_mac or dst == bcast):
            return False
        etype = int.from_bytes(data[12:14], 'big')
        if etype != CHAT_ETHER_TYPE:
            return False
        payload = data[14:]
        if self.upper:
            self.upper.recv(payload)
            return True
        return False
