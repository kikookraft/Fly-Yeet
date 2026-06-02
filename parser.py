import gui
import os
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ZoneType(str, Enum):
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Color(BaseModel):
    r: int = Field(..., ge=0, le=255)
    g: int = Field(..., ge=0, le=255)
    b: int = Field(..., ge=0, le=255)


class Postition(BaseModel):
    x: int = Field(..., ge=-50, le=50)
    y: int = Field(..., ge=-50, le=50)


class Hub(BaseModel):
    name: str
    color: Color
    max_drones: int
    zone_type: ZoneType
    position: Postition


class Connection(BaseModel):
    from_hub: Hub
    to_hub: Hub
    max_link_capacity: int = Field(..., gt=0)
