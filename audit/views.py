from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django_filters import rest_framework as django_filters
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, EventType, SecurityEvent, Severity
from .permissions import IsSecurityAuditor
from .serializers import SecurityEventSerializer
from .services import log_event, verify_chain


# ---------------------------------------------------------------------
# EVENT LIST (read-only)
# ---------------------------------------------------------------------
class SecurityEventFilter(django_filters.FilterSet):
    date_from = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gte")
    date_to = django_filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="lte")
    actor = django_filters.CharFilter(field_name="actor_username", lookup_expr="iexact")

    class Meta:
        model = SecurityEvent
        fields = ["event_type", "category", "severity", "outcome", "ip_address", "actor", "date_from", "date_to"]


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SecurityEvent.objects.all()
    serializer_class = SecurityEventSerializer
    permission_classes = [IsSecurityAuditor]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SecurityEventFilter
    search_fields = ["actor_username", "path", "target_repr", "ip_address"]
    ordering_fields = ["timestamp", "severity", "event_type"]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        log_event(
            EventType.AUDIT_LOG_VIEWED, request=request,
            details={"view": "events", "filters": dict(request.query_params.items())},
        )
        return response


# ---------------------------------------------------------------------
# DASHBOARD SUMMARY
# ---------------------------------------------------------------------
class SecuritySummaryView(APIView):
    permission_classes = [IsSecurityAuditor]

    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        days = 7
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        events = SecurityEvent.objects.all()
        recent = events.filter(timestamp__gte=last_24h)

        totals = recent.aggregate(
            total=Count("id"),
            login_success=Count("id", filter=Q(event_type=EventType.LOGIN_SUCCESS)),
            login_failed=Count("id", filter=Q(event_type=EventType.LOGIN_FAILED)),
            access_denied=Count("id", filter=Q(event_type=EventType.ACCESS_DENIED)),
            rate_limited=Count("id", filter=Q(event_type=EventType.RATE_LIMITED)),
            alerts=Count("id", filter=Q(category=Category.DETECTION)),
            high_severity=Count("id", filter=Q(severity__in=[Severity.HIGH, Severity.CRITICAL])),
        )

        # 7-day trend of key security signals
        daily = (
            events.filter(timestamp__gte=start)
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(
                login_success=Count("id", filter=Q(event_type=EventType.LOGIN_SUCCESS)),
                login_failed=Count("id", filter=Q(event_type=EventType.LOGIN_FAILED)),
                access_denied=Count("id", filter=Q(event_type=EventType.ACCESS_DENIED)),
                alerts=Count("id", filter=Q(category=Category.DETECTION)),
            )
        )
        by_day = {row["day"]: row for row in daily}
        trend = []
        for i in range(days):
            day = (start + timedelta(days=i)).date()
            row = by_day.get(day, {})
            trend.append({
                "date": day.isoformat(),
                "login_success": row.get("login_success", 0),
                "login_failed": row.get("login_failed", 0),
                "access_denied": row.get("access_denied", 0),
                "alerts": row.get("alerts", 0),
            })

        by_category = list(
            recent.values("category").annotate(count=Count("id")).order_by("-count")
        )
        top_failed_ips = list(
            recent.filter(event_type__in=[EventType.LOGIN_FAILED, EventType.ACCESS_DENIED])
            .exclude(ip_address=None)
            .values("ip_address")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        top_failed_users = list(
            recent.filter(event_type=EventType.LOGIN_FAILED)
            .values("actor_username")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        recent_alerts = SecurityEventSerializer(
            events.filter(category=Category.DETECTION)[:10], many=True
        ).data

        log_event(EventType.AUDIT_LOG_VIEWED, request=request, details={"view": "summary"})
        return Response({
            "generated_at": now.isoformat(),
            "last_24h": totals,
            "trend_7d": trend,
            "by_category_24h": by_category,
            "top_failed_ips_24h": top_failed_ips,
            "top_failed_usernames_24h": top_failed_users,
            "recent_alerts": recent_alerts,
        })


# ---------------------------------------------------------------------
# INTEGRITY CHECK (hash chain)
# ---------------------------------------------------------------------
class AuditIntegrityView(APIView):
    permission_classes = [IsSecurityAuditor]

    def get(self, request):
        ok, checked, bad_id = verify_chain()
        log_event(
            EventType.AUDIT_LOG_VIEWED, request=request,
            severity=Severity.INFO if ok else Severity.CRITICAL,
            details={"view": "integrity", "intact": ok, "first_invalid_id": bad_id},
        )
        return Response({"intact": ok, "records_checked": checked, "first_invalid_id": bad_id})
