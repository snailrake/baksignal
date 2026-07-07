import enum


class FuelType(str, enum.Enum):
    ai92 = "92"
    ai95 = "95"
    diesel = "dt"


class Availability(str, enum.Enum):
    yes = "yes"
    no = "no"
    unknown = "unknown"


class QueueLevel(str, enum.Enum):
    none = "none"
    small = "small"
    medium = "medium"
    large = "large"
    unknown = "unknown"


class SourceType(str, enum.Enum):
    user = "user"
    admin = "admin"
    public_news = "public_news"
    imported = "imported"


class StationVerificationStatus(str, enum.Enum):
    active = "active"
    needs_review = "needs_review"
    hidden = "hidden"
    closed = "closed"
