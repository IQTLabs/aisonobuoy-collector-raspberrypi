"""
Test module for pibackbone.
@author: Charlie Lewis
"""
from pibackbone.main import PiBackbone


def test_initial_question():
    instance = PiBackbone()
    instance.initial_question()
