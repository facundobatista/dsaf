# Distributed node

All this is about the distributed nodes that handle sensors or actuators.

## How to use

Push files into the microcontroller:

    fades -d adafruit-ampy -x ampy --port /dev/ttyUSB0 --baud 115200 put src/

If it's the very first time with this microcontroller, also copy the entry point:

    fades -d adafruit-ampy -x ampy --port /dev/ttyUSB0 --baud 115200 put main.py

Connect to the micro to check how it goes:

    screen -h 1000 /dev/ttyUSB0 115200

It should drop you into a REPL, you may need to Ctrl-C; leaving the REPL (Ctrl-D) will soft reboot the micro.
