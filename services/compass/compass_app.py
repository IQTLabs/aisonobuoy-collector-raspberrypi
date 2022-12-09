import argparse
import logging
import math

import bjoern
import falcon
import smbus2
from falcon_cors import CORS

TWO_PI = 2 * math.pi

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


class Compass:

    def __init__(self, address=None, utscale=None, declination=None, calibration=None):
        self.bus = smbus2.SMBus(1)
        self.heading_reading = 'no heading'
        self.address = address
        self.utscale = utscale # scale factor for x/y readings to micro Tesla.
        self.declination = declination
        self.calibration = calibration

    def read_byte(self, adr):  # communicate with compass
        return self.bus.read_byte_data(self.address, adr)

    def read_word(self, adr):
        low = self.bus.read_byte_data(self.address, adr)
        high = self.bus.read_byte_data(self.address, adr+1)
        val = (high << 8) + low
        return val

    def read_word_2c(self, adr):
        val = self.read_word(adr)
        if val >= 0x8000:
            return -((65535 - val)+1)
        return val

    def write_byte(self, adr, value):
        self.bus.write_byte_data(self.address, adr, value)

    def on_get(self, _req, resp, calibration=None):
        if calibration is None:
            calibration = self.calibration
        self.get_heading(calibration=float(calibration))
        resp.text = str(self.heading_reading)
        resp.content_type = falcon.MEDIA_TEXT
        resp.status = falcon.HTTP_200

    def x_y_to_degrees(self, x_out, y_out, calibration):
        heading = math.atan2(y_out, x_out) + self.declination

        if heading < 0:
            heading += TWO_PI
        if heading > TWO_PI:
            heading -= TWO_PI

        # convert from radians to degrees
        heading = (heading * 180) / math.pi
        # calibration is in degrees, offset from compass reading.
        heading = (heading + calibration) % 360
        return heading

    @staticmethod
    def get_heading(calibration):
        return


class QMC5883L(Compass):
    """QMC5883L.

       See https://github.com/keepworking/Mecha_QMC5883L and
       https://datasheet.lcsc.com/lcsc/2012221837_QST-QMC5883L_C976032.pdf.
    """

    def __init__(self, declination, calibration):
        super().__init__(
            address=0x0d, utscale=0.92, declination=declination, calibration=calibration)

    def get_heading(self, calibration):
        self.write_byte(11, 0b00000001)
        self.write_byte(10, 0b00100000)
        self.write_byte(9, 0xD)
        x_offset = -10
        y_offset = 10
        x_out = (self.read_word_2c(0) - x_offset+2) * self.utscale
        y_out = (self.read_word_2c(2) - y_offset+2) * self.utscale
        # must read Z even though not used, else compass won't update because
        # the measurement as considered incomplete.
        _z_out = self.read_word_2c(4)
        self.heading_reading = self.x_y_to_degrees(x_out, y_out, calibration)


class MMC5883MA(Compass):
    """MMC5883MA.

    See https://github.com/adafruit/Adafruit_MMC5883 and
    https://www.mouser.com/datasheet/2/821/MMC5883MA-RevC-1219541.pdf.
    """

    def __init__(self, declination, calibration):
        super().__init__(
            address=0x30, utscale=0.025, declination=declination, calibration=calibration)

    def get_heading(self, calibration):
        self.write_byte(0x0a, 0x01) # continuous measurement at 14Hz
        # read x, y, z and convert to uT
        x_out = (self.read_word(0) - 0x8000) * self.utscale
        y_out = (self.read_word(2) - 0x8000) * self.utscale
        _z_out = self.read_word(4)
        self.heading_reading = self.x_y_to_degrees(x_out, y_out, calibration)


class CompassAPI:

    def __init__(self, compass):
        self.compass = compass
        cors = CORS(allow_all_origins=True)
        self.app = falcon.App(middleware=[cors.middleware])
        r = self.routes()
        for route in r:
            self.app.add_route(self.version()+route, r[route])

    @staticmethod
    def paths():
        return ['/{calibration}', '/heading']

    @staticmethod
    def version():
        return '/v1'

    def routes(self):
        p = self.paths()
        funcs = [self.compass for _ in range(len(p))]
        return dict(zip(p, funcs))

    def main(self):
        logging.info('starting API thread')
        bjoern.run(self.app, '0.0.0.0', 8000)


COMPASS_MAP = {'qmc5883l': QMC5883L, 'mmc5883ma': MMC5883MA}


def argument_parser():
    parser = argparse.ArgumentParser(prog='compass', description='serve compass heading requests')
    parser.add_argument('--compass', choices=sorted(COMPASS_MAP.keys()), default='qmc5883l', help='compass type to use')
    parser.add_argument('--declination', type=float, default=0.48, help='magnetic declination angle in radians to use (location dependant)')
    parser.add_argument('--calibration', type=float, default=0, help='calibration offset from north in degrees')
    return parser


if __name__ == "__main__":
    args = argument_parser().parse_args()
    compass = COMPASS_MAP[args.compass](declination=args.declination, calibration=args.calibration)
    api = CompassAPI(compass=compass)
    api.main()
