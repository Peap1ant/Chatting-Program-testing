from scapy.all import sniff, sendp, Ether
import threading
from .BaseLayer import BaseLayer

class PhysicalLayer(BaseLayer):
    def __init__(self, iface: str):
        super().__init__()
        self.iface = iface
        self._rx_thread = None
        self.running = False

    def send(self, frame: bytes):
        sendp(frame, iface=self.iface, verbose=False)

    def start(self, promisc=True, bpf_filter=None):
        self.running = True
        def _loop():
            sniff(
                iface=self.iface,
                store=False,
                promisc=promisc,
                lfilter=lambda p: Ether in p and getattr(p, "type", None) == 0xFFFF,
                prn=lambda pkt: self._forward(bytes(pkt)),
                stop_filter=lambda pkt: not self.running
            )
        self._rx_thread = threading.Thread(target=_loop, daemon=True)
        self._rx_thread.start()

    def _forward(self, raw_bytes: bytes):
        if self.upper:
            self.upper.recv(raw_bytes)

    def stop(self):
        self.running = False
