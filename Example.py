2# ------ import libraries--

import tkinter
import tkinter.font
from scapy.all import Ether, IP, TCP, sendp

# ------ main code ------

# Window
win = tkinter.Tk()

# Title
win.title('패킷 전송 테스트')

# Resolution
win.geometry('500x300+0+0')
win.resizable(False, False)

# Font
font = tkinter.font.Font(family="Arial", size=10)

# Title
title_text = tkinter.Label(win, text='패킷 전송 테스트')
title_text.pack(side='top')

# ----- Entry ------

entry_label = tkinter.Label(win, text='전송할 내용: ')
entry_label.place(x = 50, y = 50)

entry_entry = tkinter.Entry(win, width=20) # 0 + 학번적기
entry_entry.place(x = 150, y = 51)


# ------ send packet code def ------

class custom_class:
    def __init__(self):
        self.count = 0

    def send_packet(self):
        if self.count == 1:
            self.done.destroy()

        # Packet sending
        self.target_mac = 'F0:2F:74:8A:C3:11'
        self.target_ip = '192.168.0.3'
        self.target_port = 80

        self.packet = Ether(dst = self.target_mac) / IP(dst = self.target_ip) / TCP(dport = self.target_port) / f'{entry_entry.get()}'

        sendp(self.packet)

        # Place "Done!" message
        self.done = tkinter.Label(win, text='Done!')
        self.done.place(x = 400, y = 250)
        self.count = 1

c = custom_class()

Btn = tkinter.Button(text = '패킷 전송하기', width = 10)
Btn.config(command = c.send_packet)
Btn.place(x = 350, y = 50)

# Start GUI
win.mainloop()