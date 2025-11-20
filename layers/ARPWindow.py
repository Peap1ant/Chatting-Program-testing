import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

def _ip_to_bytes(ip_str: str) -> bytes:
    parts = ip_str.split('.')
    if len(parts) != 4:
        raise ValueError('잘못된 IP 형식')
    return bytes(int(p) & 0xFF for p in parts)

def _mac_to_str(mac_bytes: bytes) -> str:
    return ':'.join(f'{b:02x}' for b in mac_bytes)

class TestArpDialog(tk.Toplevel):
    """
    'TestARP' 스크린샷과 같은 레이아웃의 Toplevel 창.
    사용법:
        win = TestArpDialog(parent_root, arp_layer)
    """
    def __init__(self, parent, arp):
        super().__init__(parent)
        self.title('TestARP')
        self.geometry('820x430')
        self.resizable(False, False)
        self.transient(parent)

        self.arp = arp

        # -------------------- 좌측: ARP Cache --------------------
        left_group = ttk.LabelFrame(self, text='ARP Cache')
        left_group.place(x=12, y=12, width=400, height=330)

        self.cache_tree = ttk.Treeview(
            left_group, columns=('ip','mac','state'), show='headings', height=10
        )
        self.cache_tree.heading('ip', text='IP 주소')
        self.cache_tree.heading('mac', text='H/W 주소')
        self.cache_tree.heading('state', text='상태')
        self.cache_tree.column('ip', width=130, anchor='w')
        self.cache_tree.column('mac', width=170, anchor='center')
        self.cache_tree.column('state', width=80, anchor='center')
        self.cache_tree.place(x=10, y=10, width=370, height=210)

        self.btn_item_del = ttk.Button(left_group, text='Item Delete', command=self._on_cache_item_delete)
        self.btn_all_del  = ttk.Button(left_group, text='All Delete',  command=self._on_cache_all_delete)
        self.btn_item_del.place(x=40, y=230, width=120, height=36)
        self.btn_all_del.place(x=210, y=230, width=120, height=36)

        ttk.Label(left_group, text='IP주소').place(x=10, y=280)
        self.ip_entry = ttk.Entry(left_group)
        self.ip_entry.place(x=70, y=276, width=200, height=26)
        self.btn_ip_send = ttk.Button(left_group, text='Send', command=self._on_ip_send)
        self.btn_ip_send.place(x=290, y=274, width=90, height=30)

        # -------------------- 우측: Proxy ARP --------------------
        right_group = ttk.LabelFrame(self, text='Proxy ARP Entry')
        right_group.place(x=424, y=12, width=380, height=330)

        self.proxy_list = tk.Listbox(right_group)
        self.proxy_list.place(x=10, y=10, width=360, height=210)

        self.btn_proxy_add = ttk.Button(right_group, text='Add', command=self._on_proxy_add)
        self.btn_proxy_del = ttk.Button(right_group, text='Delete', command=self._on_proxy_del)
        self.btn_proxy_add.place(x=70, y=230, width=110, height=36)
        self.btn_proxy_del.place(x=200, y=230, width=110, height=36)

        # -------------------- 하단: Gratuitous ARP --------------------
        garp_group = ttk.LabelFrame(self, text='Gratuitous ARP')
        garp_group.place(x=424, y=350, width=380, height=70)

        ttk.Label(garp_group, text='H/W 주소').place(x=10, y=10)
        self.garp_hw_entry = ttk.Entry(garp_group)
        self.garp_hw_entry.place(x=80, y=8, width=220, height=26)
        ttk.Button(garp_group, text='Send', command=self._on_garp_send).place(x=310, y=6, width=60, height=30)

        # -------------------- 하단 버튼: 종료 / 취소 --------------------
        ttk.Button(self, text='종료', command=self._on_close).place(x=130, y=380, width=150, height=34)
        ttk.Button(self, text='취소', command=self._on_close).place(x=300, y=380, width=150, height=34)

        # 초기 갱신
        self.refresh_views()

    # ---------- View 갱신 ----------
    def refresh_views(self):
        self._refresh_cache_tree()
        self._refresh_proxy_list()

    def _refresh_cache_tree(self):
        self.cache_tree.delete(*self.cache_tree.get_children())
        try:
            # arp_table: dict[ip_bytes] = mac_bytes
            for ip_b, mac_b in (self.arp.arp_table or {}).items():
                ip_str  = '.'.join(str(b) for b in ip_b)
                if mac_b is None or (isinstance(mac_b, str) and '?' in mac_b):
                    mac_str, state = '?' * 18, 'incomplete'
                else:
                    mac_str, state = _mac_to_str(mac_b), 'complete'
                self.cache_tree.insert('', 'end', values=(ip_str, mac_str, state))
        except Exception:
            pass

    def _refresh_proxy_list(self):
        self.proxy_list.delete(0, 'end')
        try:
            # proxy_map: dict[ip_bytes] = mac_bytes
            for ip_b, mac_b in (self.arp.proxy_map or {}).items():
                ip_str  = '.'.join(str(b) for b in ip_b)
                mac_str = _mac_to_str(mac_b)
                self.proxy_list.insert('end', f'{ip_str}    {mac_str}')
        except Exception:
            pass

    # ---------- 이벤트 핸들러 ----------
    def _on_cache_item_delete(self):
        sel = self.cache_tree.selection()
        if not sel:
            return
        for item in sel:
            ip_str = self.cache_tree.item(item, 'values')[0]
            try:
                ip_b = _ip_to_bytes(ip_str)
                # ARPLayer가 전용 삭제 메서드가 없다면 테이블에서 직접 pop
                if hasattr(self.arp, 'arp_table'):
                    self.arp.arp_table.pop(ip_b, None)
            except Exception:
                pass
        self._refresh_cache_tree()

    def _on_cache_all_delete(self):
        if hasattr(self.arp, 'arp_table'):
            try:
                self.arp.arp_table.clear()
            except Exception:
                pass
        self._refresh_cache_tree()

    def _on_ip_send(self):
        ip_str = self.ip_entry.get().strip()
        if not ip_str:
            return
        try:
            mac = self.arp.lookup(_ip_to_bytes(ip_str))  # 캐시 미스면 내부에서 ARP Request 전송
            if mac:
                messagebox.showinfo('ARP', f'{ip_str} → {_mac_to_str(mac)}')
            else:
                messagebox.showinfo('ARP', f'who-has {ip_str}? (요청 전송)')
        except Exception as e:
            messagebox.showerror('오류', f'ARP Lookup 실패: {e}')
        self._refresh_cache_tree()

    def _on_proxy_add(self):
        # 간단 입력 팝업 (IP, MAC)
        ip = simpledialog.askstring('Proxy ARP 추가', 'Target IP (예: 192.168.0.50)', parent=self)
        if not ip:
            return
        mac = simpledialog.askstring('Proxy ARP 추가', 'Owner MAC (예: aa:bb:cc:dd:ee:ff)', parent=self)
        if not mac:
            return
        try:
            self.arp.add_proxy_entry_from_gui(ip.strip(), mac.strip())
            self._refresh_proxy_list()
        except Exception as e:
            messagebox.showerror('오류', f'Proxy 추가 실패: {e}')

    def _on_proxy_del(self):
        # 선택된 라인에서 IP만 파싱
        sel = self.proxy_list.curselection()
        if not sel:
            return
        line = self.proxy_list.get(sel[0])
        ip = line.split()[0]
        try:
            self.arp.remove_proxy_entry(ip)
            self._refresh_proxy_list()
        except Exception as e:
            messagebox.showerror('오류', f'Proxy 삭제 실패: {e}')

    def _on_garp_send(self):
        hw = self.garp_hw_entry.get().strip()
        try:
            if hw:
                ok = self.arp.send_gratuitous_from_gui(hw)
            else:
                ok = self.arp.send_gratuitous()
            if ok:
                messagebox.showinfo('GARP', 'Gratuitous ARP 전송 완료')
            else:
                messagebox.showwarning('GARP', '전송 실패 (src/iface 확인)')
        except Exception as e:
            messagebox.showerror('오류', f'GARP 실패: {e}')

    def _on_close(self):
        self.destroy()
