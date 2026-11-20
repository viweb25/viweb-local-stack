import pytest
from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates


class UnavailableRepository:
    def list_templates(self):
        raise ConnectionError("Repository unavailable")


def test_operation_failure_is_not_converted_to_success():
    with pytest.raises(ConnectionError, match="Repository unavailable"):
        GetFunctionTemplates(UnavailableRepository()).execute()
