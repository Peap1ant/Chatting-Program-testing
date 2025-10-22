# ------ Import module(if needs) ------

import tkinter as tk
from tkinter import ttk, messagebox
from scapy.all import get_if_list

# ------ Main code ------

class GUI:
    def __init__(self, title='LAN Chatting Program'):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry('900x520')
        self.root.resizable(False, False)

        self._send_cb = None
        self._on_device_change_cb = None

        self._device_var = tk.StringVar()
        self._peer_mac_var = tk.StringVar(value='FF:FF:FF:FF:FF:FF')
        self._msg_var = tk.StringVar()
        self._my_mac_var = tk.StringVar(value='')

        top = tk.Frame(self.root)
        top.pack(side='top', fill='x', padx=12, pady=10)

        tk.Label(top, text='Device').grid(row=0, column=0, sticky='w')
        self.device_combo = ttk.Combobox(top, textvariable=self._device_var, state='readonly', width=40)
        self.device_combo.grid(row=0, column=1, sticky='w', padx=6)
        self.device_combo.bind('<<ComboboxSelected>>', self._on_device_change)

        self.refresh_btn = ttk.Button(top, text='Refresh', command=self.refresh_devices)
        self.refresh_btn.grid(row=0, column=2, padx=6)

        tk.Label(top, text='My MAC').grid(row=0, column=3, sticky='e', padx=(18,4))
        self.my_mac_label = tk.Label(top, textvariable=self._my_mac_var, relief='sunken', anchor='w', width=20)
        self.my_mac_label.grid(row=0, column=4, sticky='w')

        tk.Label(top, text='Peer MAC').grid(row=1, column=0, sticky='w', pady=(8,0))
        self.peer_entry = ttk.Entry(top, textvariable=self._peer_mac_var, width=43)
        self.peer_entry.grid(row=1, column=1, sticky='w', padx=6, pady=(8,0))

        tk.Label(top, text='Message').grid(row=1, column=3, sticky='e', padx=(18,4), pady=(8,0))
        self.msg_entry = ttk.Entry(top, textvariable=self._msg_var, width=28)
        self.msg_entry.grid(row=1, column=4, sticky='w', pady=(8,0))
        self.msg_entry.bind('<Return>', self._on_send)

        self.send_btn = ttk.Button(top, text='Send', command=self._on_send)
        self.send_btn.grid(row=1, column=5, padx=(8,0), pady=(8,0))

        mid = tk.Frame(self.root)
        mid.pack(side='top', fill='both', expand=True, padx=12, pady=(6,10))

        self.chat_text = tk.Text(mid, wrap='word', state='disabled')
        self.chat_scroll = ttk.Scrollbar(mid, orient='vertical', command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=self.chat_scroll.set)
        self.chat_text.pack(side='left', fill='both', expand=True)
        self.chat_scroll.pack(side='right', fill='y')

        status = tk.Frame(self.root)
        status.pack(side='bottom', fill='x')
        self.status_var = tk.StringVar(value='Ready')
        self.status_label = tk.Label(status, textvariable=self.status_var, anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True, padx=12, pady=6)

        self.refresh_devices()

    def refresh_devices(self):
        try:
            devices = get_if_list() or []
        except Exception as e:
            devices = []
            messagebox.showerror('Error', f'Interface enumerate failed: {e}')
        self.device_combo['values'] = devices
        if devices:
            self.device_combo.current(0)
            self._device_var.set(devices[0])
            self._notify_device_change(devices[0])
        else:
            self._device_var.set('')
            self.set_status('No interfaces found')

    def set_send_callback(self, fn):
        self._send_cb = fn

    def set_on_device_change(self, fn):
        self._on_device_change_cb = fn

    def set_my_mac(self, mac_text):
        self._my_mac_var.set(mac_text)

    def get_selected_device(self):
        return self._device_var.get()

    def get_peer_mac(self):
        return self._peer_mac_var.get().strip()

    def display_message(self, sender, text):
        self.chat_text.configure(state='normal')
        self.chat_text.insert('end', f'[{sender}] {text}\n')
        self.chat_text.see('end')
        self.chat_text.configure(state='disabled')

    def set_status(self, text):
        self.status_var.set(text)

    def _notify_device_change(self, sel):
        if self._on_device_change_cb:
            self._on_device_change_cb(sel)

    def _on_device_change(self, event=None):
        sel = self._device_var.get()
        self._notify_device_change(sel)

    def _on_send(self, event=None):
        msg = self._msg_var.get().strip()
        dst = self.get_peer_mac()
        if not msg:
            messagebox.showwarning('알림', '메시지를 입력하세요.')
            return
        if not dst:
            messagebox.showwarning('알림', '상대 MAC 주소를 입력하세요.')
            return
        if self._send_cb:
            ok = self._send_cb(dst, msg)
            if ok:
                self._msg_var.set('')
        else:
            messagebox.showerror('오류', '전송 콜백이 설정되지 않았습니다.')

    def run(self):
        self.root.mainloop()
