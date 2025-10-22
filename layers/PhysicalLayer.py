import threading
import time
from scapy.all import sniff, sendp
from .BaseLayer import BaseLayer

class PhysicalLayer(BaseLayer):
    def __init__(self, iface: str):
        super().__init__()
        self.iface = iface
        self._t = None
        self._stop = threading.Event()

    def send(self, frame: bytes):
        if not self.iface:
            print("TX aborted: iface not set")
            return False
        try:
            print(f"TX iface={self.iface} len={len(frame)}")
            sendp(frame, iface=self.iface, verbose=False)
            return True
        except Exception as e:
            print(f"TX error: {e}")
            return False

    def _sniff_loop(self):
        print(f"[PHY] sniffer thread start on iface={self.iface}")
        while not self._stop.is_set():
            try:
                sniff(
                    iface=self.iface,
                    store=False,
                    prn=self._on_pkt,
                    timeout=2
                )
            except Exception as e:
                print(f"[PHY] sniff error: {e}")
                time.sleep(1)

        print("[PHY] sniffer thread exit")

    def _on_pkt(self, pkt):
        raw = getattr(pkt, "original", None)
        if raw is None:
            try:
                raw = bytes(pkt)
            except Exception:
                return
        print(f"[PHY] RX {len(raw)} bytes")
        if self.upper:
            self.upper.recv(raw)

    def start(self):
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._sniff_loop, daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=3)
            self._t = None
