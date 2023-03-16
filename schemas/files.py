from typing import Optional, Union

from pydantic import BaseModel, UUID4


class FileUpload(BaseModel):
    """
    Schema for file upload response
    """
    keys: Optional[Union[str, UUID4]] = None
    md5: Optional[str] = None
    id: Optional[int] = None
    detail: Optional[str] = None
