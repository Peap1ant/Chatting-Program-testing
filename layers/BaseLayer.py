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
        return False

    def recv(self, data: bytes):
        return False

    def start(self):
        self.running = True
        if self.lower and hasattr(self.lower, "start"):
            self.lower.start()

    def stop(self):
        self.running = False
        if self.lower and hasattr(self.lower, "stop"):
            self.lower.stop()
