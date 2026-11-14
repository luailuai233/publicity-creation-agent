from enum import Enum


class ProjectStatus(str, Enum):
    MATERIALS = "MATERIALS"
    INSPIRATION = "INSPIRATION"
    STRATEGY = "STRATEGY"
    EDITOR = "EDITOR"
    EXPORT = "EXPORT"


class MaterialCategory(str, Enum):
    FLOW = "FLOW"
    INTERVIEW = "INTERVIEW"
    SPEECH = "SPEECH"
    PHOTO = "PHOTO"
    NOTE = "NOTE"
    OTHER = "OTHER"


class ParseStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class FactStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CONFLICT = "CONFLICT"
    INVALID = "INVALID"


class FactType(str, Enum):
    TIME = "TIME"
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    ROLE = "ROLE"
    EVENT = "EVENT"
    QUOTE = "QUOTE"
    NUMBER = "NUMBER"
    VIEWPOINT = "VIEWPOINT"


class IssueType(str, Enum):
    MISSING_SOURCE = "MISSING_SOURCE"
    FACT_CONFLICT = "FACT_CONFLICT"
    SIMILAR_EXPRESSION = "SIMILAR_EXPRESSION"
    PRIVACY_RISK = "PRIVACY_RISK"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"
