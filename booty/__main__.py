import logging
import time
import click
from booty.util import create_serial_port, create_blt, erase_device, load_hex, verify_hex
from booty.version import __version__

logger = logging.getLogger('booty')
logging.basicConfig(level=logging.DEBUG)


@click.command()
@click.option('--hexfile', '-h', help='The path to the hex file', type=click.Path())
@click.option('--port', '-p', help='Serial port (COMx on Windows devices, ttyXX on Unix-like devices)')
@click.option('--baudrate', '-b', default=115200, help='Baud rate in bits/s (defaults to 115200)')
@click.option('--erase', '-e', is_flag=True, help='Erase the application space of the device')
@click.option('--load', '-l', is_flag=True, help='Load the device with the hex file')
@click.option('--verify', '-v', is_flag=True, help='Verify device')
@click.option('--version', '-V', is_flag=True, help='Show software version')
def main(hexfile, port, baudrate, erase, load, verify, version):
    if version:
        logger.info('version {}'.format(__version__))
        return

    if not erase and not load and not verify:
        logger.error('no operations specified - exiting')
        return

    sp = create_serial_port(port, baudrate)
    blt = create_blt(sp)

    # allow time for threads and hardware to spin up
    time.sleep(0.1)

    if not blt.device_identified:
        logger.error('device not responding')
        return

    if erase:
        logger.info('erasing the device...')
        result = erase_device(blt)
        if result:
            logger.info('device successfully erased!')
        else:
            logger.warning('device erase failed')

    if load:
        logger.info('loading...')
        result = load_hex(blt, hexfile)
        if result:
            logger.info('device successfully loaded!')
        else:
            logger.warning('device load failed')
    else:
        result = True

    if verify and result:
        logger.info('verifying...')
        result = verify_hex(blt, hexfile)
        if result:
            logger.info('device verified!')
        else:
            logger.warning('device verification failed')

if __name__ == '__main__':
    main()
