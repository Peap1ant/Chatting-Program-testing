from layers.GUILayer import GUI
from layers.ChatappLayer import ChatAppLayer
from layers.EthernetLayer import EthernetLayer
from layers.PhysicalLayer import PhysicalLayer
from scapy.all import get_if_hwaddr, conf

def mac_to_bytes(mac):
    return bytes.fromhex(mac.replace(":", ""))

if __name__ == "__main__":
    gui = GUI()
    try:
        iface = gui.get_selected_iface()
        if not iface:
            raise AttributeError
    except Exception:
        iface = getattr(conf, "iface", "")

    nickname = get_if_hwaddr(iface) if iface else "User"
    app = ChatAppLayer(nickname=nickname)
    eth = EthernetLayer()
    phy = PhysicalLayer(iface if iface else "")

    app.set_lower(eth)
    eth.set_upper(app)
    eth.set_lower(phy)
    phy.set_upper(eth)

    if iface:
        eth.set_src_mac(mac_to_bytes(get_if_hwaddr(iface)))

    app.set_gui(gui)
    phy.start()
    try:
        gui.run()
    finally:
        phy.stop()
