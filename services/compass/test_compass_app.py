
import sys
import fake_rpi
from falcon import testing

sys.modules['smbus2'] = fake_rpi.smbus
from compass_app import QMC5883L, MMC5883MA, argument_parser, CompassAPI


def test_argument_parser():
    argument_parser()


def test_heading():
    compass = QMC5883L(declination=-1, calibration=-1)
    app = CompassAPI(compass)
    client = testing.TestClient(app.app)
    result = client.simulate_get('/v1/heading')
    assert 200 == result.status_code  # nosec
    result = client.simulate_get('/v1/0')
    assert 200 == result.status_code  # nosec
    result = client.simulate_get('/wrong')
    assert 404 == result.status_code  # nosec


def test_qmc5883L():
    compass = QMC5883L(declination=0, calibration=0)
    compass.get_heading(calibration=0)


def test_mma5883ma():
    compass = MMC5883MA(declination=0, calibration=0)
    compass.get_heading(calibration=0)
