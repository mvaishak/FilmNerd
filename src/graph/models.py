from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class NodeType(str, Enum):
    DIRECTOR        = "director"
    CINEMATOGRAPHER = "cinematographer"
    EDITOR          = "editor"
    WRITER          = "writer"
    COMPOSER        = "composer"
    FILM            = "film"


class EdgeType(str, Enum):
    COLLABORATED_WITH = "collaborated_with"
    INFLUENCED_BY     = "influenced_by"
    THEMATIC_LINK     = "thematic_link"
    DIRECTED          = "directed"
    SHOT              = "shot"
    EDITED            = "edited"
    WROTE             = "wrote"
    COMPOSED          = "composed"

