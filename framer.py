import threading
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class Framer:
    """
    Frames and De-frames the data
    """
    _START_OF_FRAME = 0xf7
    _END_OF_FRAME = 0x7f
    _ESC = 0xf6
    _ESC_XOR = 0x20

    def __init__(self, port, timeout=0.1, threaded=True):
        self._port = port
        self._timeout = timeout
        self._threaded = threaded

        self._raw = []
        self._messages = []

        if self._threaded:
            self._runner = threading.Thread(target=self.run, daemon=True)
            self._runner.start()

    def tx(self, message):
        """
        Transmit a series of bytes
        :param message: a list of bytes to send
        :return: None
        """
        message = message if isinstance(message, list) else [message]

        length = len(message)
        length_high_byte = (length & 0xff00) >> 8
        length_low_byte = length & 0x00ff

        message_with_length = [length_low_byte, length_high_byte] + message

        sum1, sum2 = self._fletcher16_checksum(message_with_length)
        message_with_length.append(sum1)
        message_with_length.append(sum2)

        message = [self._START_OF_FRAME]

        for b in message_with_length:
            if b in [self._START_OF_FRAME, self._END_OF_FRAME, self._ESC]:
                message.append(self._ESC)
                message.append(b ^ self._ESC_XOR)
            else:
                message.append(b)

        message.append(self._END_OF_FRAME)

        self._port.write(message)

    def rx(self):
        """
        Receive a series of bytes that have been verified
        :return: a series of bytes as a tuple or None if empty
        """
        if not self._threaded:
            self.run()

        try:
            return tuple(self._messages.pop(0))
        except IndexError:
            return None

    def is_empty(self):
        if not self._threaded:
            self.run()

        if len(self._messages) == 0:
            return True
        else:
            return False

    def _parse_raw_data(self):
        """
        Parses the incoming data and determines if it is valid.  Valid
        data gets placed into self._messages
        :return: None
        """
        if self._START_OF_FRAME in self._raw and self._END_OF_FRAME in self._raw:

            while self._raw[0] != self._START_OF_FRAME and len(self._raw) > 0:
                self._raw.pop(0)

            if self._raw[0] == self._START_OF_FRAME:
                self._raw.pop(0)

            eof_index = self._raw.index(self._END_OF_FRAME)
            raw_message = self._raw[:eof_index]
            self._raw = self._raw[eof_index:]

            logger.debug('raw message: {}'.format(raw_message))

            message = self._remove_esc_chars(raw_message)
            logger.debug('message with checksum: {}'.format(message))

            expected_checksum = (message[-1] << 8) | message[-2]
            logger.debug('checksum: {}'.format(expected_checksum))

            message = message[:-2]  # checksum bytes
            logger.debug('message: {}'.format(message))

            sum1, sum2 = self._fletcher16_checksum(message)
            calculated_checksum = (sum2 << 8) | sum1

            if expected_checksum == calculated_checksum:
                message = message[2:]  # remove length
                logger.debug('valid message received: {}'.format(message))
                self._messages.append(message)
            else:
                logger.warning('invalid message received: {}, discarding'.format(message))
                logger.debug('expected checksum: {}, calculated checksum: {}'.format(expected_checksum, calculated_checksum))

        # remove any extra bytes at the beginning
        try:
            while self._raw[0] != self._START_OF_FRAME and len(self._raw) > 0:
                self._raw.pop(0)
        except IndexError:
            pass

    def _fletcher16_checksum(self, data):
        """
        Calculates a fletcher16 checksum for the list of bytes
        :param data: a list of bytes that comprise the message
        :return:
        """
        sum1 = 0
        sum2 = 0

        for i, b in enumerate(data):
            sum1 += b
            sum1 &= 0xff  # Results wrapped at 16 bits
            sum2 += sum1
            sum2 &= 0xff

        logger.debug('sum1: {} sum2: {}'.format(sum1, sum2))

        return sum1, sum2

    def _remove_esc_chars(self, raw_message):
        """
        Removes any escape characters from the message
        :param raw_message: a list of bytes containing the un-processed data
        :return: a message that has the escaped characters appropriately un-escaped
        """
        message = []
        escape_next = False
        for c in raw_message:
            if escape_next:
                message.append(c ^ self._ESC_XOR)
                escape_next = False
            else:
                if c == self._ESC:
                    escape_next = True
                else:
                    message.append(c)

        return message

    def run(self):
        """
        Receives the serial data into the self._raw buffer
        :return:
        """
        run_once = True
        while run_once or self._threaded:
            waiting = self._port.in_waiting
            if waiting > 0:
                for c in self._port.read(waiting):
                    self._raw.append(int(c))

            self._parse_raw_data()
            run_once = False

            if self._threaded:
                time.sleep(self._timeout)


if __name__ == '__main__':
    import serial

    port = serial.Serial('COM20', baudrate=115200)
    framer = Framer(port)

    while True:
        framer.tx([0x00])
        time.sleep(2)
        logger.debug('transmitted')


