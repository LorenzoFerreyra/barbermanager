from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework import status
from ..utils import (
    IsAdminRole,
    send_barber_invite_email,
)
from ..serializers import (
    GetAdminProfileSerializer,
    UpdateAdminProfileSerializer,
    DeleteAdminProfileSerializer,
    GetAllBarbersSerializer,
    GetAllClientsSerializer,
    InviteBarberSerializer,
    DeleteBarberSerializer,
    CreateBarberAvailabilitySerializer,
    UpdateBarberAvailabilitySerializer,
    DeleteBarberAvailabilitySerializer,
    GetAllAppointmentsSerializer,
)

@extend_schema(
    methods=['GET'],
    responses={200: GetAdminProfileSerializer},
    description="Admin only: Gets all related profile information for authenticated admin.",
)
@extend_schema(
    methods=['PATCH'],
    request=UpdateAdminProfileSerializer,
    responses={200: OpenApiResponse(description="Profile info updated successfully.")},
    description="Admin only: Update information for the authenticated barber's profile.",
)
@extend_schema(
    methods=['DELETE'],
    responses={204: OpenApiResponse(description="Admin deleted successfully.")},
    description="Admin only: Delete the authenticated barber's account.",
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAdminRole])
@parser_classes([JSONParser]) 
def manage_admin_profile(request):
    """
    Admin only: Handles get, update and delete operations for the authenticated admin's profile.

    - GET: Updates general profie information by the authenticated admin.
    - PATCH: Gets all related profile information for authenticated admin.
    - DELETE: Deletes the account of the authenticated admin.
    """
    if request.method == 'GET':
        serializer = GetAdminProfileSerializer(data={}, context={'admin': request.user})
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = UpdateAdminProfileSerializer(data=request.data, context={'admin': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({"detail": "Profile info updated successfully."}, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        serializer = DeleteAdminProfileSerializer(data={}, context={'admin': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    responses={200: GetAllBarbersSerializer},
    description="Admin only: Returns all barbers registered and their data .",
)
@api_view(['GET'])
@permission_classes([IsAdminRole])
@parser_classes([JSONParser]) 
def get_all_barbers(request):
    """
    Admin only: Returns all barbers registered and their data 
    """
    serializer = GetAllBarbersSerializer(data={}, instance={}) 
    serializer.is_valid(raise_exception=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    responses={200: GetAllClientsSerializer},
    description="Admin only: Returns all clients registered and their data .",
)
@api_view(['GET'])
@permission_classes([IsAdminRole])
@parser_classes([JSONParser]) 
def get_all_clients(request):
    """
    Admin only: Returns all clients registered and their data 
    """
    serializer = GetAllClientsSerializer(data={}, instance={}) 
    serializer.is_valid(raise_exception=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    methods=['GET'],
    responses={200: GetAllAppointmentsSerializer},
    description="Admin only: Get all appointments present in the system.",
)
@api_view(['GET'])
@permission_classes([IsAdminRole])
def get_all_appointments(request):
    """
    Admin only: Get all appointments present in the system
    """
    serializer = GetAllAppointmentsSerializer(data={}, instance={})
    serializer.is_valid(raise_exception=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    methods=['POST'],
    request=InviteBarberSerializer,
    responses={201: OpenApiResponse(description="Barber invited successfully.")},
    description="Admin only: Invite a barber by email. Sends a link with encoded email (uid).",
)
@api_view(['POST'])
@permission_classes([IsAdminRole])
@parser_classes([JSONParser]) 
def invite_barber(request):
    """
    Admin only: Invite a barber by email. Sends a link with encoded email (uid).
    """
    serializer = InviteBarberSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    barber = serializer.save()

    uid = urlsafe_base64_encode(force_bytes(barber.pk))
    token = default_token_generator.make_token(barber)
    send_barber_invite_email(barber.email, uid, token, settings.FRONTEND_URL)

    return Response({'detail': 'Barber invited successfully.'}, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['DELETE'],
    responses={204: OpenApiResponse(description="Barber deleted successfully.")},
    description="Admin only: Deletes a barber by ID using the serializer.",
)
@api_view(['DELETE'])
@permission_classes([IsAdminRole])
def delete_barber(request, barber_id):
    """
    Admin only: Deletes a barber by ID using the serializer
    """
    serializer = DeleteBarberSerializer(data={"id": barber_id})
    serializer.is_valid(raise_exception=True)
    serializer.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    methods=['POST'],
    request=CreateBarberAvailabilitySerializer,
    responses={201: OpenApiResponse(description="Availability created successfully.")},
    description="Admin only: Creates an availability for the selected barber.",
)
@api_view(['POST'])
@permission_classes([IsAdminRole])
@parser_classes([JSONParser]) 
def create_barber_availability(request, barber_id):
    """
    Admin only: Creates an availability for the selected barber.
    """
    serializer = CreateBarberAvailabilitySerializer(data=request.data, context={'barber_id': barber_id})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    return Response({"detail": "Availability created successfully."}, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['PATCH'],
    request=UpdateBarberAvailabilitySerializer,
    responses={200: OpenApiResponse(description="Availability updated successfully.")},
    description="Admin only: Edit the details (date/slots) of a given availability.",
)
@extend_schema(
    methods=['DELETE'],
    responses={204: OpenApiResponse(description="Availability deleted successfully.")},
    description="Admin only: Remove a given availability.",
)
@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAdminRole])
@parser_classes([JSONParser]) 
def manage_barber_availability(request, barber_id, availability_id):
    """
    Admin only: Handles update and delete operations for a specific availability by the selected barber.

    - PATCH: Edit the details (date/slots) of a given availability.
    - DELETE: Remove a given availability.
    """
    if request.method == 'PATCH':
        serializer = UpdateBarberAvailabilitySerializer(data=request.data, context={'barber_id': barber_id, 'availability_id': availability_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({"detail": "Availability updated successfully."}, status=status.HTTP_200_OK)
    
    
    elif request.method == 'DELETE':
        serializer = DeleteBarberAvailabilitySerializer(data={}, context={'barber_id': barber_id, 'availability_id': availability_id})
        serializer.is_valid(raise_exception=True)
        serializer.delete() 
        
        return Response(status=status.HTTP_204_NO_CONTENT)
