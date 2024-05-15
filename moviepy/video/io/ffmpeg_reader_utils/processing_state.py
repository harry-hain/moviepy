class ProcessingState:
    def __init__(self, proc=None, pos=0, lastread=None):
        self.proc = proc
        self.pos = pos
        self.lastread = lastread
