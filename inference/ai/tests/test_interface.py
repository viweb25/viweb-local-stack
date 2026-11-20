import pytest
from vi_ml.functions.base import FunctionAI


def test_incomplete_function_cannot_be_instantiated():
    with pytest.raises(TypeError):
        FunctionAI()
