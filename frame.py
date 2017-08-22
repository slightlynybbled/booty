import threading
import time
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Framer:
    START_OF_FRAME = 0xf7
    END_OF_FRAME = 0x7f
    ESC = 0xf6
    ESC_XOR = 0x20

    def __init__(self, port, timeout=0.1, threaded=True):
        self.port = port
        self.timeout = timeout
        self.threaded = threaded

        self.raw = []
        self.messages = []

        if self.threaded:
            self.runner = threading.Thread(target=self.run, daemon=True)
            self.runner.start()

    def tx(self, message):
        self.port.write([self.START_OF_FRAME])

        sum1, sum2 = self.fletcher16_checksum(message)
        message.append(sum1)
        message.append(sum2)

        for b in message:
            if b in [self.START_OF_FRAME, self.END_OF_FRAME, self.ESC]:
                self.port.write([self.ESC])
                self.port.write([b ^ self.ESC_XOR])
            else:
                self.port.write([b])

        self.port.write([self.END_OF_FRAME])

    def parse_raw_data(self):
        if self.START_OF_FRAME in self.raw and self.END_OF_FRAME in self.raw:

            while self.raw[0] != self.START_OF_FRAME and len(self.raw) > 0:
                self.raw.pop(0)

            if self.raw[0] == self.START_OF_FRAME:
                self.raw.pop(0)

            eof_index = self.raw.index(self.END_OF_FRAME)
            raw_message = self.raw[:eof_index]
            self.raw = self.raw[eof_index:]

            logger.debug('raw message: {}'.format(raw_message))

            message = self.remove_esc_chars(raw_message)
            logger.debug('message with checksum: {}'.format(message))

            expected_checksum = (message[-1] << 8) | message[-2]
            logger.debug('checksum: {}'.format(expected_checksum))

            message = message[:-2]
            logger.debug('message: {}'.format(message))

            sum1, sum2 = self.fletcher16_checksum(message)
            calculated_checksum = (sum2 << 8) | sum1

            if expected_checksum == calculated_checksum:
                logger.debug('valid message received: {}'.format(message))
                self.messages.append(message)
            else:
                logger.warning('invalid message received: {}, discarding'.format(message))
                logger.debug('expected checksum: {}, calculated checksum: {}'.format(expected_checksum, calculated_checksum))

        # remove any extra bytes at the beginning
        try:
            while self.raw[0] != self.START_OF_FRAME and len(self.raw) > 0:
                self.raw.pop(0)
        except IndexError:
            pass

    def fletcher16_checksum(self, data):
        sum1 = 0
        sum2 = 0

        for i, b in enumerate(data):
            sum1 += b
            sum1 &= 0xff  # Results wrapped at 16 bits
            sum2 += sum1
            sum2 &= 0xff

        logger.debug('sum1: {} sum2: {}'.format(sum1, sum2))

        return sum1, sum2

    def remove_esc_chars(self, raw_message):
        message = []
        escape_next = False
        for c in raw_message:
            if escape_next:
                message.append(c ^ self.ESC_XOR)
                escape_next = False
            else:
                if c == self.ESC:
                    escape_next = True
                else:
                    message.append(c)

        return message

    def run(self):
        run_once = True
        while run_once or self.threaded:
            waiting = self.port.in_waiting
            if waiting > 0:
                for c in self.port.read(waiting):
                    self.raw.append(int(c))

            self.parse_raw_data()
            run_once = False

            if self.threaded:
                time.sleep(self.timeout)


if __name__ == '__main__':
    import serial

    port = serial.Serial('COM20', baudrate=115200)
    framer = Framer(port)

    while True:
        framer.tx([0x00, 0x00])
        time.sleep(2)
        logger.debug('transmitted')


