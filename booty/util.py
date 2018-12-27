import logging
import time

from booty.hex import HexParser
from booty.comm_thread import BootLoaderThread
import serial

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_serial_port(port_name, baud_rate=115200):
    return serial.Serial(port_name, baudrate=baud_rate)


def create_blt(port):
    return BootLoaderThread(port)


def bitwise_not(n, width=32):
    return (1 << width) - 1 - n


def identify_device(boot_loader_app, timeout=5.0):
    # wait for the device to be identified, or wait 10s and exit on fail
    start_time = time.time()
    while not boot_loader_app.device_identified:
        time.sleep(0.2)
        boot_loader_app.query_device()

        # when time expires, then exit the program
        if (time.time() - start_time) > timeout:
            boot_loader_app.end_thread()
            logger.error('device not responding, check connection and reset device')
            time.sleep(0.1)  # time to end the thread
            return False

    return True


def erase_device(boot_loader_app):
    logger.info('erasing device...')

    highest_prog_address = boot_loader_app.prog_length - boot_loader_app.page_length
    last_prog_page = highest_prog_address & bitwise_not(boot_loader_app.page_length - 1)

    # erase first page, program first page
    address = 0
    boot_loader_app.erase_page(address)
    logger.debug('erasing first page...')

    address = boot_loader_app.app_start_addr
    while address < last_prog_page:
        boot_loader_app.erase_page(address)
        logger.debug('erasing {} page...'.format(hex(address)))
        address += boot_loader_app.page_length

    # wait for all transmissions are complete
    while boot_loader_app.busy:
        time.sleep(0.2)
        logger.info('erase operations remaining: {}'.format(boot_loader_app.transactions_remaining))

    logger.info('erasure complete!')

    return True


def load_hex(boot_loader_app, hex_file_path):
    logger.info('loading device...')

    hp = HexParser(hex_file_path)

    # calculate some useful constants
    prog_ops_per_erase = int(boot_loader_app.page_length / boot_loader_app.max_prog_size)
    highest_prog_address = boot_loader_app.prog_length - boot_loader_app.page_length
    last_prog_page = highest_prog_address & bitwise_not(boot_loader_app.page_length - 1)

    # erase first page, program first page
    address = 0
    for i in range(prog_ops_per_erase):
        row_data = [hp.get_opcode(addr + (i * boot_loader_app.max_prog_size)) for addr in range(boot_loader_app.max_prog_size * 2) if addr % 2 == 0]
        logger.debug('writing first page...')
        boot_loader_app.write_max(address + len(row_data) * i, row_data)

    address = boot_loader_app.app_start_addr
    while address < last_prog_page:
        row_data = [hp.get_opcode(addr + address) for addr in range(boot_loader_app.max_prog_size * 2) if addr % 2 == 0]

        logger.debug('writing to {}...'.format(hex(address)))

        boot_loader_app.write_max(address, row_data)
        address += boot_loader_app.max_prog_size << 1

    # wait for all transmissions are complete
    while boot_loader_app.busy:
        time.sleep(0.2)
        logger.info('write operations remaining: {}'.format(boot_loader_app.transactions_remaining))

    logger.info('loading complete!')

    return True


def verify_hex(boot_loader_app, hex_file_path, retries=3, whitelist_addresses=(0x000000)):
    okay_so_far = True
    logger.info('reading flash from device...')

    hp = HexParser(hex_file_path)
    highest_prog_address = boot_loader_app.prog_length - boot_loader_app.page_length

    # read entire program memory
    for address in range(0, highest_prog_address, boot_loader_app.max_prog_size):
        logger.debug('reading address {:06X}'.format(address))
        boot_loader_app.read_page(address)

    # wait for transmissions to complete
    while boot_loader_app.busy:
        time.sleep(0.2)
        logger.info('flash read operations remaining: {}'.format(boot_loader_app.transactions_remaining))

    logger.info('verifying....')
    for segment in hp.segments:
        logger.info('verifying segment {}').format(segment)
        for addr in segment:
            if addr in whitelist_addresses:
                logger.debug('address {:06X} is whitelisted, skipping verification.'.format(addr))
                continue

            m = None
            for retry in range(retries):
                m = boot_loader_app.get_opcode(addr)
                if m is not None:
                    break
                logger.debug('address {:06X} not yet loaded'.format(addr))
                time.sleep(0.2)
            if m is None:
                logger.error('aborting verification. Could not read address {:06X}.'.format(addr))
                return False

            m = m & 0xffffff
            h = hp.get_opcode(addr) & 0xffffff
            if m != h:
                logger.error('address {:06X}: device value "{:06X}" does not match hex value "{:06X}"'.format(addr, m, h))
                okay_so_far = False

    logger.info('verification complete!')
    return okay_so_far


if __name__ == '__main__':
    hex_path = 'C:/_code/libs/blink.X/dist/default/production/blink.X.production.hex'

    # todo: specify port using configuration file or command-line arguments
    port = serial.Serial('COM20', baudrate=115200)
    blt = BootLoaderThread(port)

    identify_device(blt)
    load_hex(blt, hex_path)
    verify_hex(blt, hex_path)

    blt.end_thread()
    time.sleep(1.0)  # time for thread to end itself
