from pydantic import BaseModel
from typing import Optional

class FileBrowserHookPayload(BaseModel):
    filePath: str
    username: Optional[str] = None
    event: Optional[str] = None
