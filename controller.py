import logging
import threading
import time

import serial
from framer import Framer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

READ_PLATFORM = 0x00
READ_VERSION = 0x01
READ_ROW_LEN = 0x02
READ_PAGE_LEN = 0x03
READ_PROG_LEN = 0x04
READ_MAX_PROG_SIZE = 0x05

ERASE_PAGE = 0x10
ERASE_ALL = 0x11

READ_ADDR = 0x20

WRITE_ROW = 0x30
WRITE_PAGE = 0x31


class Controller:
    def __init__(self, port, timeout=0.1, threaded=True):
        self._framer = Framer(port=port, threaded=False)
        self._timeout = timeout
        self._threaded = threaded

        self.platform = None
        self.version = None
        self.row_length = None
        self.page_length = None
        self.prog_length = None
        self.max_prog_size = None

        self.local_memory_map = []

        if self._threaded:
            self._runner = threading.Thread(target=self.run, daemon=True)
            self._runner.start()

    def parse_messages(self):
        messages = []
        while not self._framer.is_empty():
            messages.append(self._framer.rx())

        for message in messages:
            self._parse_message(message)

    def _parse_message(self, msg):
        command = msg[0]
        if command == READ_PLATFORM:
            platform = ''
            for c in msg[1:]:
                platform += chr(c)
            self.platform = platform
            logger.debug('platform set: {}'.format(self.platform))

        elif command == READ_VERSION:
            version = ''
            for c in msg[1:]:
                version += chr(c)
            self.version = version
            logger.debug('version set: {}'.format(self.version))

        elif command == READ_ROW_LEN:
            self.row_length = msg[1] + (msg[2] << 8)
            logger.debug('row length set: {}'.format(self.row_length))

        elif command == READ_PAGE_LEN:
            self.page_length = msg[1] + (msg[2] << 8)
            logger.debug('page length set: {}'.format(self.page_length))

        elif command == READ_PROG_LEN:
            self.prog_length = msg[1] + (msg[2] << 8)
            logger.debug('program length set: {}'.format(self.prog_length))

            self.local_memory_map = [0xffffff] * (0x200 * self.prog_length >> 1)

        elif command == READ_MAX_PROG_SIZE:
            self.max_prog_size = msg[1] + (msg[2] << 8)
            logger.debug('max programming size set: {}'.format(self.max_prog_size))

        elif command == READ_ADDR:
            mem = msg[1:]
            width_in_bytes = 4

            elements = []
            while len(mem) > 0:
                elements.append(mem[:width_in_bytes])
                mem = mem[width_in_bytes:]

            prog_mem = []
            for e in elements:
                memory = 0
                for i, num in enumerate(e):
                    memory += num << (i * 8)
                prog_mem.append(memory)

            address = prog_mem[0]
            value = prog_mem[1]

            if self.local_memory_map:
                self.local_memory_map[address >> 1] = value

            logger.debug('{:04X}: {:06X}'.format(address, value))

        else:
            logger.warning('command not found: {}'.format(command))

    def query_device(self):
        sleep_between_queries = 0.005

        self.query_platform()
        time.sleep(sleep_between_queries)

        self.query_version()
        time.sleep(sleep_between_queries)

        self.query_row_length()
        time.sleep(sleep_between_queries)

        self.query_page_length()
        time.sleep(sleep_between_queries)

        self.query_prog_length()
        time.sleep(sleep_between_queries)  # extra time to allow memory to catch up

        self.query_max_prog_size()
        time.sleep(0.1)

    def query_platform(self):
        self._framer.tx(READ_PLATFORM)

    def query_version(self):
        self._framer.tx(READ_VERSION)

    def query_row_length(self):
        self._framer.tx(READ_ROW_LEN)

    def query_page_length(self):
        self._framer.tx(READ_PAGE_LEN)

    def query_prog_length(self):
        self._framer.tx(READ_PROG_LEN)

    def query_max_prog_size(self):
        self._framer.tx(READ_MAX_PROG_SIZE)

    def erase_page(self, page_number):
        self._framer.tx([ERASE_PAGE, page_number & 0x00ff, (page_number & 0xff00) >> 8])
        logger.debug('erasing page {}'.format(page_number))
        time.sleep(0.005)  # page erases require 4ms to complete

    def read_row(self, address):
        address &= 0xfffffffe   # must be an even address
        self._framer.tx(
            [
                READ_ADDR,
                (address & 0x000000ff),
                (address & 0x0000ff00) >> 8,
                (address & 0x00ff0000) >> 16,
                (address & 0xff000000) >> 24,
            ]
        )
        time.sleep(0.003)

    def write_row(self, address, data):
        if len(data) != self.row_length:
            raise ValueError('data width does not match row length')

        to_tx = [
            WRITE_ROW,
            (address & 0x000000ff),
            (address & 0x0000ff00) >> 8,
            (address & 0x00ff0000) >> 16,
            (address & 0xff000000) >> 24
        ]

        for d in data:
            to_tx.append(d & 0x000000ff)
            to_tx.append((d & 0x0000ff00) >> 8)
            to_tx.append((d & 0x00ff0000) >> 16)
            to_tx.append((d & 0xff000000) >> 24)

        self._framer.tx(to_tx)

    def write_page(self, address, data):
        map = [0xffffff] * self.max_prog_size

        for i, d in enumerate(data):
            map[i] = d

        to_tx = [
            WRITE_PAGE,
            (address & 0x000000ff),
            (address & 0x0000ff00) >> 8,
            (address & 0x00ff0000) >> 16,
            (address & 0xff000000) >> 24
        ]

        for d in map:
            to_tx.append(d & 0x000000ff)
            to_tx.append((d & 0x0000ff00) >> 8)
            to_tx.append((d & 0x00ff0000) >> 16)
            to_tx.append((d & 0xff000000) >> 24)

        self._framer.tx(to_tx)

    def run(self):
        """
        Receives the serial data into the self._raw buffer
        :return:
        """
        run_once = True
        while run_once or self._threaded:
            self.parse_messages()
            run_once = False

            if self._threaded:
                time.sleep(self._timeout)

if __name__ == '__main__':
    port = serial.Serial('COM20', baudrate=115200)
    controller = Controller(port=port)

    controller.query_device()
    time.sleep(0.1)

    # erase page test
    #controller.erase_page(0x400)

    # read addresses
    #address = 0x000
    #max_address = 0x200
    #while address < controller.prog_length and address < max_address:
    #    logger.debug('{:06X}'.format(address))
    #    controller.read_row(address)
    #    address += 2

    #for i, e in enumerate(controller.local_memory_map[:10]):
    #    logger.info('{:06X}: {:06X}'.format(i, e))

    # double-word write
    # controller.write_row(0x2000, [0x00123456, 0x00987654])

    # write page of data
    controller.write_page(0x2000, [0x00123456, 0x00987654, 0x00321098])
