import logging
import time

from hex import HexParser
from bootloaderif import BootLoaderIf
import serial

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# todo: specify port using configuration file or command-line arguments
port = serial.Serial('COM20', baudrate=115200)
bl = BootLoaderIf(port)


def bitwise_not(n, width=32):
    return (1 << width) - 1 - n


def load(hex_file_path):
    hp = HexParser(hex_file_path)

    # wait for the device to be identified, or wait 10s and exit on fail
    start_time = time.time()
    while not bl.device_identified:
        time.sleep(0.1)
        if time.time() - start_time > 10.0:
            bl.end_thread()
            logger.error('device not responding, check connection and reset device')
            return

    # calculate some useful constants
    prog_ops_per_page = int(bl.page_length / bl.max_prog_size)
    highest_prog_address = bl.prog_length - bl.page_length
    last_prog_page = highest_prog_address & bitwise_not(bl.page_length - 1)

    # erase first page, program first page
    address = 0
    bl.erase_page(address)

    for i in range(prog_ops_per_page):
        row_data = [hp.get_opcode(addr) for addr in range(bl.max_prog_size * 2) if addr % 2 == 0]

        logger.debug('writing {} instructions to {}'.format(
            len(row_data),
            address + len(row_data) * i)
        )

        bl.write_max(address + len(row_data) * i, row_data)

    # erase application start address to uC end address

    # wait for all tranmissions are complete
    while len(bl.transmit_queue) > 0:
        pass

    bl.end_thread()
    time.sleep(1.0)


if __name__ == '__main__':
    load('C:/_code/libs/blink.X/dist/default/production/blink.X.production.hex')
