from .BaseLayer import BaseLayer

class EthernetLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.src_mac = bytearray(6)
        self.dst_mac = bytearray(6)

    def set_src_mac(self, mac: bytes):
        self.src_mac[:] = mac

    def set_dst_mac(self, mac: bytes):
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
        if et != b'\xFF\xFF':
            return False
        bcast = b'\xFF' * 6
        if not (dst == bcast or dst == bytes(self.src_mac)):
            return False
        payload = data[14:].rstrip(b'\x00')
        if not payload:
            return False
        if self.upper:
            self.upper.recv(payload)
            return True
        return False
