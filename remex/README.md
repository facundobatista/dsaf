# Remote Executor

Device to control different components in a park (pool, watering, etc.).


## Helpers:

To sync all code to device:
```
./espdev_sync.py main.py src/
```

...or manually:

```
fades -d adafruit-ampy -x ampy --port /dev/ttyUSB0 --baud 115200 ls
fades -d adafruit-ampy -x ampy --port /dev/ttyUSB0 --baud 115200 put main.py




To connect to the device manually:
```
screen -h 1000 /dev/ttyUSB0 115200
```

Add this config to your `.screenrc` to be able to exit screen doing `CTRL-a k`:
```
.screenrc: bind k colon "kill\015"
```

# Specification

The Framework will use two leds and a button to operate; these are already integrated in a development device, so no extra hardware is needed to start to operate.

The leds represents the status of the device, and the button allows special interaction of the user. The rest of user's interaction happens through remote clients.

When booting the device, the Status led will blink fast once and then twice to indicate that the Remex Framework is loaded (don't confuse it with double fast blink done in the Power led by the bootloader).

After booting, if configuration is saved, it will automatically enter into Regular Mode. If configuration is missing, corrupt, or wrong, it will switch to panic mode. From Regular or Panic modes the device can be moved to Configuration Mode by leaving the the button pressed for two seconds.


## Execution Modes

These are the different modes in which the framework can run.


## Regular Mode

This is the normal operation mode of the device. The Power led blinks once every 10 seconds, and the Status led will be always off.

In this mode it mostly will be running software from the user, but the Framework will still communicate regularly with the Management Node (to report device health information, and to receive orders).

Leave the button pressed for two seconds to switch the device to the Configuration Mode.

Note that if the user's software crashes, those errores will be reported to the Management Node but the device will continue to work in Regular Mode.


## Configuration Mode

This is the mode to configure the device. Normally only used on initial setup, or when some configuration needs to be changed (e.g. the WiFi connection parameters).

Leave the button pressed for two seconds to switch the device to this mode. The Power led will slowly blink on and off, and the Status led will remain on.

After switching to this mode the configuration script should be run in the laptop. See below for indications on how to use the script and what it does. When the configuration script connects to the device, the Status led will start blinking.

Once configured, press briefly the button again and the device will go to Regular Mode (or Panic, if configuration is not correct).


## Panic Mode

Something is wrong with the device configuration and can not connect to the Management Node. The Power led quickly blinks on and off (half a second period). The Status led will do a series of fast blinks followed by a pause.

The quantity of fast blinks in the Status led indicates the problem found (listed here with recommended actions to follow):

- 1: no configuration found
    - switch to Configuration Mode (press the button for two seconds) and configure it (see above)

- 2: configuration found but cannot connect to WiFi
    - ensure that the WiFi is working correctly and its range covers the device
    - switch to Configuration Mode (press the button for two seconds) and fix the configuration

- 3: can connect to WiFi but not to the Management Node
    - ensure the router providing WiFi has Internet working properly

Note that if any problem is found in a "normal operation" but the framework can still connect to the Management Node, the device will be in Regular Mode and will just inform the failures to the Management Node.



# How To Use

#


## TODO

- script to connect to node, ask health, sets config (wifi data, and ManagNode location)
- make it work to get out of config; report to the node that is switching (before doing so), connect and report back to the ManagNode
- now in "regular" we should see reports to ManagNode
- this should support reboots
- Implement "orders" (as responses in those reports); first just prints received stuff
- Implement "set time", always returned
- support sending back new software; the device should get it, save it, import it, run "run()" inside
