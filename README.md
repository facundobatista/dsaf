# Distributed Sensors and Actuators Framework

The primary objective of this Framework is to enable the distribution of sensors throughout a facility, regardless of its size (such as a machine or a house), while maximizing the simplicity of sensor installation and data collection.

The Framework comprises three types of nodes (explained in detail below):

1. Manager Node: This central node serves as the main administrative interface for a human operator. It allows the operator to manage all distributed sensors, inspect their data, and visualize information. The manager node typically runs on a desktop or headless computer and can be accessed through an API by third-party tools or via its web interface.

2. Sensor Nodes: These nodes are responsible for generating and transmitting information. Multiple sensor nodes are deployed, each consisting of a specific sensor connected to a customized ESP32 system. The ESP32 system is equipped with the "distributed" part of the Framework.

3. Configurator Node: This node is responsible for configuring the network connection of the sensors. It is a single node implemented as an ESP32 hardware device that exposes a known network. The human operator can connect to the configurator node to set the "facility WiFi parameters." The configurator node then provides this information to the sensors at a specific time.

FIXME [Graph illustrating the Framework's structure]


## Functionality provided by the central management node includes:

- Viewing the list of active sensors, their status, and reported data history.
- Managing sensors by changing the code that handles them, pinging the nodes, and requesting data refresh.
- Providing an elegant visualization of the reported information (similar to "Grafana").
- Offering an API to allow third-party applications to consume the information.
- Monitoring the status and health of the configurator node.


## Key features of each sensor node:

- Automatic reporting of the node's "health" status, battery level, server ping time, etc.
- Periodic execution of the code that handles the sensor, returning multiple data points to the central node.
- Ability to receive and "hot swap" Python code specific to the sensor's use.
- Support for robust rebooting, triggered by battery changes or other reasons.
- Initiating communication with the configurator node when in "blank started" mode or during the first two seconds after reboot.
- Status information is conveyed through LEDs near the sensor. The LEDs display the following indications:

    | Green LED | Blue LED | Meaning |
    | --- | --- | --- |
    | Off | Off | No power; everything is broken, life is bad, world will end |
    | Full on | Off | Hardware booted successfully; Framework started |
    | Short blink every 5 seconds | Off | Working normally; server communication is fine |
    | 300 ms square waveform blink | Off | Configurator detected; actively working with it |
    | 1.5 s square waveform blink | Short N times blinks every 3 seconds | N=1: No configuration; N=2: No network or no response from server |
    | 1.5 s square waveform blink | Full on | Complex error; full details reported to the central node |
    | 2 s square waveform blink | 2 s square waveform blink | Battery critically low |

FIXME [Graph illustrating the sensor node's cycle]

## Key features of the configurator node:

- Exposes a well-known WiFi network and accepts connections on port 80 (for humans) and other ports (for sensors).
- Pressing a button enables WiFi and triggers the configurator node to enter "listening mode." If there is no interaction with the device for 5 seconds, it returns to "rest mode."
- Provides a user-friendly web page accessible via the device's WiFi network. The operator can connect their laptop to the device's WiFi and use a browser to access the web page.
- Through the web page, the operator can:
    - Configure the system, including the network to connect to (with password) and the IP/name of the central node, among other settings.
    - Access a history of device interactions and related information for each device.
- The sensor node can retrieve essential configuration information via the API, enabling it to communicate with the central node (primarily network name/password and central node domain name or IP). In the future, additional parameters such as port and encryption tokens may be included.
- A green LED on the configurator node provides the following information:
    - Off: Rest mode
    - Full on: Listening mode
    - Fast blink: Communication with a sensor; returns to listening mode if successful; otherwise, enters a 5-times 1-second square waveform blinking sequence before returning to listening mode.

FIXME [Graph illustrating the configurator node's cycle]


## The setup process for adding a new sensor node to the network is as follows:
    - Power up the sensor node and wait for the green LED to turn on.
    - Bring the sensor node closer to the configurator node and press its button.
    - Both the sensor and configurator nodes should start blinking.
    - Allow a couple of seconds for the nodes to establish communication.
    - If everything went well...
        - the configurator should display a steady green light 
        - the sensor node should enter "working" mode (a short blink every five seconds)
    - On the other hand, if any issues arise:
        - the configurator should fast blink for some seconds (the operator can connect to the configurator node via a browser to investigate).
        - the sensor node should inform it as possible (see above the status table)

In a future phase, the framework will be extended to include "actuators." While the overall process of establishing bidirectional communication, managing actuator code, and interfacing with humans will remain the same, changes will be made to enable bidirectional payload transfer. Further consideration is required for this extension.


## Licensing

This Framework is free to use for any non-commercial use. Please contact me for different uses.
