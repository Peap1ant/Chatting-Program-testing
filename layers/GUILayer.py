import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from scapy.all import get_if_list, get_if_hwaddr, get_if_addr
import re
import winreg
import os
import mimetypes
import threading
import time
from PIL import Image, ImageTk # pip install pillow 필요
from .ARPWindow import TestArpDialog

class GUI:
    def __init__(self, title='LAN Chatting Program'):

        self.arp = None
        self.chat_app = None # [추가] 로그 저장을 위해 ChatAppLayer 참조 필요

        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry('900x600') # 이미지 표시를 위해 세로 조금 늘림
        self.root.resizable(False, False)

        # 이미지 참조 유지용 캐시 (GC 방지)
        self.image_cache = {}

        # ... (ARP 메뉴 등 기존 코드 동일) ...
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
        self._delete_msg_cb = None

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

        # --- Row 1: My Info ---
        tk.Label(top, text='My MAC').grid(row=1, column=0, sticky='w', pady=(8,0))
        self.my_mac_label = tk.Entry(top, relief='sunken', width=30)
        self.my_mac_label.grid(row=1, column=1, sticky='w', padx=6, pady=(8,0))
        self.my_mac_label.insert(0, 'N/A')
        self.my_mac_label.configure(state='readonly')

        tk.Label(top, text='My IP').grid(row=1, column=2, sticky='e', padx=(10,4), pady=(8,0))
        self.my_ip_label = tk.Entry(top, relief='sunken', width=30)
        self.my_ip_label.grid(row=1, column=3, sticky='w', padx=6, pady=(8,0))
        self.my_ip_label.insert(0, 'N/A')
        self.my_ip_label.configure(state='readonly')

        # --- Row 2: Peer MAC ---
        tk.Label(top, text='Peer MAC').grid(row=2, column=0, sticky='w', pady=(8,0))
        self.peer_entry = ttk.Entry(top, textvariable=self._peer_mac_var, width=30)
        self.peer_entry.grid(row=2, column=1, sticky='w', padx=6, pady=(8,0))
        self.set_mac_btn = ttk.Button(top, text='Set MAC', command=self._on_set_mac)
        self.set_mac_btn.grid(row=2, column=2, padx=(10,4), pady=(8,0), sticky='w')

        # --- Row 3: Peer IP ---
        tk.Label(top, text='Peer IP').grid(row=3, column=0, sticky='w', pady=(8,0))
        self.peer_ip_entry = ttk.Entry(top, textvariable=self._peer_ip_var, width=30)
        self.peer_ip_entry.grid(row=3, column=1, sticky='w', padx=6, pady=(8,0))
        self.set_ip_btn = ttk.Button(top, text='Set IP', command=self._on_set_ip)
        self.set_ip_btn.grid(row=3, column=2, padx=(10,4), pady=(8,0), sticky='w')

        # --- Row 4: Message ---
        tk.Label(top, text='Message').grid(row=4, column=0, sticky='w', pady=(8,0))
        self.msg_entry = ttk.Entry(top, textvariable=self._msg_var, width=70)
        self.msg_entry.grid(row=4, column=1, columnspan=3, sticky='w', padx=6, pady=(8,0))
        self.msg_entry.bind('<Return>', self._on_send)

        self.send_btn = ttk.Button(top, text='Send', command=self._on_send)
        self.send_btn.grid(row=4, column=4, padx=2, pady=(8,0))

        self.file_btn = ttk.Button(top, text='File...', command=self._on_file_btn)
        self.file_btn.grid(row=4, column=5, padx=2, pady=(8,0))

        # --- Chat Area ---
        mid = tk.Frame(self.root)
        mid.pack(side='top', fill='both', expand=True, padx=12, pady=(10,10))
        self.chat_text = tk.Text(mid, wrap='word', state='disabled')
        self.chat_scroll = ttk.Scrollbar(mid, orient='vertical', command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=self.chat_scroll.set)
        self.chat_text.pack(side='left', fill='both', expand=True)
        self.chat_scroll.pack(side='right', fill='y')

        self.chat_text.bind("<Double-Button-1>", self._on_double_click_text)

        status = tk.Frame(self.root)
        status.pack(side='bottom', fill='x')
        self.status_var = tk.StringVar(value='Ready')
        self.status_label = tk.Label(status, textvariable=self.status_var, anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True, padx=12, pady=6)

        self.refresh_devices()

    # ... (set_title, _npf_to_friendly, refresh_devices 등 기존 메서드 생략) ...
    def set_title(self, title: str):
        self.root.title(title)

    def _npf_to_friendly(self, npf_name):
        m = re.search(r'\{[0-9A-Fa-f\-]{36}\}', npf_name)
        if not m: return npf_name
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

    # --- Callbacks Setters ---
    def set_send_callback(self, fn): self._send_cb = fn
    def set_on_device_change(self, fn): self._on_device_change_cb = fn
    def set_mac_callback(self, fn): self._set_mac_cb = fn
    def set_ip_callback(self, fn): self._set_ip_cb = fn
    def set_file_send_callback(self, fn): self._file_send_cb = fn
    def set_delete_msg_callback(self, fn): self._delete_msg_cb = fn

    def set_chat_app(self, chat_app):
        """[추가] ChatAppLayer 연결 (로그 기록용)"""
        self.chat_app = chat_app

    # --- Status Setters ---
    def set_my_mac(self, mac_text):
        def _apply():
            val = mac_text or 'N/A'
            self.my_mac_label.configure(state='normal')
            self.my_mac_label.delete(0, 'end')
            self.my_mac_label.insert(0, val)
            self.my_mac_label.configure(state='readonly')
        self.root.after(0, _apply)

    def set_my_ip(self, ip_text):
        def _apply():
            val = ip_text or 'N/A'
            self.my_ip_label.configure(state='normal')
            self.my_ip_label.delete(0, 'end')
            self.my_ip_label.insert(0, val)
            self.my_ip_label.configure(state='readonly')
        self.root.after(0, _apply)

    def get_selected_device(self):
        label = self._device_var.get()
        return self._display_to_npf.get(label, '')

    def get_peer_mac(self): return self._peer_mac_var.get().strip()
    def get_peer_ip(self): return self._peer_ip_var.get().strip()
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
        if self._on_device_change_cb: self._on_device_change_cb(npf_name, mac_str, ip_str)
        if self.arp:
            try:
                ip_b  = bytes(map(int, ip_str.split('.')))
                mac_b = bytes.fromhex(mac_str.replace(':','').replace('-', ''))
                self.arp.set_src_info(ip_b, mac_b)
            except Exception: pass

    def _on_device_change(self, event=None):
        label = self._device_var.get()
        npf = self._display_to_npf.get(label)
        if npf: self._notify_device_change(npf)

    def _on_set_mac(self, event=None):
        dst_mac = self.get_peer_mac()
        if not dst_mac:
            messagebox.showwarning('알림', 'MAC 주소를 입력하세요.')
            return
        if self._set_mac_cb:
            if self._set_mac_cb(dst_mac):
                self.set_status(f'Peer MAC set to {dst_mac}')
            else:
                self.set_status(f'Failed to set Peer MAC')
        else: messagebox.showerror('오류', 'MAC 설정 콜백이 설정되지 않았습니다.')

    def _on_set_ip(self, event=None):
        dst_ip = self.get_peer_ip()
        if not dst_ip:
            messagebox.showwarning('알림', 'IP 주소를 입력하세요.')
            return

        # 1. 하위 계층에 IP 설정 (기존 로직)
        if self._set_ip_cb:
            if self._set_ip_cb(dst_ip):
                self.set_status(f'Peer IP set to {dst_ip}')
            else:
                self.set_status(f'Failed to set Peer IP')
        else:
            messagebox.showerror('오류', 'IP 설정 콜백이 설정되지 않았습니다.')
            return

        # 2. [추가됨] ARP를 통해 MAC 주소 자동 찾기 시도
        if self.arp:
            self.set_status(f'Resolving MAC for {dst_ip}...')
            # GUI 멈춤 방지를 위해 별도 스레드에서 수행
            t = threading.Thread(target=self._perform_arp_resolution, args=(dst_ip,))
            t.daemon = True
            t.start()

    def _perform_arp_resolution(self, ip_str):
        """백그라운드에서 ARP 요청을 보내고 응답을 기다림"""
        try:
            # IP 문자열 -> bytes 변환
            ip_parts = ip_str.split('.')
            ip_bytes = bytes(int(p) for p in ip_parts)

            # 1. ARP 요청 전송 (lookup은 캐시에 없으면 요청을 보냄)
            # 이미 캐시에 있다면 즉시 리턴되지만, 없다면 None 리턴 후 내부적으로 Request 전송
            cached_mac = self.arp.lookup(ip_bytes)

            if cached_mac:
                # 이미 캐시에 있는 경우 즉시 업데이트
                self._update_peer_mac_gui(cached_mac)
                return

            # 2. 응답 대기 (Polling): 최대 2초간 대기 (0.2초 * 10회)
            for _ in range(10):
                time.sleep(0.2)
                # ARPLayer의 테이블 확인
                if ip_bytes in self.arp.arp_table:
                    found_mac = self.arp.arp_table[ip_bytes]
                    self._update_peer_mac_gui(found_mac)
                    return

            # 3. 실패 시 메시지
            self.root.after(0, lambda: self.set_status(f"ARP Failed: No response from {ip_str}"))

        except Exception as e:
            print(f"[GUI] ARP Resolution Error: {e}")

    def _update_peer_mac_gui(self, mac_bytes):
        """찾아낸 MAC 주소를 GUI에 반영하고 연결 설정"""
        mac_str = ':'.join(f'{b:02x}' for b in mac_bytes)

        def _gui_update():
            # 1. MAC 입력칸 채우기
            self._peer_mac_var.set(mac_str)
            # 2. 상태바 업데이트
            self.set_status(f"ARP Resolved: {mac_str}")
            # 3. 자동으로 'Set MAC' 버튼 누른 효과 (연결 확정)
            self._on_set_mac()

        self.root.after(0, _gui_update)

    def _on_send(self, event=None):
        msg = self._msg_var.get().strip()
        if not msg:
            messagebox.showwarning('알림', '메시지를 입력하세요.')
            return
        if self._send_cb:
            ok = self._send_cb(msg)
            if ok: self._msg_var.set('')
        else: messagebox.showerror('오류', '전송 콜백이 설정되지 않았습니다.')

    def _on_file_btn(self):
        filename = filedialog.askopenfilename(title='Select File to Send')
        if filename:
            if self._file_send_cb: self._file_send_cb(filename)
            else: messagebox.showerror('Error', 'File callback not set')

    def attach_arp(self, arp): self.arp = arp

    def open_ARP_window(self):
        if not getattr(self, 'arp', None):
            messagebox.showerror('오류', 'ARPLayer가 연결되지 않았습니다.')
            return
        if getattr(self, '_arp_win', None) and self._arp_win.winfo_exists():
            self._arp_win.lift(); self._arp_win.focus_force(); return
        self._arp_win = TestArpDialog(self.root, self.arp)

    # --- [수정] 채팅/파일 표시 메서드 ---

    def clear_chat(self):
        self.chat_text.configure(state='normal')
        self.chat_text.delete('1.0', 'end')
        self.chat_text.configure(state='disabled')
        self.image_cache = {} # 캐시 초기화

    def display_message(self, sender, text, msg_id=None):
        """텍스트 메시지 표시 (태그 범위 수정)"""
        def _append():
            self.chat_text.configure(state='normal')

            # 1. 삽입 전 시작 위치 기록
            start_index = self.chat_text.index('end-1c')

            # 2. 텍스트 삽입
            full_msg = f'[{sender}] {text}\n'
            self.chat_text.insert('end', full_msg)

            # 3. 삽입 후 끝 위치 기록 및 태그 적용
            if msg_id:
                end_index = self.chat_text.index('end-1c')
                self.chat_text.tag_add(msg_id, start_index, end_index)

            self.chat_text.see('end')
            self.chat_text.configure(state='disabled')
        self.root.after(0, _append)

    def display_image(self, sender, image_path, msg_id=None):
        """이미지를 채팅창에 삽입 (텍스트+이미지 전체 태그)"""
        def _append():
            if not os.path.exists(image_path):
                self.display_message(sender, f"[Image not found: {image_path}]", msg_id)
                return

            try:
                # Pillow로 이미지 로드
                pil_img = Image.open(image_path)
                tk_img = ImageTk.PhotoImage(pil_img)

                # GC 방지
                img_key = msg_id if msg_id else str(len(self.image_cache))
                self.image_cache[img_key] = tk_img

                self.chat_text.configure(state='normal')

                # 1. 삽입 전 시작 위치 기록 (이 시점부터 태그 시작)
                start_index = self.chat_text.index('end-1c')

                # 2. 구성 요소 삽입
                # (1) 보낸 사람 및 텍스트 표시
                self.chat_text.insert('end', f'[{sender}] [Image]\n')
                # (2) 이미지 삽입
                self.chat_text.image_create('end', image=tk_img)
                # (3) 하단 여백(줄바꿈)
                self.chat_text.insert('end', '\n')

                # 3. 삽입 후 끝 위치 기록 및 태그 적용
                if msg_id:
                    end_index = self.chat_text.index('end-1c')
                    # start~end 범위(텍스트+이미지+여백)를 모두 ID로 태깅
                    self.chat_text.tag_add(msg_id, start_index, end_index)

                self.chat_text.see('end')
                self.chat_text.configure(state='disabled')

            except Exception as e:
                print(f"Image Render Error: {e}")
                self.display_message(sender, f"[Image Render Failed: {os.path.basename(image_path)}]", msg_id)

        self.root.after(0, _append)

    def remove_message_ui(self, msg_id):
        """ID에 해당하는 메시지(텍스트 혹은 이미지 블록) 전체 삭제"""
        def _remove():
            self.chat_text.configure(state='normal')

            # 태그가 걸린 모든 범위를 찾아 삭제
            # tag_ranges는 (start1, end1, start2, end2...) 튜플을 반환
            ranges = self.chat_text.tag_ranges(msg_id)

            # 범위가 존재하면 뒤에서부터 삭제 (인덱스 밀림 방지)를 하거나,
            # 보통 메시지는 하나의 덩어리이므로 첫 번째 범위만 지워도 됨.
            # 여기서는 안전하게 루프를 돌며 삭제합니다.
            if ranges:
                # 짝수(start), 홀수(end) 인덱스 쌍 처리
                for i in range(len(ranges) - 2, -1, -2):
                    start = ranges[i]
                    end = ranges[i+1]
                    self.chat_text.delete(start, end)

            self.chat_text.configure(state='disabled')

            # 이미지 캐시에서도 삭제
            if msg_id in self.image_cache:
                del self.image_cache[msg_id]

        self.root.after(0, _remove)

    def _on_double_click_text(self, event):
        try:
            index = event.widget.index(f"@{event.x},{event.y}")
            tags = event.widget.tag_names(index)
            for tag in tags:
                if tag in ('sel', 'current'): continue
                if messagebox.askyesno("삭제", "이 메시지를 삭제하시겠습니까?"):
                    if self._delete_msg_cb:
                        self._delete_msg_cb(tag)
                    else:
                        messagebox.showerror("오류", "삭제 콜백이 없습니다.")
                return
        except Exception as e:
            print(f"Click Error: {e}")

    # --- [추가] 파일 수신/송신 처리 (이미지 판별 로직) ---
    def _check_is_valid_image(self, path):
        """MIME 타입이 image이고 512x512 이하인지 확인"""
        try:
            mime, _ = mimetypes.guess_type(path)
            if not mime or not mime.startswith('image'):
                return False

            with Image.open(path) as img:
                w, h = img.size
                if w <= 512 and h <= 512:
                    return True
        except:
            pass
        return False

    def on_file_received_msg(self, full_path):
        """FileAppLayer에서 수신 완료 후 호출"""
        filename = os.path.basename(full_path)

        # 1. 이미지 조건 확인
        is_image = self._check_is_valid_image(full_path)

        # 2. ChatAppLayer에 로그 저장 요청 (상대 경로로 변환 필요)
        # logs/ 디렉터리가 기준이 아니라 실행 파일 기준 상대 경로 (./files/...)
        rel_path = os.path.relpath(full_path, start='.')
        # 윈도우 경로(\)를 /로 변환 (JSON 호환성)
        rel_path = rel_path.replace('\\', '/')

        if self.chat_app:
            if is_image:
                self.chat_app.log_file_event('PEER', rel_path, is_image=True)
            else:
                self.chat_app.log_file_event('PEER', rel_path, is_image=False)

    def on_file_sent_msg(self, full_path):
        """FileAppLayer에서 송신 시작/완료 시 호출 (내 화면 표시용)"""
        # 내가 보낸 파일도 로그에 남기고 화면에 띄움
        is_image = self._check_is_valid_image(full_path)
        rel_path = os.path.relpath(full_path, start='.')
        rel_path = rel_path.replace('\\', '/')

        if self.chat_app:
            if is_image:
                self.chat_app.log_file_event('ME', rel_path, is_image=True)
            else:
                self.chat_app.log_file_event('ME', rel_path, is_image=False)

    def run(self):
        self.root.mainloop()