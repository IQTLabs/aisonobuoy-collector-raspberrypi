import os

from sense_app import Telemetry  # pylint: disable=no-name-in-module


def test_telemetry():

    class MockEvent:

        def __init__(self):
            self.action = 'released'
            self.direction = 'middle'


    class MockStick:

        def get_events(self):
            return [MockEvent()]


    class MockSense:

        def __init__(self):
            self.stick = MockStick()

        def get_temperature(self):
            return 10

        def get_humidity(self):
            return 10

        def get_pressure(self):
            return 10

        def get_accelerometer_raw(self):
            return {'x': 10, 'y': 10, 'z': 10}

        def get_gyroscope_raw(self):
            return {'x': 10, 'y': 10, 'z': 10}

        def get_compass_raw(self):
            return {'x': 10, 'y': 10, 'z': 10}

        def set_pixel(self, x, y, color):
            pass

        def set_pixels(self, matrix):
            pass


    t = Telemetry('.')
    t.sense = MockSense()
    t.MINUTES_BETWEEN_WAKES = 1.1
    t.MINUTES_BETWEEN_WRITES = 2
    t.main(False)
