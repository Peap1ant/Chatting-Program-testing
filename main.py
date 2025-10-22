from layers.ChatappLayer import ChatAppLayer
from layers.EthernetLayer import EthernetLayer
from layers.PhysicalLayer import PhysicalLayer
from layers.GUILayer import GUI
from scapy.all import get_if_hwaddr

gui = GUI()
iface = gui.get_selected_device()

app = ChatAppLayer("User1")
eth = EthernetLayer()
phy = PhysicalLayer(iface=iface)

app.set_lower(eth)
eth.set_upper(app)
eth.set_lower(phy)
phy.set_upper(eth)

def on_dev_change(selected_if):
    phy.iface = selected_if
    try:
        mac_str = get_if_hwaddr(selected_if)
        mac = bytes.fromhex(mac_str.replace(':',''))
        eth.set_src_mac(mac)
        gui.set_my_mac(mac_str)
        gui.set_status(f"Device changed to {selected_if}")
    except Exception:
        gui.set_status("MAC 주소를 가져오지 못했습니다.")

gui.set_on_device_change(on_dev_change)

try:
    mac_str = get_if_hwaddr(iface) if iface else ''
    if mac_str:
        eth.set_src_mac(bytes.fromhex(mac_str.replace(':','')))
        gui.set_my_mac(mac_str)
except Exception:
    pass

app.set_gui(gui)
app.run()
