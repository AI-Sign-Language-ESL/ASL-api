from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from .models import Meeting, Participant
from .services import generate_meeting_code


# =====================================================
# CREATE MEETING
# =====================================================
class CreateMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, "role", None) != "organization":
            return Response(
                {"error": "Only organizations can create meetings"},
                status=status.HTTP_403_FORBIDDEN,
            )

        code = generate_meeting_code()

        with transaction.atomic():
            meeting = Meeting.objects.create(
                title=request.data.get("title", "Meeting"),
                host=request.user,
                meeting_code=code,
            )

            Participant.objects.create(
                user=request.user,
                meeting=meeting,
                role="host",
            )

        return Response(
            {
                "meeting_id": str(meeting.id),
                "meeting_code": meeting.meeting_code,
                "title": meeting.title,
            },
            status=status.HTTP_201_CREATED,
        )


# =====================================================
# JOIN MEETING
# =====================================================
class JoinMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        try:
            meeting = Meeting.objects.get(meeting_code=code, is_active=True)
        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        participant, _ = Participant.objects.get_or_create(
            user=request.user,
            meeting=meeting,
            defaults={"role": "participant"},
        )

        return Response(
            {
                "message": "Joined successfully",
                "role": participant.role,
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# LEAVE MEETING
# =====================================================
class LeaveMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        try:
            meeting = Meeting.objects.get(meeting_code=code)
        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted, _ = Participant.objects.filter(
            user=request.user,
            meeting=meeting
        ).delete()

        if deleted == 0:
            return Response(
                {"error": "You are not part of this meeting"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "Left successfully"})


# =====================================================
# LIST PARTICIPANTS
# =====================================================
class ParticipantsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        try:
            meeting = Meeting.objects.get(meeting_code=code)
        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        participants = meeting.participants.select_related("user")

        data = [
            {
                "id": p.user.id,
                "username": p.user.username,
                "role": p.role,
            }
            for p in participants
        ]

        return Response({"participants": data})


# =====================================================
# END MEETING
# =====================================================
class EndMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        try:
            meeting = Meeting.objects.get(meeting_code=code)
        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if meeting.host != request.user:
            return Response(
                {"error": "Only host can end meeting"},
                status=status.HTTP_403_FORBIDDEN,
            )

        meeting.is_active = False
        meeting.save()

        return Response({"message": "Meeting ended"})