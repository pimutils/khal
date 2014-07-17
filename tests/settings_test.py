from khal.settings import get_config

PATH = __file__.rsplit('/', 1)[0] + '/configs/'


class TestSettings(object):
    def test_simple_config(self):
        config = get_config(PATH + 'simple.conf')
        assert config == 0
