from .BaseLayer import BaseLayer
from scapy.all import Ether, ARP, sendp
import threading

class ARPLayer(BaseLayer):
    def __init__(self):
        super().__init__()
        self.src_ip = None
        self.src_mac = None
        self.arp_table = {}
        self.proxy_map = {}
        self.lock = threading.Lock()

        # ==== [추가됨] Pass-through 메소드 (IPLayer의 요청을 EthernetLayer로 전달) ====
    def set_dst_mac(self, mac: bytes):
        """IPLayer에서 호출한 MAC 설정을 EthernetLayer로 전달"""
        if self.lower and hasattr(self.lower, 'set_dst_mac'):
            self.lower.set_dst_mac(mac)
        else:
            print('[ARP] 경고: 하위 계층에 set_dst_mac이 없습니다.')

    def send(self, data: bytes):
        """IPLayer에서 내려온 채팅 패킷을 그대로 EthernetLayer로 전달"""
        if self.lower:
            return self.lower.send(data)
        return False
    # =========================================================================

    # ==== 설정 관련 (기존 동일) ================================================
    def set_src_info(self, ip_bytes: bytes, mac_bytes: bytes):
        self.src_ip = ip_bytes
        self.src_mac = mac_bytes
        print(f'[ARP] 내 정보 등록: IP={self._ip_str(ip_bytes)}, MAC={self._mac_str(mac_bytes)}')

    def add_proxy_entry(self, target_ip: bytes, owner_mac: bytes):
        with self.lock:
            self.proxy_map[target_ip] = owner_mac
        print(f'[ARP] Proxy 엔트리 추가: {self._ip_str(target_ip)} -> {self._mac_str(owner_mac)}')

    # ==== 일반 ARP (기존 동일) =================================================
    def lookup(self, ip_bytes: bytes):
        with self.lock:
            mac = self.arp_table.get(ip_bytes)
        if mac:
            return mac
        print(f'[ARP] 캐시 없음 -> {self._ip_str(ip_bytes)}에 대한 요청 전송 시도')
        self.request(ip_bytes)
        return None

    def request(self, target_ip: bytes):
        if not (self.src_ip and self.src_mac):
            return False
        iface = self._get_iface()
        if not iface:
            return False

        pkt = Ether(dst='ff:ff:ff:ff:ff:ff', src=self._mac_str(self.src_mac)) / \
              ARP(op=1, hwsrc=self._mac_str(self.src_mac), psrc=self._ip_str(self.src_ip), pdst=self._ip_str(target_ip))
        sendp(pkt, iface=iface, verbose=False)
        print(f'[ARP] Request 송신: who-has {self._ip_str(target_ip)}?')
        return True

    def reply(self, dst_ip, dst_mac, proxy_ip=None, proxy_mac=None):
        iface = self._get_iface()
        if not iface:
            return False

        psrc_ip = proxy_ip or self.src_ip
        src_mac = proxy_mac or self.src_mac

        pkt = Ether(dst=self._mac_str(dst_mac), src=self._mac_str(src_mac)) / \
              ARP(op=2, hwsrc=self._mac_str(src_mac), psrc=self._ip_str(psrc_ip), hwdst=self._mac_str(dst_mac), pdst=self._ip_str(dst_ip))
        sendp(pkt, iface=iface, verbose=False)
        print(f'[ARP] Reply 송신: {self._ip_str(psrc_ip)} is-at {self._mac_str(src_mac)}')
        return True

    # ==== Gratuitous ARP (기존 동일) ===========================================
    def send_gratuitous(self):
        if not (self.src_ip and self.src_mac):
            return False
        iface = self._get_iface()
        if not iface:
            return False

        pkt = Ether(dst='ff:ff:ff:ff:ff:ff', src=self._mac_str(self.src_mac)) / \
              ARP(op=2, hwsrc=self._mac_str(self.src_mac), psrc=self._ip_str(self.src_ip), hwdst='00:00:00:00:00:00', pdst=self._ip_str(self.src_ip))
        sendp(pkt, iface=iface, verbose=False)
        print(f'[ARP] Gratuitous 송신: {self._ip_str(self.src_ip)} is-at {self._mac_str(self.src_mac)}')
        return True

    def recv(self, data: bytes):
        # 1. ARP 패킷으로 파싱 시도
        try:
            pkt = ARP(data)
            if pkt.op not in [1, 2]:
                raise ValueError('Not an ARP packet')

            op = pkt.op

            # [수정 중요] tuple(...) 대신 bytes(...)를 사용해야 함
            # sender_ip = tuple(int(x) for x in pkt.psrc.split('.'))  <-- 기존 코드 (삭제)
            sender_ip = bytes(map(int, pkt.psrc.split('.')))        # <-- 수정 코드

            sender_mac = bytes.fromhex(pkt.hwsrc.replace(':', ''))

            # [수정 중요] 타겟 IP도 비교를 위해 bytes로 변환
            # target_ip = tuple(int(x) for x in pkt.pdst.split('.'))  <-- 기존 코드 (삭제)
            target_ip = bytes(map(int, pkt.pdst.split('.')))        # <-- 수정 코드

            if op == 2:
                with self.lock:
                    # 이제 bytes 키로 저장되므로 GUI에서 조회 가능
                    self.arp_table[sender_ip] = sender_mac
                print(f'[ARP] 캐시 학습: {pkt.psrc} -> {pkt.hwsrc}')
                return True

            elif op == 1:
                print(f'[ARP] Request 수신: who has {pkt.pdst}? tell {pkt.psrc}')

                # [수정] target_ip가 이미 bytes이므로 tuple() 변환 제거
                if target_ip == self.src_ip:  # tuple(self.src_ip) 제거
                    self.reply(sender_ip, sender_mac)
                    return True

                if target_ip in self.proxy_map:
                    proxy_mac = self.proxy_map[target_ip]
                    self.reply(sender_ip, sender_mac, proxy_ip=target_ip, proxy_mac=proxy_mac)
                    print(f'[ARP] Proxy ARP 응답: {pkt.pdst} 대신 응답함')
                    return True

            return True

        except Exception:
            if self.upper:
                return self.upper.recv(data)
            return False

    # ==== GUI 연동용 (기존 동일) ===============================================
    def add_proxy_entry_from_gui(self, ip_str, mac_str):
        try:
            ip_bytes = bytes(map(int, ip_str.split('.')))
            mac_bytes = bytes.fromhex(mac_str.replace(':', '').replace('-', ''))
            self.proxy_map[ip_bytes] = mac_bytes
            print(f'[ARP] (GUI) Proxy 추가: {ip_str} -> {mac_str}')
        except Exception as e:
            print(f'[ARP] (GUI) Proxy 추가 실패: {e}')

    def remove_proxy_entry(self, ip_str):
        try:
            ip_bytes = bytes(map(int, ip_str.split('.')))
            if ip_bytes in self.proxy_map:
                del self.proxy_map[ip_bytes]
                print(f'[ARP] (GUI) Proxy 삭제: {ip_str}')
            else:
                print(f'[ARP] (GUI) Proxy 항목 없음: {ip_str}')
        except Exception as e:
            print(f'[ARP] (GUI) Proxy 삭제 실패: {e}')

    def send_gratuitous_from_gui(self, mac_str):
        try:
            self.src_mac = bytes.fromhex(mac_str.replace(':', '').replace('-', ''))
            self.send_gratuitous()
            return True
        except Exception as e:
            print(f'[ARP] (GUI) Gratuitous 전송 실패: {e}')
            return False

    # ==== 내부 유틸 함수 (기존 동일) ===========================================
    def _get_iface(self):
        if hasattr(self.lower, 'iface'):
            return self.lower.iface
        phy = getattr(self.lower, 'lower', None)
        return getattr(phy, 'iface', None)

    @staticmethod
    def _ip_str(ip: bytes):
        return '.'.join(str(b) for b in ip)

    @staticmethod
    def _mac_str(mac: bytes):
        return ':'.join(f'{b:02x}' for b in mac)