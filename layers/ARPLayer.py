# layers/ARPLayer.py
from .BaseLayer import BaseLayer
from scapy.all import Ether, ARP, sendp
import threading


class ARPLayer(BaseLayer):
    """
    ARP / Proxy ARP / Gratuitous ARP 통합 버전
    ────────────────────────────────
    - 일반 ARP: 요청, 응답, 캐시 학습
    - Proxy ARP: 다른 IP에 대한 요청에 대리응답
    - Gratuitous ARP: 자신의 IP–MAC을 네트워크에 알림
    """
    def __init__(self):
        super().__init__()
        self.src_ip = None
        self.src_mac = None
        self.arp_table = {}         # 일반 ARP 캐시 {IP(bytes): MAC(bytes)}
        self.proxy_map = {}         # Proxy ARP {Target_IP(bytes): MAC(bytes)}
        self.lock = threading.Lock()

    # ====설정 관련====
    def set_src_info(self, ip_bytes: bytes, mac_bytes: bytes):
        """내 IP와 MAC 등록"""
        self.src_ip = ip_bytes
        self.src_mac = mac_bytes
        print(f"[ARP] 내 정보 등록: IP={self._ip_str(ip_bytes)}, MAC={self._mac_str(mac_bytes)}")

    def add_proxy_entry(self, target_ip: bytes, owner_mac: bytes):
        """Proxy ARP: 특정 IP에 대해 내가 대신 응답"""
        with self.lock:
            self.proxy_map[target_ip] = owner_mac
        print(f"[ARP] Proxy 엔트리 추가: {self._ip_str(target_ip)} → {self._mac_str(owner_mac)}")

    # ====일반 ARP (요청 / 응답 / 캐시)====
    def lookup(self, ip_bytes: bytes):
        """ARP 테이블 조회 (없으면 ARP Request 보냄)"""
        with self.lock:
            mac = self.arp_table.get(ip_bytes)
        if mac:
            return mac
        print(f"[ARP] 캐시 없음 → {self._ip_str(ip_bytes)} 요청 시도")
        self.request(ip_bytes)
        return None

    def request(self, target_ip: bytes):
        """ARP Request 전송"""
        if not (self.src_ip and self.src_mac):
            print("[ARP] 요청 실패: 소스 정보 없음")
            return False
        iface = self._get_iface()
        if not iface:
            print("[ARP] 요청 실패: iface 없음")
            return False

        pkt = Ether(dst="ff:ff:ff:ff:ff:ff", src=self._mac_str(self.src_mac)) / \
              ARP(op=1,
                  hwsrc=self._mac_str(self.src_mac),
                  psrc=self._ip_str(self.src_ip),
                  pdst=self._ip_str(target_ip))
        sendp(pkt, iface=iface, verbose=False)
        print(f"[ARP] Request 송신: who-has {self._ip_str(target_ip)}?")
        return True

    def reply(self, dst_ip, dst_mac, proxy_ip=None, proxy_mac=None):
        """ARP Reply 전송 (일반 응답 또는 Proxy 응답)"""
        iface = self._get_iface()
        if not iface:
            print("[ARP] Reply 실패: iface 없음")
            return False

        psrc_ip = proxy_ip or self.src_ip
        src_mac = proxy_mac or self.src_mac

        pkt = Ether(dst=self._mac_str(dst_mac), src=self._mac_str(src_mac)) / \
              ARP(op=2,
                  hwsrc=self._mac_str(src_mac),
                  psrc=self._ip_str(psrc_ip),
                  hwdst=self._mac_str(dst_mac),
                  pdst=self._ip_str(dst_ip))
        sendp(pkt, iface=iface, verbose=False)
        print(f"[ARP] Reply 송신: {self._ip_str(psrc_ip)} is-at {self._mac_str(src_mac)}")
        return True

    # ====Gratuitous ARP====
    def send_gratuitous(self):
        """자신의 IP–MAC을 네트워크에 알림"""
        if not (self.src_ip and self.src_mac):
            print("[ARP] Gratuitous 실패: src 정보 없음")
            return False
        iface = self._get_iface()
        if not iface:
            print("[ARP] Gratuitous 실패: iface 없음")
            return False

        pkt = Ether(dst="ff:ff:ff:ff:ff:ff", src=self._mac_str(self.src_mac)) / \
              ARP(op=2,
                  hwsrc=self._mac_str(self.src_mac),
                  psrc=self._ip_str(self.src_ip),
                  hwdst="00:00:00:00:00:00",
                  pdst=self._ip_str(self.src_ip))
        sendp(pkt, iface=iface, verbose=False)
        print(f"[ARP] Gratuitous ARP 송신: {self._ip_str(self.src_ip)} is-at {self._mac_str(self.src_mac)}")
        return True

    # ====수신 처리 (ARP Request / Reply)====
    def recv(self, data: bytes):
        try:
            pkt = ARP(data)
        except Exception:
            return False

        op = pkt.op
        sender_ip = tuple(int(x) for x in pkt.psrc.split('.'))
        sender_mac = bytes.fromhex(pkt.hwsrc.replace(':', ''))
        target_ip = tuple(int(x) for x in pkt.pdst.split('.'))

        # (1) ARP Reply-> 캐시 저장
        if op == 2:
            with self.lock:
                self.arp_table[sender_ip] = sender_mac
            print(f"[ARP] 캐시 학습: {pkt.psrc} → {pkt.hwsrc}")
            return True

        # (2) ARP Request
        elif op == 1:
            print(f"[ARP] Request 수신: who has {pkt.pdst}? tell {pkt.psrc}")

            # 일반 ARP 응답 (내 IP 요청)
            if target_ip == tuple(self.src_ip):
                self.reply(sender_ip, sender_mac)
                return True

            # Proxy ARP 응답 (등록된 IP 요청)
            if target_ip in self.proxy_map:
                proxy_mac = self.proxy_map[target_ip]
                self.reply(sender_ip, sender_mac,
                           proxy_ip=target_ip, proxy_mac=proxy_mac)
                print(f"[ARP] Proxy ARP 응답: {pkt.pdst} 대신 응답함")
                return True

        return False

    # ====내부 유틸 함수====
    def _get_iface(self):
        """하위 계층(Ethernet→Physical)에서 iface 이름 가져오기"""
        if hasattr(self.lower, "iface"):
            return self.lower.iface
        phy = getattr(self.lower, "lower", None)
        return getattr(phy, "iface", None)

    @staticmethod
    def _ip_str(ip: bytes):
        return '.'.join(str(b) for b in ip)

    @staticmethod
    def _mac_str(mac: bytes):
        return ':'.join(f"{b:02x}" for b in mac)
