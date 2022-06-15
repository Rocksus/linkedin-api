from datetime import datetime
from typing import List
from pydantic import BaseModel

class LinkedinActivity(BaseModel):
    actor_urn: str
    actor_type: str
    actor_name: str
    dash_entity_urn: str
    entity_urn: str
    url: str
    caption: str
    post_urn: str
    is_shared: bool
    shared_caption: str
    is_reposted: bool
    is_liked: bool
    is_commented: bool
    comment: str
    timestamp: datetime
    
class LinkedinProfileActivityData(BaseModel):
    activities: List[LinkedinActivity]