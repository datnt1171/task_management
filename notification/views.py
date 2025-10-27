from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from firebase_admin.exceptions import FirebaseError

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_notification_to_self(request):
    """Send notification to current user's devices"""
    title = request.data.get('title')
    body = request.data.get('body')
    data = request.data.get('data', {})
    
    if not title or not body:
        return Response(
            {'error': 'title and body are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    devices = FCMDevice.objects.filter(user=request.user, active=True)
    
    if not devices.exists():
        return Response(
            {'error': 'No active devices found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    message = Message(
        notification=Notification(title=title, body=body),
        data=data,
    )
    
    try:
        response = devices.send_message(message)
        return Response({
            'message': 'Notification sent successfully',
            'success_count': response.success_count if hasattr(response, 'success_count') else 0,
            'failure_count': response.failure_count if hasattr(response, 'failure_count') else 0,
        })
    except FirebaseError as e:
        return Response(
            {'error': f'Firebase error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )