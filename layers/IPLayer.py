from .BaseLayer import BaseLayer

class IPLayer(BaseLayer):
    """
    일반적인 TCP/UDP 구조를 따라하는 게 아니므로 프로토콜 번호는 임의로 만든 값으로 설정합니다.
    이렇게 안 하고 그냥 TCP/UDP 구조 따라서 만들면 패킷이 들어왔을 때 Chatapp에서 처리할 건지 아닌지 구분을 할 수가 없어집니다.
    """
    IP_PROTO_CUSTOM = b'\xEE' # 임의의 커스텀 프로토콜 번호 (238)
    IP_BROADCAST = b'\xFF\xFF\xFF\xFF' # 255.255.255.255

    def __init__(self):
        super().__init__()
        # 기본 IP를 0.0.0.0으로 설정
        self.src_ip = b'\x00\x00\x00\x00'
        self.dst_ip = b'\x00\x00\x00\x00'

    def set_src_ip(self, ip_bytes: bytes):
        """이 호스트의 IP 주소를 4바이트로 설정합니다."""
        if len(ip_bytes) == 4:
            self.src_ip = ip_bytes
        else:
            print(f"[IP] 오류: 잘못된 Src IP 길이 {len(ip_bytes)}")

    def set_dst_ip(self, ip_bytes: bytes):
        """목적지 IP 주소를 4바이트로 설정합니다. (주로 브로드캐스트용)"""
        if len(ip_bytes) == 4:
            ip_str = '.'.join(f'{b:d}' for b in ip_bytes)
            print(f"[IP] Destination IP set to: {ip_str}")
            self.dst_ip = ip_bytes
        else:
            print(f"[IP] 오류: 잘못된 Dst IP 길이 {len(ip_bytes)}")

    def send(self, data: bytes):
        """
        상위 계층(ChatApp)의 데이터를 받아 IP 헤더를 추가하고
        하위 계층(Ethernet)으로 전송합니다.
        """
        if not self.lower:
            print("[IP] 전송 실패: 하위 계층이 설정되지 않음")
            return False

        # 9바이트 IP 헤더 생성: SrcIP(4) + DstIP(4) + Protocol(1)
        header = self.src_ip + self.dst_ip + self.IP_PROTO_CUSTOM
        packet = header + data

        # EthernetLayer로 패킷 전달
        return self.lower.send(packet)

    def recv(self, data: bytes):
        """
        하위 계층(Ethernet)에서 패킷을 받아 IP 헤더를 분석하고
        상위 계층(ChatApp)으로 페이로드를 올립니다.
        """
        # 최소 IP 헤더 길이(9바이트) 확인
        if len(data) < 9:
            print(f"[IP] 수신 실패: 패킷이 너무 짧음 ({len(data)}B)")
            return False

        # IP 헤더 파싱
        recv_src_ip = data[0:4]
        recv_dst_ip = data[4:8]
        recv_proto = data[8:9]

        # 프로토콜 번호 확인
        if recv_proto != self.IP_PROTO_CUSTOM:
            return False # 이 앱을 위한 패킷이 아님

        # 목적지 IP 주소 확인 (내 IP 이거나 L3 브로드캐스트)
        if recv_dst_ip != self.src_ip and recv_dst_ip != self.IP_BROADCAST:
            return False # 이 호스트를 위한 패킷이 아님

        payload = data[9:]
        if not payload:
            return False # 페이로드가 없음

        # 상위 계층으로 페이로드 전달
        if self.upper:
            return self.upper.recv(payload)

        return False

    def set_dst_mac(self, mac: bytes):
        if self.lower and hasattr(self.lower, 'set_dst_mac'):
            # 하위 계층(EthernetLayer)의 함수를 직접 호출
            self.lower.set_dst_mac(mac)
        else:
            print("[IP] 경고: 하위 계층에 'set_dst_mac' 속성이 없습니다.")