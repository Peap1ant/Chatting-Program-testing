from layers.ChatappLayer import ChatAppLayer
from layers.EthernetLayer import EthernetLayer
from layers.PhysicalLayer import PhysicalLayer
from layers.GUILayer import GUI

gui = GUI()
app = ChatAppLayer("User1")
eth = EthernetLayer()
phy = PhysicalLayer(iface=gui.get_selected_device())

app.set_lower(eth)
eth.set_upper(app)
eth.set_lower(phy)
phy.set_upper(eth)

app.set_gui(gui)
app.run()
