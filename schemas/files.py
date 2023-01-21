from pydantic import BaseModel, UUID4
from typing import Optional, Union


class FileUpload(BaseModel):
    keys: Optional[Union[str, UUID4]] = None
    md5: Optional[str] = None
    id: Optional[int] = None
    detail: Optional[str] = None
