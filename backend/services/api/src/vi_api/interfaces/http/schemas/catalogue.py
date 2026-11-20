from pydantic import BaseModel, ConfigDict


class FunctionTemplate(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)
    id: str
    name: str
    stage: str
    config_schema: dict
