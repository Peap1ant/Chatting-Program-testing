# ------ Import module(if needs) ------

# ------ Main code ------

"""
Base of the all layers.

"""

class BaseLayer:
    def __init__(self):
        self.upper = None
        self.lower = None
        self.running = False

    def set_upper(self, layer):
        self.upper = layer

    def set_lower(self, layer):
        self.lower = layer

    def send(self, data: bytes):
        return None

    def recv(self, data: bytes):
        return None

    def start(self):
        self.running = True

    def stop(self):
        self.running = False
        