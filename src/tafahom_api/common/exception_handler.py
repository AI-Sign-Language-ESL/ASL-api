import logging
import traceback

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class APIError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An unexpected error occurred"
    default_code = "error"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "error"),
                "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
            }
        }
    else:
        error_id = id(exc)
        error_trace = traceback.format_exc()

        logger.error(
            f"Unhandled exception [{error_id}]: {exc}\n{error_trace}",
            exc_info=True,
        )

        response_data = {
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
            }
        }

        if not settings.DEBUG:
            response_data["error"]["error_id"] = str(error_id)

        response = Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response