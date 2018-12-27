import intelhex


class AddressSegment:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __str__(self):
        return '[{:06X} : {:06x}]'.format(self.start, self.end)


class HexParser:
    def __init__(self, filename):
        self.memory_map = intelhex.IntelHex(filename)

    @property
    def segments(self):
        # have to divide by 2, since IntelHex uses byte addresses
        # and we use addresses of int16's
        return [AddressSegment(start // 2, end // 2) for start, end in self.memory_map.segments()]

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
