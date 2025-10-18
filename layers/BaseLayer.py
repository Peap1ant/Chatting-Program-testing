# ------ Import module(if needs) ------

# ------ Main code ------

"""
Base of the all layers.

"""

class BaseLayer:
    
    def __init__(self):
        self.upper, self.lower, self.running = None

    # Setting upper layer

    def set_upper(self, layer):
        self.upper = layer

    # Setting lower layer

    def set_lower(self, layer):
        self.lower = layer

    # Setting data sending, WIP

    def send(self, data: bytes):
        None

    # Setting data receiving, WIP

    def recv(self, data: bytes):
        None

    # Setting running status

    def start(self):
        self.running = True

    def stop(self):
        self.running = False