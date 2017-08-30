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


def identify_device():
    # wait for the device to be identified, or wait 10s and exit on fail
    start_time = time.time()
    while not bl.device_identified:
        time.sleep(0.1)
        if time.time() - start_time > 1.0:
            bl.end_thread()
            logger.error('device not responding, check connection and reset device')
            time.sleep(0.1)     # time to end the thread
            return False

    return True


def load(hex_file_path):
    hp = HexParser(hex_file_path)

    if not bl.device_identified:
        if not identify_device():
            return False

    # calculate some useful constants
    prog_ops_per_page = int(bl.page_length / bl.max_prog_size)
    highest_prog_address = bl.prog_length - bl.page_length
    last_prog_page = highest_prog_address & bitwise_not(bl.page_length - 1)

    # erase first page, program first page
    address = 0
    bl.erase_page(address)
    logger.debug('erasing first page...')

    for i in range(prog_ops_per_page):
        row_data = [hp.get_opcode(addr) for addr in range(bl.max_prog_size * 2) if addr % 2 == 0]

        logger.debug('writing first page...')
        bl.write_max(address + len(row_data) * i, row_data)

    # erase application start address to uC end address
    address = bl.app_start_addr
    while address < last_prog_page:
        bl.erase_page(address)
        logger.debug('erasing {} page...'.format(hex(address)))

        for i in range(prog_ops_per_page):
            row_data = [hp.get_opcode(addr + address) for addr in range(bl.max_prog_size * 2) if addr % 2 == 0]

            logger.debug('writing to {}...'.format(hex(address)))

            bl.write_max(address, row_data)

            address += bl.max_prog_size << 1

    # wait for all transmissions are complete
    while bl.busy:
        time.sleep(0.2)
        logger.info('erase/write operations remaining: {}'.format(bl.transactions_remaining))

    logger.info('loading complete!')

    return True


def verify(hex_file_path):
    hp = HexParser(hex_file_path)

    highest_prog_address = bl.prog_length - bl.page_length

    # read entire program memory
    address = 0
    while address < highest_prog_address:
        logger.debug('reading address {:06X}'.format(address))
        bl.read_page(address)

        address += bl.max_prog_size

    # wait for transmissions to complete
    while bl.busy:
        time.sleep(0.2)
        logger.info('flash read operations remaining: {}'.format(bl.transactions_remaining))

    addresses = [a for a in range(bl.app_start_addr, highest_prog_address) if (a % 2) == 0]
    memory = [bl.get_opcode(a) & 0xffffff for a in range(bl.app_start_addr, highest_prog_address) if (a % 2) == 0]
    hex_file = [hp.get_opcode(a) & 0xffffff for a in range(bl.app_start_addr, highest_prog_address) if (a % 2) == 0]

    # check each location in application memory
    for a, m, h in zip(addresses, memory, hex_file):
        if m != h:
            logger.error('address {}: device value "{}" does not match hex value "{}"'.format(a, m, h))
            return False

    logger.info('verification complete')
    return True


if __name__ == '__main__':
    hex_path = 'C:/_code/libs/blink.X/dist/default/production/blink.X.production.hex'

    identify_device()
    load(hex_path)
    verify(hex_path)

    bl.end_thread()
    time.sleep(1.0)     # time for thread to end itself
