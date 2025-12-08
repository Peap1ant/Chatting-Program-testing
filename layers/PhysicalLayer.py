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

    def set_iface(self, iface: str):
        if self.iface == iface and self._t and self._t.is_alive():
            print(f'[PHY] Interface already set to "{iface}" and running.')
            return

        print(f'[PHY] Interface changing from "{self.iface}" to "{iface}"...')

        # self.running은 BaseLayer의 start()가 호출되어야 True가 됩니다.
        if self.running:
            self.stop()  # 기존 스니퍼 중지 (콘솔 로그 생성)

        self.iface = iface

        if self.running:
            self.start() # 새 인터페이스로 스니퍼 시작 (콘솔 로그 생성)
            print(f'[PHY] Interface change complete for "{iface}".')
        else:
            print(f'[PHY] Interface set to "{iface}". (Will start when .run() is called)')


    def send(self, frame: bytes):
        if not self.iface:
            print('TX aborted: iface not set')
            return False
        try:
            print(f'TX iface={self.iface} len={len(frame)}')
            sendp(frame, iface=self.iface, verbose=False)
            return True
        except Exception as e:
            print(f'TX error: {e}')
            return False

    def _sniff_loop(self):
        print(f'[PHY] sniffer thread start on iface={self.iface}')
        while not self._stop.is_set():
            try:
                if not self.iface:
                    print('[PHY] Sniff loop paused: iface not set.')
                    time.sleep(2)
                    continue

                sniff(
                    iface=self.iface,
                    store=False,
                    prn=self._on_pkt,
                    timeout=10
                )
            except Exception as e:
                # 인터페이스가 갑자기 사라지거나 할 때 오류 발생 가능
                print(f'[PHY] sniff error: {e}')
                time.sleep(1)

        print('[PHY] sniffer thread exit')

    def _on_pkt(self, pkt):
        raw = getattr(pkt, 'original', None)
        if raw is None:
            try:
                raw = bytes(pkt)
            except Exception:
                return
        print(f'[PHY] RX {len(raw)} bytes')
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
            self._t.join(timeout=12)
            self._t = None