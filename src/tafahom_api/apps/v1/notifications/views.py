from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        qs = Notification.objects.filter(user=request.user)
        notifications = []
        for n in qs[:50]:
            notifications.append({
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "read": n.is_read,
                "action_url": n.action_url,
                "created_at": n.created_at.isoformat(),
            })
        return Response(notifications)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            n = Notification.objects.get(id=notification_id, user=request.user)
            n.is_read = True
            n.save(update_fields=["is_read"])
            return Response({"detail": "Marked as read"})
        except Notification.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All marked as read"})


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        try:
            n = Notification.objects.get(id=notification_id, user=request.user)
            n.delete()
            return Response({"detail": "Deleted"})
        except Notification.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class NotificationClearAllView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        count, _ = Notification.objects.filter(user=request.user).delete()
        return Response({"detail": f"Deleted {count} notifications"})
