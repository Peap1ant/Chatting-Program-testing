import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from scapy.all import get_if_list, get_if_hwaddr, get_if_addr
import re
import winreg
from .ARPWindow import TestArpDialog

class GUI:
    def __init__(self, title='LAN Chatting Program'):

        self.arp = None

        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry('900x520')
        self.root.resizable(False, False)

        # ARP window
        self.menubar = tk.Menu(self.root)
        tools = tk.Menu(self.menubar, tearoff=0)
        tools.add_command(label = 'ARP Tool...', command = self.open_ARP_window)
        self.menubar.add_cascade(label = 'Tools', menu = tools)
        self.root.config(menu = self.menubar)

        # 콜백 함수들
        self._send_cb = None
        self._file_send_cb = None
        self._on_device_change_cb = None
        self._set_mac_cb = None
        self._set_ip_cb = None

        # GUI 변수들
        self._device_var = tk.StringVar()
        self._peer_mac_var = tk.StringVar(value='FF:FF:FF:FF:FF:FF')
        self._peer_ip_var = tk.StringVar(value='255.255.255.255')
        self._msg_var = tk.StringVar()
        self._display_to_npf = {}

        top = tk.Frame(self.root)
        top.pack(side='top', fill='x', padx=12, pady=10)

        # --- Row 0: Device Selection ---
        tk.Label(top, text='Device').grid(row=0, column=0, sticky='w')
        self.device_combo = ttk.Combobox(top, textvariable=self._device_var, state='readonly', width=70)
        self.device_combo.grid(row=0, column=1, columnspan=3, sticky='w', padx=6)
        self.device_combo.bind('<<ComboboxSelected>>', self._on_device_change)

        self.refresh_btn = ttk.Button(top, text='Refresh', command=self.refresh_devices)
        self.refresh_btn.grid(row=0, column=4, padx=6)

        # --- Row 1: My Info (MAC & IP) ---
        tk.Label(top, text='My MAC').grid(row=1, column=0, sticky='w', pady=(8,0))

        self.my_mac_label = tk.Entry(top, relief='sunken', width=30)
        self.my_mac_label.grid(row=1, column=1, sticky='w', padx=6, pady=(8,0))
        self.my_mac_label.insert(0, 'N/A')
        self.my_mac_label.configure(state='readonly') # 'readonly' 상태로 설정

        tk.Label(top, text='My IP').grid(row=1, column=2, sticky='e', padx=(10,4), pady=(8,0))

        self.my_ip_label = tk.Entry(top, relief='sunken', width=30)
        self.my_ip_label.grid(row=1, column=3, sticky='w', padx=6, pady=(8,0))
        self.my_ip_label.insert(0, 'N/A')
        self.my_ip_label.configure(state='readonly') # 'readonly' 상태로 설정

        # --- Row 2: Peer MAC (Entry + Button) ---
        tk.Label(top, text='Peer MAC').grid(row=2, column=0, sticky='w', pady=(8,0))
        self.peer_entry = ttk.Entry(top, textvariable=self._peer_mac_var, width=30)
        self.peer_entry.grid(row=2, column=1, sticky='w', padx=6, pady=(8,0))

        self.set_mac_btn = ttk.Button(top, text='Set MAC', command=self._on_set_mac)
        self.set_mac_btn.grid(row=2, column=2, padx=(10,4), pady=(8,0), sticky='w')

        # --- Row 3: Peer IP (Entry + Button) ---
        tk.Label(top, text='Peer IP').grid(row=3, column=0, sticky='w', pady=(8,0))
        self.peer_ip_entry = ttk.Entry(top, textvariable=self._peer_ip_var, width=30)
        self.peer_ip_entry.grid(row=3, column=1, sticky='w', padx=6, pady=(8,0))

        self.set_ip_btn = ttk.Button(top, text='Set IP', command=self._on_set_ip)
        self.set_ip_btn.grid(row=3, column=2, padx=(10,4), pady=(8,0), sticky='w')

        # --- Row 4: Message (Entry + Button) ---
        tk.Label(top, text='Message').grid(row=4, column=0, sticky='w', pady=(8,0))
        self.msg_entry = ttk.Entry(top, textvariable=self._msg_var, width=70)
        self.msg_entry.grid(row=4, column=1, columnspan=3, sticky='w', padx=6, pady=(8,0))
        self.msg_entry.bind('<Return>', self._on_send)

        self.send_btn = ttk.Button(top, text='Send', command=self._on_send)
        self.send_btn.grid(row=4, column=4, padx=2, pady=(8,0))

        self.file_btn = ttk.Button(top, text='File...', command=self._on_file_btn)
        self.file_btn.grid(row=4, column=5, padx=2, pady=(8,0))

        mid = tk.Frame(self.root)
        mid.pack(side='top', fill='both', expand=True, padx=12, pady=(10,10))
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

    def set_title(self, title: str):
        self.root.title(title)

    def _npf_to_friendly(self, npf_name):
        m = re.search(r'\{[0-9A-Fa-f\-]{36}\}', npf_name)
        if not m:
            return npf_name
        guid = m.group(0)
        path = r'SYSTEM\\CurrentControlSet\\Control\\Network\\{4d36e972-e325-11ce-bfc1-08002be10318}\\' + guid + r'\\Connection'
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            name, _ = winreg.QueryValueEx(key, 'Name')
            winreg.CloseKey(key)
            return name
        except OSError: return npf_name

    def refresh_devices(self):
        try:
            raw = get_if_list() or []
            names = []
            self._display_to_npf = {}
            for npf in raw:
                disp = self._npf_to_friendly(npf)
                if disp == r'\Device\NPF_Loopback': continue
                names.append(disp)
                self._display_to_npf[disp] = npf
        except Exception as e:
            names = []
            messagebox.showerror('Error', f'Interface enumerate failed: {e}')
        self.device_combo['values'] = names
        if names:
            self.device_combo.current(0)
            self._device_var.set(names[0])
            self._notify_device_change(self._display_to_npf[names[0]])
        else:
            self._device_var.set('')
            self.set_status('No interfaces found')
            self.set_my_mac('N/A')
            self.set_my_ip('N/A')

    def set_send_callback(self, fn):
        self._send_cb = fn

    def set_on_device_change(self, fn):
        self._on_device_change_cb = fn

    def set_mac_callback(self, fn):
        self._set_mac_cb = fn

    def set_ip_callback(self, fn):
        self._set_ip_cb = fn

    def set_file_send_callback(self, fn):
        self._file_send_cb = fn

    def set_my_mac(self, mac_text):
        def _apply():
            val = mac_text or 'N/A'
            self.my_mac_label.configure(state='normal') # 쓰기 가능
            self.my_mac_label.delete(0, 'end')
            self.my_mac_label.insert(0, val)
            self.my_mac_label.configure(state='readonly') # 다시 읽기 전용
        self.root.after(0, _apply)

    def set_my_ip(self, ip_text):
        def _apply():
            val = ip_text or 'N/A'
            self.my_ip_label.configure(state='normal') # 쓰기 가능
            self.my_ip_label.delete(0, 'end')
            self.my_ip_label.insert(0, val)
            self.my_ip_label.configure(state='readonly') # 다시 읽기 전용
        self.root.after(0, _apply)

    def get_selected_device(self):
        label = self._device_var.get()
        return self._display_to_npf.get(label, '')

    def get_peer_mac(self):
        return self._peer_mac_var.get().strip()

    def get_peer_ip(self):
        return self._peer_ip_var.get().strip()

    def display_message(self, sender, text):
        def _append():
            self.chat_text.configure(state='normal')
            self.chat_text.insert('end', f'[{sender}] {text}\n')
            self.chat_text.see('end')
            self.chat_text.configure(state='disabled')
        self.root.after(0, _append)

    def set_status(self, text):
        def _apply(): self.status_var.set(text)
        self.root.after(0, _apply)

    def _notify_device_change(self, npf_name):
        try: mac_str = get_if_hwaddr(npf_name)
        except Exception: mac_str = ''
        try: ip_str = get_if_addr(npf_name)
        except Exception: ip_str = '0.0.0.0'

        self.set_my_mac(mac_str)
        self.set_my_ip(ip_str)

        if self._on_device_change_cb:
            self._on_device_change_cb(npf_name, mac_str, ip_str)

        if self.arp:
            try:
                ip_b  = bytes(map(int, ip_str.split('.')))
                mac_b = bytes.fromhex(mac_str.replace(':','').replace('-', ''))
                self.arp.set_src_info(ip_b, mac_b)  # ARP가 이후 lookup/GARP에 사용할 내 IP/MAC 등록
            except Exception:
                pass

    def _on_device_change(self, event=None):
        label = self._device_var.get()
        npf = self._display_to_npf.get(label)
        if npf:
            self._notify_device_change(npf)

    def _on_set_mac(self, event=None):
        dst_mac = self.get_peer_mac()
        if not dst_mac:
            messagebox.showwarning('알림', 'MAC 주소를 입력하세요.')
            return
        if self._set_mac_cb:
            if self._set_mac_cb(dst_mac):
                self.set_status(f'Peer MAC set to {dst_mac}')
            else:
                self.set_status(f'Failed to set Peer MAC (invalid format?)')
        else:
            messagebox.showerror('오류', 'MAC 설정 콜백이 설정되지 않았습니다.')

    def _on_set_ip(self, event=None):
        dst_ip = self.get_peer_ip()
        if not dst_ip:
            messagebox.showwarning('알림', 'IP 주소를 입력하세요.')
            return
        if self._set_ip_cb:
            if self._set_ip_cb(dst_ip):
                self.set_status(f'Peer IP set to {dst_ip}')
            else:
                self.set_status(f'Failed to set Peer IP (invalid format?)')
        else:
            messagebox.showerror('오류', 'IP 설정 콜백이 설정되지 않았습니다.')

    def _on_send(self, event=None):
        msg = self._msg_var.get().strip()
        if not msg:
            messagebox.showwarning('알림', '메시지를 입력하세요.')
            return
        if self._send_cb:
            ok = self._send_cb(msg)
            if ok:
                self._msg_var.set('')
        else:
            messagebox.showerror('오류', '전송 콜백이 설정되지 않았습니다.')

    def _on_file_btn(self):
        """파일 선택 모달"""
        filename = filedialog.askopenfilename(title='Select File to Send')
        if filename:
            if self._file_send_cb:
                self._file_send_cb(filename)
            else:
                messagebox.showerror('Error', 'File callback not set')

    def attach_arp(self, arp):
        """메인에서 생성한 ARPLayer를 붙인다"""
        self.arp = arp

    def open_ARP_window(self):
        if not getattr(self, 'arp', None):
            messagebox.showerror('오류', 'ARPLayer가 연결되지 않았습니다.')
            return
        if getattr(self, '_arp_win', None) and self._arp_win.winfo_exists():
            self._arp_win.lift(); self._arp_win.focus_force(); return
        self._arp_win = TestArpDialog(self.root, self.arp)

    def run(self):
        self.root.mainloop()