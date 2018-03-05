import sys
import os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

from bot import aqi_to_concentration


def equal(a, b):
    return abs(a - b) <= 1


def test_aqi_to_concentration():
    assert equal(aqi_to_concentration(42), 10)
    assert equal(aqi_to_concentration(65), 19)
    assert equal(aqi_to_concentration(109), 39)
    assert equal(aqi_to_concentration(136), 50)
    assert equal(aqi_to_concentration(152), 60)
    assert equal(aqi_to_concentration(173), 100)
    assert equal(aqi_to_concentration(228), 178)
    assert equal(aqi_to_concentration(255), 206)
    assert equal(aqi_to_concentration(300), 250)
    assert equal(aqi_to_concentration(390), 340)
    assert equal(aqi_to_concentration(434), 401)
    assert equal(aqi_to_concentration(500), 500)
