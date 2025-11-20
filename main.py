from layers.ChatappLayer import ChatAppLayer
from layers.FileAppLayer import FileAppLayer  # 추가
from layers.EthernetLayer import EthernetLayer
from layers.IPLayer import IPLayer
from layers.ARPLayer import ARPLayer
from layers.PhysicalLayer import PhysicalLayer
from layers.GUILayer import GUI

gui = GUI("LAN 채팅 프로그램")
iface = gui.get_selected_device()

# 계층 생성
chat_app = ChatAppLayer()
file_app = FileAppLayer() # 추가
ip_layer = IPLayer()
arp = ARPLayer()
eth = EthernetLayer()
phy = PhysicalLayer(iface=iface)

# 계층 연결
# 1. App Layer들 -> IP Layer (하위 연결)
chat_app.set_lower(ip_layer)
file_app.set_lower(ip_layer)

# 2. IP Layer -> App Layer들 (상위 등록 - 프로토콜 ID 사용)
ip_layer.register_upper(IPLayer.PROTOCOL_CHAT, chat_app)
ip_layer.register_upper(IPLayer.PROTOCOL_FILE, file_app)

# 3. IP -> ARP -> Eth -> Phy (기존과 동일)
ip_layer.set_lower(arp)
arp.set_upper(ip_layer)
arp.set_lower(eth)
eth.set_upper(arp)
eth.set_lower(phy)
phy.set_upper(eth)

# GUI 연결
gui.attach_arp(arp)
chat_app.set_gui(gui)
file_app.set_gui(gui)   # GUI 연결
gui.set_file_send_callback(file_app.send) # 파일 전송 콜백 연결

# Device Change 핸들러
def on_dev_change(selected_if, mac_str, ip_str):
    print(f"\n[Main] Device Change: {selected_if}")
    phy.set_iface(selected_if)

    try:
        if mac_str:
            mac = bytes.fromhex(mac_str.replace(':', ''))
            eth.set_src_mac(mac)

        if ip_str and ip_str not in ['0.0.0.0', '127.0.0.1', None]:
            parts = ip_str.split('.')
            ip_bytes = b''.join([int(p).to_bytes(1, 'big') for p in parts])
            ip_layer.set_src_ip(ip_bytes)
            gui.set_status(f"Ready. IP: {ip_str}")
        else:
            ip_bytes = b'\x00'*4
            ip_layer.set_src_ip(ip_bytes)
            gui.set_status("Warning: No valid IP")

        # ARP 초기화
        arp.set_src_info(ip_bytes, mac)
        arp.send_gratuitous()
        arp.add_proxy_entry(b'\xC0\xA8\x00\x64', mac)

    except Exception as e:
        gui.set_status(f"Error: {e}")

gui.set_on_device_change(on_dev_change)

# 실행
# BaseLayer 구조상 start()는 최하위부터 연쇄적으로 불리지 않을 수 있으니 명시적 시작
phy.start()
gui.run()
phy.stop()