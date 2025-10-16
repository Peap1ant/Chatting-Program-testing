# ------ Import module ------

import tkinter as tk
import tkinter.font

# ------ Main code ------

"""
Include GUI.
Can select connected device and setting MAC address.
Can input and send message, can recive message from other device.
"""

class GUI():

    def __init__(self):

        # Make root window
        self.root = tk.Tk()

        # Rename title
        self.root.title('Chatting Program')

        # Resize window
        self.root.geometry('1000x600+0+0')
        self.root.resizable(False, False)

        # Font
        self.font = tkinter.font.Font(family="Arial", size=10)

        # Placing title
        self.title_text = tkinter.Label(self.root, text='LAN Chatting Program')
        self.title_text.pack(side='top')
        

    def run(self):

        # Run GUI
        self.root.mainloop()