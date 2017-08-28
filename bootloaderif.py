import logging
import threading
import time

import serial
from framer import Framer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

READ_PLATFORM = 0x00
READ_VERSION = 0x01
READ_ROW_LEN = 0x02
READ_PAGE_LEN = 0x03
READ_PROG_LEN = 0x04
READ_MAX_PROG_SIZE = 0x05
READ_APP_START_ADDRESS = 0x07

ERASE_PAGE = 0x10
ERASE_ALL = 0x11

READ_ADDR = 0x20
READ_PAGE = 0x21

WRITE_ROW = 0x30
WRITE_MAX = 0x31


class BootLoaderIf:
    def __init__(self, port, timeout=0.1, threaded=True):
        self._framer = Framer(port=port, threaded=False)
        self._timeout = timeout
        self._threaded = threaded

        self.transmit_queue = []

        self.platform = None
        self.version = None
        self.row_length = None
        self.page_length = None
        self.prog_length = None
        self.max_prog_size = None
        self.app_start_addr = None

        self.device_identified = False

        self.local_memory_map = []

        self.end = False

        if self._threaded:
            self._runner = threading.Thread(target=self.run, daemon=True)
            self._runner.start()

        self.query_device()

    @property
    def busy(self):
        if len(self.transmit_queue) > 0:
            return True
        else:
            return False

    def end_thread(self):
        self.end = True
        logger.info('ending bootloader interface thread...')

    def add_to_queue(self, action, time_to_wait):
        logger.debug('adding to tx queue: {}'.format(action))
        self.transmit_queue.append(
            (action, time_to_wait)
        )

        logger.debug('current transmit queue:')
        for m in self.transmit_queue:
            logger.debug('\t{}'.format(m))

    def service_tx_queue(self):
        if len(self.transmit_queue) > 0:
            action, time_to_wait = self.transmit_queue.pop(0)
            logger.debug('transmitting ({}): {}'.format(time_to_wait, action))
            self._framer.tx(action)

            time.sleep(time_to_wait)

    def parse_messages(self):
        messages = []
        while not self._framer.is_empty():
            messages.append(self._framer.rx())

        for message in messages:
            self._parse_message(message)

        if not self.device_identified:
            if self.platform is not None \
                    and self.version is not None \
                    and self.row_length is not None \
                    and self.page_length is not None \
                    and self.prog_length is not None \
                    and self.max_prog_size is not None \
                    and self.app_start_addr is not None:
                self.device_identified = True
                logger.debug('device identification complete')

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

        elif command == READ_APP_START_ADDRESS:
            self.app_start_addr = msg[1] + (msg[2] << 8)
            logger.debug('application start address set: {}'.format(self.app_start_addr))

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
        self.query_platform()

        self.query_version()
        self.query_row_length()
        self.query_page_length()
        self.query_prog_length()
        self.query_max_prog_size()
        self.query_app_start_address()

    def query_platform(self):
        self.add_to_queue(READ_PLATFORM, self._timeout)

    def query_version(self):
        self.add_to_queue(READ_VERSION, self._timeout)

    def query_row_length(self):
        self.add_to_queue(READ_ROW_LEN, self._timeout)

    def query_page_length(self):
        self.add_to_queue(READ_PAGE_LEN, self._timeout)

    def query_prog_length(self):
        self.add_to_queue(READ_PROG_LEN, self._timeout)

    def query_max_prog_size(self):
        self.add_to_queue(READ_MAX_PROG_SIZE, self._timeout)

    def query_app_start_address(self):
        self.add_to_queue(READ_APP_START_ADDRESS, self._timeout)

    def erase_page(self, address_start):
        self.add_to_queue([ERASE_PAGE, address_start & 0x00ff, (address_start & 0xff00) >> 8], 0.025)
        logger.debug('erasing page addresses {} to {}'.format(address_start, address_start + self.page_length * 2 - 1))

    def read_row(self, address):
        address &= 0xfffffffe   # must be an even address

        self.add_to_queue([
                READ_ADDR,
                (address & 0x000000ff),
                (address & 0x0000ff00) >> 8,
                (address & 0x00ff0000) >> 16,
                (address & 0xff000000) >> 24,
            ],
            0.003
        )

    def write_row(self, address, data):
        if not self.row_length:
            logger.error('row length has not been set, aborting write')
            return

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

        self.add_to_queue(to_tx, 0.010)

    def write_max(self, address, data):
        if not self.max_prog_size:
            logger.error('program size has not been set, aborting write')
            return

        prog_map = [0xffffff] * self.max_prog_size

        for i, d in enumerate(data):
            prog_map[i] = d

        to_tx = [
            WRITE_MAX,
            (address & 0x000000ff),
            (address & 0x0000ff00) >> 8,
            (address & 0x00ff0000) >> 16,
            (address & 0xff000000) >> 24
        ]

        for d in prog_map:
            to_tx.append(d & 0x000000ff)
            to_tx.append((d & 0x0000ff00) >> 8)
            to_tx.append((d & 0x00ff0000) >> 16)
            to_tx.append((d & 0xff000000) >> 24)

        logger.debug('writing maximum length ({}) to program memory'.format(self.max_prog_size))
        self.add_to_queue(to_tx, len(data)/128 * 0.015)

    def run(self):
        """
        Receives the serial data into the self._raw buffer
        :return:
        """
        run_once = True
        while (run_once or self._threaded) and self.end is False:
            self.service_tx_queue()
            self.parse_messages()

            run_once = False

            if self._threaded:
                time.sleep(self._timeout)

        if self._threaded:
            logger.info('bootloader thread complete')


if __name__ == '__main__':
    port = serial.Serial('COM20', baudrate=115200)
    controller = BootLoaderIf(port=port)

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
    #controller.write_max(0x2000, [0x00123456, 0x00987654, 0x00321098])
