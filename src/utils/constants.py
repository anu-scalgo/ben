"""Application constants and enums."""

from enum import Enum


class PlanTier(str, Enum):
    """Subscription plan tier enum."""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def __lt__(self, other):
        """Compare tiers for plan upgrades."""
        order = {
            PlanTier.FREE: 0,
            PlanTier.BASIC: 1,
            PlanTier.PRO: 2,
            PlanTier.ENTERPRISE: 3,
        }
        return order.get(self, 0) < order.get(other, 0)


class StorageProvider(str, Enum):
    """Storage provider enum."""

    S3 = "s3"
    ORACLE = "oracle"
    WASABI = "wasabi"


class UploadStatus(str, Enum):
    """File upload status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"

