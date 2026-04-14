from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from rag_core.models import Organization, OrganizationMember, UsageLedger


@dataclass
class PlanLimits:
    questions: int
    uploads: int
    tokens: int


def membership_for_user(user, organization: Organization | None) -> OrganizationMember | None:
    if not organization:
        return None
    return OrganizationMember.objects.filter(organization=organization, user=user).first()


def role_for_user(user, organization: Organization | None) -> str | None:
    member = membership_for_user(user, organization)
    return member.role if member else None


def user_can_manage_org(user, organization: Organization | None) -> bool:
    return role_for_user(user, organization) in {"owner", "admin"}


def user_can_edit_workspace(user, organization: Organization | None) -> bool:
    return role_for_user(user, organization) in {"owner", "admin", "editor"}


def limits_for_plan(plan: str) -> PlanLimits:
    if plan == "pro":
        return PlanLimits(
            questions=settings.TIER_PRO_DAILY_QUESTIONS,
            uploads=settings.TIER_PRO_DAILY_UPLOADS,
            tokens=settings.TIER_PRO_DAILY_TOKENS,
        )
    if plan == "enterprise":
        return PlanLimits(questions=10_000, uploads=5_000, tokens=5_000_000)
    return PlanLimits(
        questions=settings.TIER_FREE_DAILY_QUESTIONS,
        uploads=settings.TIER_FREE_DAILY_UPLOADS,
        tokens=settings.TIER_FREE_DAILY_TOKENS,
    )


def _used_today(organization: Organization, metric: str) -> int:
    start = timezone.now() - timedelta(days=1)
    used = (
        UsageLedger.objects.filter(organization=organization, metric=metric, created_at__gte=start)
        .aggregate(total=Sum("amount"))
        .get("total")
    )
    return int(used or 0)


def enforce_limit(organization: Organization, metric: str, amount: int = 1) -> None:
    limits = limits_for_plan(organization.plan)
    used = _used_today(organization, metric)
    cap_map = {"question": limits.questions, "upload": limits.uploads, "token": limits.tokens}
    cap = cap_map.get(metric, limits.tokens)
    if used + amount > cap:
        raise RuntimeError(f"Daily {metric} quota reached for the {organization.plan} plan.")


def record_usage(organization: Organization, user, metric: str, amount: int = 1) -> None:
    UsageLedger.objects.create(
        organization=organization,
        user=user,
        metric=metric,
        amount=max(1, int(amount)),
    )
