# ------ Import module(if needs) ------

from .BaseLayer import BaseLayer

# ------ Main code ------

class EthernetLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.src_mac = bytearray(6)
        self.dst_mac = bytearray(6)

    def set_src_mac(self, mac):
        self.src_mac[:] = mac

    def set_dst_mac(self, mac):
        self.dst_mac[:] = mac

    def send(self, data: bytes):
        frame = bytearray(len(data) + 14)
        frame[0:6] = self.dst_mac
        frame[6:12] = self.src_mac
        frame[12:14] = b'\xFF\xFF'
        frame[14:] = data
        if self.lower:
            self.lower.send(bytes(frame))
            return True
        return False

    def recv(self, data: bytes):
        if len(data) < 14:
            return False

        frame_dst_mac = data[0:6]
        ether_type = data[12:14]
        broadcast_address = b'\xFF\xFF\xFF\xFF\xFF\xFF'

        is_mine = (frame_dst_mac == self.src_mac)
        is_broadcast = (frame_dst_mac == broadcast_address)
        if not is_mine and not is_broadcast:
            return False

        if ether_type != b'\xFF\xFF':
            return False

        payload = data[14:]
        payload = payload.rstrip(b'\x00')

        if self.upper:
            self.upper.recv(payload)
            return True
        return False


