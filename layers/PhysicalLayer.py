from scapy.all import AsyncSniffer
from .BaseLayer import BaseLayer

class PhysicalLayer(BaseLayer):
    def __init__(self, iface: str):
        super().__init__()
        self.iface = iface
        self.sniffer = None

    def send(self, frame: bytes):
        from scapy.all import sendp
        if not self.iface:
            return False
        sendp(frame, iface=self.iface, verbose=False)
        return True

    def start(self):
        if self.sniffer:
            return
        def _prn(pkt):
            raw = getattr(pkt, "original", None)
            if raw is None:
                try:
                    raw = bytes(pkt)
                except Exception:
                    return
            if self.upper:
                self.upper.recv(raw)
        self.sniffer = AsyncSniffer(
            iface=self.iface,
            store=False,
            promisc=True,
            prn=_prn
        )
        self.sniffer.start()

    def stop(self):
        if self.sniffer:
            self.sniffer.stop()
            self.sniffer = None
