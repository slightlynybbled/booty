=====================
Introduction
=====================

----------------------------
What is a Bootloader?
----------------------------

A bootloader is a term that is generally applied to microcontrollers.  It is a special
type of application that will run under certain conditions that allows the actual
application to be erased, updated, verified, or flashed as needed.

There are `more comprehensive explanations <https://electronics.stackexchange.com/questions/27486/what-is-a-boot-loader-and-how-would-i-develop-one>`_
available with a quick search.

----------------------------
What is ``booty``
----------------------------

The ``booty`` protocol focuses on the relatively simple bootloaders required for
microcontroller applications.  If your microcontroller is in the PIC, dsPIC, STM32F,
Atmel, or similar families, then ``booty`` will likely fulfill your requirements.

*****************
The protocol
*****************

``booty``, at its highest level, describes the basic operations of a bootloader
implementation and is not an implementation itself.  Protocol features include:

* serial-device based (UART, RS-232, RS-485, etc)
* device and protocol identification
* device erasure
* loading
* verification
* self protection
* open source!

*********************
The implementation(s)
*********************

On the other hand, since ``booty`` is a protocol, then there are any number of
possible implementations and workflows possible.  For instance, the author has
implemented a server using Python (described by this documentation) along with
a `client implentation in C for the dsPIC series <https://github.com/slightlynybbled/bootypic>`_
of microcontrollers.  The C implementation is small, simple, uses no interrupts,
and has been successfully tested.
