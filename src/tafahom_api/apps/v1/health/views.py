from django import db
from django.conf import settings
from django.core.cache import caches
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok", "environment": settings.ENVIRONMENT})


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    checks = {}
    overall = True

    checks["database"] = check_database()
    checks["cache"] = check_cache()
    checks["redis"] = check_redis()

    for check_result in checks.values():
        if not check_result["healthy"]:
            overall = False
            break

    return Response(
        {"status": "ready" if overall else "not_ready", "checks": checks},
        status=status.HTTP_200_OK if overall else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def check_database():
    try:
        with db.connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"healthy": True}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_cache():
    try:
        cache = caches["default"]
        cache.set("health_check", "ok", 10)
        value = cache.get("health_check")
        return {"healthy": value == "ok"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_redis():
    try:
        import redis

        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=2,
        )
        r.ping()
        return {"healthy": True}
    except Exception:
        if settings.ENVIRONMENT == "PROD":
            return {"healthy": False, "error": "Redis unavailable"}
        return {"healthy": True}