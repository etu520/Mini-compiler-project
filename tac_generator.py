
# Store TAC lines, temp and label generators...

class TACGenerator:
    def __init__(self):
        self.code = []       
        self._temp = 0
        self._label = 0

    def new_temp(self):
        self._temp += 1
        return f"T{self._temp}"

    def new_label(self):
        self._label += 1
        return f"L{self._label}"

    def emit(self, line):
        self.code.append(line)

    def get_code(self):
        return self.code[:]

    def dump(self):
        for i, l in enumerate(self.code, 1):
            print(f"({i}) {l}")
