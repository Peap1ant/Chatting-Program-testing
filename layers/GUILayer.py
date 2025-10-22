# ------ Import module ------

import tkinter as tk
from tkinter import ttk, messagebox

# ------ Main code ------

"""
Include GUI.
Can select connected device and setting MAC address.
Can input and send message, can recive message from other device.
"""

class GUI:
    def __init__(self, title='LAN Chatting Program'):

        # root

        self.root = tk.Tk()

        # title

        self.root.title(title)

        # set resolution

        self.root.geometry('1000x600+0+0')
        self.root.resizable(False, False)

        # some var

        self._send_cb = None
        self._on_device_change_cb = None
        self._my_id_var = tk.StringVar(value='Me')
        self._dst_mac_var = tk.StringVar()
        self._message_var = tk.StringVar()
        self._device_var = tk.StringVar()
        self._devices = []

        # make frame

        top = tk.Frame(self.root)
        top.pack(side='top', fill='x', padx=12, pady=8)

        # add some component

        tk.Label(top, text='Device').grid(row=0, column=0, sticky='w')
        self.device_combo = ttk.Combobox(top, textvariable=self._device_var, state='readonly', width=32)
        self.device_combo.grid(row=0, column=1, sticky='w', padx=8)
        self.device_combo.bind('<<ComboboxSelected>>', self._on_device_change)

        tk.Label(top, text='My ID').grid(row=0, column=2, sticky='e', padx=(24,4))
        self.my_id_label = tk.Label(top, textvariable=self._my_id_var, relief='sunken', width=20, anchor='w')
        self.my_id_label.grid(row=0, column=3, sticky='w')

        tk.Label(top, text='Peer MAC').grid(row=1, column=0, sticky='w', pady=(8,0))
        self.dst_entry = ttk.Entry(top, textvariable=self._dst_mac_var, width=35)
        self.dst_entry.grid(row=1, column=1, sticky='w', padx=8, pady=(8,0))
        self.dst_entry.insert(0, 'FF:FF:FF:FF:FF:FF')

        tk.Label(top, text='Message').grid(row=1, column=2, sticky='e', padx=(24,4), pady=(8,0))
        self.msg_entry = ttk.Entry(top, textvariable=self._message_var, width=40)
        self.msg_entry.grid(row=1, column=3, sticky='w', pady=(8,0))
        self.msg_entry.bind('<Return>', self._on_send)

        self.send_btn = ttk.Button(top, text='Send', command=self._on_send)
        self.send_btn.grid(row=1, column=4, padx=(10,0), pady=(8,0))

        top.grid_columnconfigure(3, weight=1)

        mid = tk.Frame(self.root)
        mid.pack(side='top', fill='both', expand=True, padx=12, pady=(6,8))

        self.chat_text = tk.Text(mid, height=24, wrap='word', state='disabled')
        self.chat_scroll = ttk.Scrollbar(mid, orient='vertical', command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=self.chat_scroll.set)
        self.chat_text.pack(side='left', fill='both', expand=True)
        self.chat_scroll.pack(side='right', fill='y')
        status = tk.Frame(self.root)
        status.pack(side='bottom', fill='x')
        self.status_var = tk.StringVar(value='Ready')
        self.status_label = tk.Label(status, textvariable=self.status_var, anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True, padx=12, pady=4)

    def set_send_callback(self, fn):
        self._send_cb = fn

    def set_on_device_change(self, fn):
        self._on_device_change_cb = fn

    def set_device_list(self, devices):
        self._devices = list(devices or [])
        self.device_combo['values'] = self._devices
        if self._devices:
            self.device_combo.current(0)
            self._device_var.set(self._devices[0])
            if self._on_device_change_cb:
                self._on_device_change_cb(self._devices[0])

    def set_my_mac(self, text):
        self._my_id_var.set(text)

    def get_selected_device(self):
        return self._device_var.get()

    def get_peer_mac(self):
        return self._dst_mac_var.get().strip()

    def display_message(self, sender, text):
        self.chat_text.configure(state='normal')
        self.chat_text.insert('end', f'[{sender}] {text}\n')
        self.chat_text.see('end')
        self.chat_text.configure(state='disabled')

    def set_status(self, text):
        self.status_var.set(text)

    def _on_device_change(self, event=None):
        sel = self._device_var.get()
        if self._on_device_change_cb:
            self._on_device_change_cb(sel)

    def _on_send(self, event=None):
        msg = self._message_var.get().strip()
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
                self._message_var.set('')

        else:
            messagebox.showerror('오류', '전송 콜백이 설정되지 않았습니다.')

    def run(self):
        self.root.mainloop()
