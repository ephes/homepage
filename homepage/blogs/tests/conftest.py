import pytest

@pytest.fixture(scope='module')
def test_templ():
    return '''
        {% lorem %}
    '''
