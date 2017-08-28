import logging
import time

from hex import HexParser
from bootloaderif import BootLoaderIf
import serial

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def load(hex_file_path):
    port = serial.Serial('COM20', baudrate=115200)

    hp = HexParser(hex_file_path)
    bl = BootLoaderIf(port)

    # wait for the device to be identified, or wait 10s
    start_time = time.time()
    while not bl.device_identified:
        time.sleep(0.1)
        if time.time() - start_time > 10.0:
            bl.end_thread()
            logger.error('device not responding, check connection and reset device')
            return

    bl.end_thread()
    time.sleep(1.0)


if __name__ == '__main__':
    load('C:/_code/libs/blink.X/dist/default/production/blink.X.production.hex')
