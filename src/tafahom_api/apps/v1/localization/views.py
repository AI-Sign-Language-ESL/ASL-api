from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser

from django.db import models
from django.utils import translation
from django.conf import settings

from .models import TranslationKey
from . import serializers
from .services.language_service import LanguageService
from .services.translationkey_service import TranslationKeyService


# ---------------- LANGUAGES ----------------


class LanguageListView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.LanguageListResponseSerializer

    def get(self, request):
        current_language = getattr(request, "LANGUAGE_CODE", "en")
        data = LanguageService.get(current_language=current_language)

        serializer = self.get_serializer(instance=data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SetLanguageView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.SetLanguageSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        language_code = serializer.validated_data["language"]
        translation.activate(language_code)

        if hasattr(request, "session"):
            request.session["django_language"] = language_code  # ✅ FIX

        response_data = {
            "language_code": language_code,
            "direction": "rtl" if language_code == "ar" else "ltr",
            "is_rtl": language_code == "ar",
        }

        response_serializer = serializers.CurrentLanguageResponseSerializer(
            instance=response_data
        )

        response = Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language_code,
            max_age=365 * 24 * 60 * 60,
            path="/",
            httponly=False,
            samesite="Lax",
        )

        return response


class CurrentLanguageView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.CurrentLanguageResponseSerializer

    def get(self, request):
        current_language = getattr(request, "LANGUAGE_CODE", "en")

        data = {
            "language_code": current_language,
            "direction": "rtl" if current_language == "ar" else "ltr",
            "is_rtl": current_language == "ar",
        }

        serializer = self.get_serializer(instance=data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------- TRANSLATIONS ----------------


class BulkTranslationKeyView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        keys = request.data.get("keys")
        language = request.data.get("language", "en")

        # -------------------------------------------------
        # ✅ VALIDATION (required by tests)
        # -------------------------------------------------

        if not isinstance(keys, list) or len(keys) == 0:
            return Response(
                {"detail": "Keys list cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(keys) > 100:
            return Response(
                {"detail": "Too many keys requested."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # ✅ FETCH TRANSLATIONS
        # -------------------------------------------------

        translations = {}
        found_keys = {
            obj.key: obj for obj in TranslationKey.objects.filter(key__in=keys)
        }

        for key in keys:
            obj = found_keys.get(key)

            if not obj:
                # ✅ REQUIRED: missing key → return key itself
                translations[key] = key
            else:
                translations[key] = obj.text_ar if language == "ar" else obj.text_en

        return Response(
            {"translations": translations},
            status=status.HTTP_200_OK,
        )


# ---------------- ADMIN KEYS ----------------


class TranslationKeyListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.TranslationKeyListSerializer
    queryset = TranslationKey.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()

        context = self.request.query_params.get("context")
        if context:
            queryset = queryset.filter(context=context)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(key__icontains=search)
                | models.Q(text_en__icontains=search)
                | models.Q(text_ar__icontains=search)
            )

        return queryset


class TranslationKeyDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.TranslationKeySerializer
    queryset = TranslationKey.objects.all()

    def perform_update(self, serializer):
        instance = serializer.save()
        TranslationKeyService.clear_translation_cache(instance.key)
