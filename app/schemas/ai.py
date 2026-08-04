from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = "Customer browsing Walters Opticians catalog"

class ChatResponse(BaseModel):
    reply: str