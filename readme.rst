====================
Purpose
====================

This code base is for creating a bootloader to be utilized for programming microcontroller flash
memory.  This program takes a hex file as the input and will parse that hex file and send it to
the microcontroller bootloader over a serial UART (commonly referred to as a "serial port" or
"COM port").

The companion project to this is the `bootypic <http://github.com/slightlynybbled/bootypic>`_ project.
Hopefully, more will follow.  GUI provided at `bootycontrol <http://github.com/slightlynybbled/bootycontrol>`_.

====================
Installation
====================

The easiest way to install this utility is to ``pip install booty``.  Alternatively, you may download
this repository, navigate to the root directory of the repository, and ``python setup.py install``.

This utility is dependent on three currently-maintained python projects:

 * click - for easy command-line utilities
 * intelhex - for easy parsing of hex files
 * pyserial - for UART communication 

====================
Running
====================

Assuming that this is installed in your root python environment, it will create a command-line utility
which can be directly invoked::

    Usage: __main__.py [OPTIONS]

    Options:
      -h, --hexfile PATH      The path to the hex file
      -p, --port TEXT         Serial port (COMx on Windows devices, ttyXX on Unix-
                              like devices)  [required]
      -b, --baudrate INTEGER  Baud rate in bits/s (defaults to 115200)
      -e, --erase             Erase the application space of the device
      -l, --load              Load the device with the hex file
      -v, --verify            Verify device
      -V, --version           Show software version
      --help                  Show this message and exit.

Of course, to use the package, there are some options that need to be specified.  The two most necessary
options are the `--hexfile` and `--port` options.  Additionally, either the `--erase`, `--load`, or `--verify` should
be specified or no action will take place.  This is, after all, a loading and/or verification utility.

Regardless of the order of the input parameters, the order of execution will be erase, load, then verify.

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

-------------------
Programming Sequence
-------------------

All relevant information is stored on the microcontroller, meaning that the relevant data is stored at compile-time.

The programming takes place in three stages:

 1. device identification - determines what the device is, the command set available, and the page erase and write sizes
 2. erasure - erasure of all application-programmable memory
 3. loading - a series of write cycles which write to the program memory of the microcontroller
 4. verify - a series of read cycles and final verification of the user memory

Shown is a complete id/erase/load/verify of a 16k device at 57600bits/s and operating at 12MIPS, which takes 15.8s.
Each section is delimited by the green markers.  This load time could obviously be reduced by running at a faster baud
rate.

    .. image:: https://github.com/slightlynybbled/booty/blob/master/docs/img/id-erase-load-verify.png

-------------------
Threaded Execution
-------------------

At the lowest level, there is a thread which takes commands from higher level software and creates an internal queue which 
is executed in sequence.  This layer will execute simple commands, such as "read flash", "write flash", etc. while also 
ensuring that the protocols, required sizes, and timing constraints are enforced.

At the higher level, the hex file is read and a command set is created for the low-level software.  At various places, there 
are "waits" put in place.  For instance, the high level software might request that the low level software do all of the 
write operations before it moves on to a verification stage.  This is more clear in the source code.

The high-level operations may be found in ``/booty/__main__.py`` and ``/booty/util.py`` while the low-level thread may be 
found in ``/booty/comm_thread.py``.
