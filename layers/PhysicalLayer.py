from scapy.all import sniff, sendp
import threading
from layers.BaseLayer import BaseLayer

class PhysicalLayer(BaseLayer):
    def __init__(self, iface: str):
        super().__init__()
        self.iface = iface
        self._stop_evt = threading.Event()
        self._rx_thread = None

    def send(self, raw_bytes: bytes):
        if not raw_bytes:
            return False
        sendp(raw_bytes, iface=self.iface, verbose=False)
        return True

    def start(self):
        if self.running:
            return
        self.running = True
        def _loop():
            sniff(
                iface=self.iface,
                store=False,
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
