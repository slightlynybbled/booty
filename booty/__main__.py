import logging
import time
import click
from booty.util import create_serial_port, create_blt, load_hex, verify_hex

logger = logging.getLogger('booty')
logging.basicConfig(level=logging.INFO)


@click.command()
@click.option('--hexfile', '-h', required=True, help='The path to the hex file', type=click.Path())
@click.option('--port', '-p', required=True, help='Serial port (COMx on Windows devices, ttyXX on Unix-like devices)')
@click.option('--baudrate', '-b', default=115200, help='Baud rate in bits/s (defaults to 115200)')
@click.option('--load', '-l', is_flag=True, help='Load the device with the hex file')
@click.option('--verify', '-v', is_flag=True, help='Verify device')
def main(hexfile, port, baudrate, load, verify):
    intro_string = 'Using provided hex file at "{}"'.format(hexfile)

    if load and verify:
        intro_string += ' to load and verify device'
    elif load:
        intro_string += ' to load device'
    elif verify:
        intro_string += ' to verify device'
    else:
        logger.error('neither "--load" nor "--verify" were specified, no operations will be performed')
        return

    logger.info(intro_string)

    sp = create_serial_port(port, baudrate)
    blt = create_blt(sp)

    # allow time for threads and hardware to spin up
    time.sleep(0.5)

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
