import enum


class ShelfType(enum.Enum):
    personal = "personal"
    shared = "shared"
    temporary = "temporary"


class ShelfRole(enum.Enum):
    editor = "editor"
    owner = "owner"
    viewer = "viewer"


class ReadingStatus(enum.Enum):
    reading = "reading"
    finished = "finished"
    paused = "paused"
    want_to_read = "want_to_read"
