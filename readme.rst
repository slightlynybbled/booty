====================
Purpose
====================

This code base is for creating a bootloader to be utilized for programming microcontroller flash
memory.  This program takes a hex file as the input and will parse that hex file and send it to
the microcontroller bootloader over a serial UART (commonly referred to as a "serial port" or
"COM port").

The sole companion project to this is the `bootypic <http://github.com/slightlynybbled/bootpic>`_ project.
Hopefully, more will follow.

====================
Installation
====================

The easiest way to install this utility is to `pip install booty`.  Alternatively, you may download
this repository, navigate to the root directory of the repository, and `python setup.py install`.

====================
Running
====================

Assuming that this is installed in your root python environment, it will create a command-line utility
which can be directly invoked::

    user ~$ booty --help
    Usage: booty [OPTIONS]

    Options:
      -h, --hexfile PATH      The path to the hex file  [required]
      -p, --port TEXT         Serial port (COMx on Windows devices, ttyXX on Unix-
                              like devices)  [required]
      -b, --baudrate INTEGER  Baud rate in bits/s (defaults to 115200)
      -l, --load              Load the device with the hex file
      -v, --verify            Verify device
      --help                  Show this message and exit.

Of course, to use the package, there are some options that need to be specified.  The two most necessary
options are the `--hexfile` and `--port` options.  Additionally, either the `--load` or `--verify` should
be specified or no action will take place.  This is, after all, a loading and/or verification utility.

If `--load` and `--verify` are specified, the loading will take place first.

A common command to load and verify a device might look like this::

    user ~$ booty -p COM20 --load --verify -hexfile "C:/path/to/my/hex.hex"

The utility will execute a series of commands and result in an output similar to this::

    user ~$ booty -p COM20 --load --verify -hexfile "C:/path/to/my/hex.hex"
    INFO:booty:Using provided hex file at "C:/path/to/my/hex.hex" to load and verify device
    INFO:booty.comm_thread:platform set: dspic33ep32mc204
    INFO:booty.comm_thread:version set: 0.1
    INFO:booty.comm_thread:row length set: 2
    INFO:booty.comm_thread:page length set: 512
    INFO:booty.comm_thread:program length set: 21996
    INFO:booty.comm_thread:max programming size set: 128
    INFO:booty.comm_thread:application start address set: 4096
    INFO:booty.comm_thread:device identification complete
    INFO:booty:loading...
    INFO:booty:device successfully loaded!
    INFO:booty:verifying...
    INFO:booty:device verified!

====================
How it Works
====================

All relevant information is stored on the microcontroller, meaning that the relevant data is stored at compile-time.

The programming takes place in three stages:

 1. device polling - determines what the device is, the command set available, and the page erase and write sizes
 2. erase/program - a series of erase/program cycles which write to the program memory of the microcontroller
 3. read/verify - a complete read and verification of the user memory

Each of these sections can be clearly observed on a logic analyzer.  The capture shown was using a dsPIC33EP32MC204
and takes 17.1s from first byte to last in order to transfer and verify 27.6kB of program data.  There is probably some
room to improve this a bit, but not much without impacting the compiled size of the device bootloader.  Also keep in
mind that flash erase and write cycles have minimum times associated with them.

    .. image:: /docs/img/poll-program-verify.png

A close up of page erase followed by a series of writes (4 writes of 128 instructions for each erase of 512 instructions):

    .. image:: /docs/img/erase-load.png

A close up of reads:

    .. image:: /docs/img/read.png
