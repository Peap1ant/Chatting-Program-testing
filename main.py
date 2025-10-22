from layers.ChatappLayer import ChatAppLayer
from layers.EthernetLayer import EthernetLayer
from layers.PhysicalLayer import PhysicalLayer
from layers.GUILayer import GUI
from scapy.all import get_if_hwaddr

# GUI 생성
gui = GUI()

# 기본 장치 선택
iface = gui.get_selected_device()
my_mac_str = get_if_hwaddr(iface)
my_mac = bytes.fromhex(my_mac_str.replace(':', ''))

# 레이어 생성
app = ChatAppLayer("User1")
eth = EthernetLayer()
phy = PhysicalLayer(iface=iface)

# 내 MAC 주소를 Ethernet 계층에 등록
eth.set_src_mac(my_mac)

# 각 계층 연결
app.set_lower(eth)
eth.set_upper(app)
eth.set_lower(phy)
phy.set_upper(eth)

# ✅ 장치 변경 시 콜백 (여기가 두 번째 블록)
def on_dev_change(selected_if):
    mac = bytes.fromhex(get_if_hwaddr(selected_if).replace(':', ''))
    eth.set_src_mac(mac)
    phy.iface = selected_if
    gui.set_my_mac(get_if_hwaddr(selected_if))
    gui.set_status(f"Device changed to {selected_if}")

gui.set_on_device_change(on_dev_change)

# GUI 연결 후 실행
app.set_gui(gui)
app.run()
