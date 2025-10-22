import tkinter as tk
from tkinter import ttk
import tkinter.font
import queue
import threading
from scapy.all import get_if_list, get_if_hwaddr, sniff
try:
    from scapy.arch.windows import get_windows_if_list
except Exception:
    get_windows_if_list = None

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Chatting Program')
        self.root.geometry('1000x600+0+0')
        self.root.resizable(False, False)
        self.font = tkinter.font.Font(family="Arial", size=10)
        self._send_cb = None
        self._q = queue.Queue()
        self.if_map = {}
        top = tk.Frame(self.root)
        top.pack(side='top', fill='x', padx=10, pady=8)
        tk.Label(top, text='Device').grid(row=0, column=0, sticky='w')
        self.if_var = tk.StringVar()
        self.if_combo = ttk.Combobox(top, textvariable=self.if_var, state='readonly', width=60, values=self._build_iface_display_list())
        if self.if_combo['values']:
            self.if_combo.current(0)
        self.if_combo.grid(row=0, column=1, padx=8, sticky='w')
        self.if_combo.bind('<<ComboboxSelected>>', self._on_iface_change)
        tk.Label(top, text='My MAC').grid(row=0, column=2, sticky='e')
        self.my_mac_var = tk.StringVar(value=self._get_current_mac())
        self.my_mac_lbl = tk.Label(top, textvariable=self.my_mac_var, width=20, anchor='w')
        self.my_mac_lbl.grid(row=0, column=3, padx=8, sticky='w')
        tk.Label(top, text='Peer MAC').grid(row=1, column=0, sticky='w', pady=(8,0))
        self.dst_mac_var = tk.StringVar()
        self.dst_mac_entry = tk.Entry(top, textvariable=self.dst_mac_var, width=30)
        self.dst_mac_entry.grid(row=1, column=1, padx=8, pady=(8,0), sticky='w')
        mid = tk.Frame(self.root)
        mid.pack(side='top', fill='both', expand=True, padx=10, pady=8)
        self.chat = tk.Text(mid, state='disabled', wrap='word')
        self.chat.pack(side='left', fill='both', expand=True)
        scroll = tk.Scrollbar(mid, command=self.chat.yview)
        scroll.pack(side='right', fill='y')
        self.chat['yscrollcommand'] = scroll.set
        bottom = tk.Frame(self.root)
        bottom.pack(side='bottom', fill='x', padx=10, pady=8)
        self.msg = tk.Text(bottom, height=3)
        self.msg.pack(side='left', fill='x', expand=True, padx=(0,8))
        self.msg.bind('<Shift-Return>', lambda e: self._insert_newline())
        self.msg.bind('<Return>', self._on_enter)
        self.send_btn = tk.Button(bottom, text='Send', width=12, command=self._on_send)
        self.send_btn.pack(side='right')
        self.root.after(50, self._drain_queue)
        self._on_iface_change()

    def _build_iface_display_list(self):
        displays = []
        self.if_map.clear()
        try:
            for item in get_windows_if_list():
                name = item.get('name') or ''
                desc = item.get('description') or ''
                mac = (item.get('mac') or '').lower()
                guid = item.get('guid') or ''
                # 내부 캡처용 이름
                dev_name = f"\\Device\\NPF_{guid}"
                display = f'{name} | {desc} | {mac}'
                self.if_map[display] = {'ifname': dev_name, 'mac': mac}
                displays.append(display)
        except Exception:
            for ifname in get_if_list():
                try:
                    mac = get_if_hwaddr(ifname).lower()
                except Exception:
                    mac = ''
                display = f'{ifname} | {mac}'
                self.if_map[display] = {'ifname': ifname, 'mac': mac}
                displays.append(display)
        return displays

    def _selected_ifname(self):
        key = self.if_var.get()
        info = self.if_map.get(key)
        return info['ifname'] if info else ''

    def _get_current_mac(self):
        ifname = self._selected_ifname()
        if not ifname:
            return '-'
        try:
            return get_if_hwaddr(ifname).lower()
        except Exception:
            return '-'

    def _on_iface_change(self, event=None):
        mac = self._get_current_mac()
        self.my_mac_var.set(mac)
        try:
            threading.Thread(target=self._autofill_peer_mac, daemon=True).start()
        except Exception:
            pass

    def _autofill_peer_mac(self):
        ifname = self._selected_ifname()
        if not ifname:
            return
        my_mac = self._get_current_mac()
        candidates = {}
        def collect(pkt):
            try:
                raw = bytes(pkt)
                smac = raw[6:12].hex(':')
                dmac = raw[0:6].hex(':')
                if smac and smac != my_mac and smac != 'ff:ff:ff:ff:ff:ff' and dmac in (my_mac, 'ff:ff:ff:ff:ff:ff'):
                    candidates[smac] = candidates.get(smac, 0) + 1
            except Exception:
                pass
        try:
            sniff(iface=ifname, prn=collect, store=False, timeout=1, count=30)
        except Exception:
            return
        if not candidates:
            return
        best = max(candidates.items(), key=lambda x: x[1])[0]
        self.dst_mac_var.set(best)

    def set_send_callback(self, cb):
        self._send_cb = cb

    def set_my_mac(self, mac_str):
        self.my_mac_var.set(mac_str.lower())

    def get_selected_iface(self):
        return self._selected_ifname()

    def display_message(self, sender, content):
        self._q.put(f'[{sender}]: {content}\n')

    def _drain_queue(self):
        try:
            while True:
                line = self._q.get_nowait()
                self.chat.configure(state='normal')
                self.chat.insert('end', line)
                self.chat.see('end')
                self.chat.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(50, self._drain_queue)

    def _on_send(self):
        if not self._send_cb:
            self.display_message('SYSTEM', '전송 콜백이 설정되지 않았습니다.')
            return
        dst = self.dst_mac_var.get().strip()
        msg = self.msg.get('1.0', 'end-1c')
        ok = self._send_cb(dst, msg)
        if ok:
            self.msg.delete('1.0', 'end')

    def _on_enter(self, event):
        self._on_send()
        return 'break'

    def _insert_newline(self):
        self.msg.insert('insert', '\n')
        return 'break'

    def run(self):
        self.root.mainloop()
