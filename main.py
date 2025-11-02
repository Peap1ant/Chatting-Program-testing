from layers.ChatappLayer import ChatAppLayer
from layers.EthernetLayer import EthernetLayer
from layers.IPLayer import IPLayer
from layers.PhysicalLayer import PhysicalLayer
from layers.GUILayer import GUI

gui = GUI("LAN 채팅 프로그램")
iface = gui.get_selected_device()

app = ChatAppLayer()
ip_layer = IPLayer()
eth = EthernetLayer()
phy = PhysicalLayer(iface=iface)

app.set_lower(ip_layer)
ip_layer.set_upper(app)
ip_layer.set_lower(eth)
eth.set_upper(ip_layer)
eth.set_lower(phy)
phy.set_upper(eth)

def on_dev_change(selected_if, mac_str, ip_str):
    print(f"\n[Main] Device Change Event: iface={selected_if}, mac={mac_str}, ip={ip_str}")

    phy.set_iface(selected_if)

    try:
        # 1. MAC 주소 설정 (EthernetLayer.set_src_mac에서 로그)
        if mac_str:
            mac = bytes.fromhex(mac_str.replace(':', ''))
            eth.set_src_mac(mac)

        # 2. IP 주소 설정 (IPLayer.set_src_ip에서 로그)
        if ip_str and ip_str not in ['0.0.0.0', '127.0.0.1', None]:
            parts = ip_str.split('.')
            if len(parts) == 4:
                ip_bytes = b''.join([int(p).to_bytes(1, 'big') for p in parts])
                ip_layer.set_src_ip(ip_bytes)
                gui.set_status(f"Ready. Device: {selected_if} (IP: {ip_str})")
            else:
                raise ValueError("잘못된 IP 형식")
        else:
            ip_layer.set_src_ip(b'\x00\x00\x00\x00')
            gui.set_status(f"Warning: No valid IP found for {selected_if}. Using 0.0.0.0")

    except Exception as e:
        gui.set_status(f"Error setting device: {e}")
        ip_layer.set_src_ip(b'\x00\x00\x00\x00')

gui.set_on_device_change(on_dev_change)

app.set_gui(gui)
app.run()