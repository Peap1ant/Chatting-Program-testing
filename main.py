from layers.ChatappLayer import ChatAppLayer
from layers.EthernetLayer import EthernetLayer
from layers.PhysicalLayer import PhysicalLayer
from layers.GUILayer import GUI
from scapy.all import get_if_hwaddr

gui = GUI()
iface = gui.get_selected_device()
my_mac = bytes.fromhex(get_if_hwaddr(iface).replace(':',''))

app = ChatAppLayer("User1")
eth = EthernetLayer()
phy = PhysicalLayer(iface=iface)

eth.set_src_mac(my_mac)

app.set_lower(eth); eth.set_upper(app)
eth.set_lower(phy); phy.set_upper(eth)

def on_dev_change(selected_if):
    from scapy.all import get_if_hwaddr
    phy.iface = selected_if
    eth.set_src_mac(bytes.fromhex(get_if_hwaddr(selected_if).replace(':','')))
    gui.set_my_mac(get_if_hwaddr(selected_if))

gui.set_on_device_change(on_dev_change)

phy.start()
app.set_gui(gui)
app.run()
phy.stop()
