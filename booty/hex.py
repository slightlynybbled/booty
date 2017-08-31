import intelhex


class HexParser:
    def __init__(self, filename):
        self.memory_map = intelhex.IntelHex(filename)

    def get_opcode(self, address):
        if address % 2 != 0:
            raise ValueError('address must be even')

        addr = address << 1

        value = self.memory_map[addr]
        value += self.memory_map[addr + 1] << 8
        value += self.memory_map[addr + 2] << 16
        value += self.memory_map[addr + 3] << 24

        return value

if __name__ == '__main__':
    hp = HexParser('C:/_code/libs/blink.X/dist/default/production/blink.X.production.hex')
    opcode = hp.get_opcode(0x1080)
    print('{:06X}'.format(opcode))
