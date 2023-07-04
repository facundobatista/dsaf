# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

from machine import ADC, Pin


class ExampleSensorManager:
    """Example class for a sensor manager.

    It will be instantiated once, passing some config, and then called .get()
    every second; the returned information from here will be JSON-encoded and
    sent to the Central Manager node.
    """

    def __init__(self, config):
        # XXX: the sensor should have a set of inputs passed by the framework, it should
        # not access hardware directly
        self.adc = ADC(0)
        self.pin = Pin(0, Pin.IN)

    def get(self):
        """Produce information from the sensor manager."""
        return {"button": self._get_button(), "sensor": self._get_adc()}

    def _get_button(self):
        """Return value of the used button."""
        return self.pin.value()

    def _get_adc(self):
        """Return value of the sensor through the ADC."""
        return self.adc.read()
