import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from api.models import (
    User, 
    Barber,
    Client, 
    Service, 
    Availability, 
    Appointment, 
    Review, 
    AppointmentStatus, 
    Roles
)

class BarberProfileTest(APITestCase):
    """
    Tests for the barber profile management and service/availability endpoints.
    """
    def setUp(self):
        # Endpoint URLs
        self.login_url = reverse("login_user")
        self.profile_url = reverse("manage_barber_profile")
        self.services_url = reverse("manage_barber_services")
        self.availabilities_url = reverse("get_barber_availabilities")
        self.appointments_url = reverse("get_barber_appointments")
        self.reviews_url = reverse("get_barber_reviews")

        # Create a barber user and a plain client
        self.barber_password = "BarberPass123!"
        self.barber_email = "barber@example.com"
        self.barber_user = Barber.objects.create_user(
            username="barber1",
            email=self.barber_email,
            password=self.barber_password,
            name="Barbone name",
            surname="barb surname",
            is_active=True,
        )

        self.client_user = Client.objects.create_user(
            username="clientUser",
            email="test@email.com",
            password="ClientPass123!",
            name="test name",
            surname="test surname",
            is_active=True,
        )


    def login_as_barber(self):
        """
        Authenticate as the test barber.
        """
        resp = self.client.post(self.login_url, {"username": self.barber_user.username, "password": self.barber_password}, format="json")
        token = resp.data["token"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


    def login_as_client(self):
        """
        Authenticate as the test non-barber client.
        """
        resp = self.client.post(self.login_url, {"username": self.client_user.username, "password": "ClientPass123!"}, format="json")
        token = resp.data["token"]["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


    def test_get_profile_success(self):
        """
        Authenticated barber can get their full profile including services and reviews.
        """
        self.login_as_barber()

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile = response.data["profile"]
        self.assertEqual(profile, self.barber_user.to_dict())
        self.assertEqual(profile['role'], Roles.BARBER.value)


    def test_get_profile_requires_auth_and_barber_role(self):
        """
        Getting profile requires barber authentication; returns 403 for non-barber.
        """
        # Not authenticated at all
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Auth as client, not barber
        self.login_as_client()

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_update_profile_success_partial(self):
        """
        Barber can update part(s) of their profile.
        """
        self.login_as_barber()
        patch = {"name": "Changed1", "username": "Changed2", "description": "Changed3"}
        resp = self.client.patch(self.profile_url, patch, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["detail"], "Profile info updated successfully.")
        self.barber_user.refresh_from_db()
        self.assertEqual(self.barber_user.name, "Changed1")
        self.assertEqual(self.barber_user.username, "Changed2")
        self.assertEqual(self.barber_user.description, "Changed3")


    def test_update_profile_username_unique_constraint(self):
        """
        Username cannot be changed to one in use.
        """
        # Create another barber
        other_barber = Barber.objects.create_user(
            username="barber2",
            email="barber2@example.com",
            password="BarberPass456!",
            name="B2",
            surname="X",
        )
        self.login_as_barber()
        resp = self.client.patch(self.profile_url, {"username": "barber2"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("taken", str(resp.data["detail"]).lower())


    def test_update_profile_requires_at_least_one_field(self):
        """
        Updating profile with no fields returns validation error.
        """
        self.login_as_barber()
        resp = self.client.patch(self.profile_url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("must provide at least one field", str(resp.data["detail"]))


    def test_delete_profile_success(self):
        """
        Barber can delete their profile account.
        """
        self.login_as_barber()
        resp = self.client.delete(self.profile_url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # Account should not exist anymore
        self.assertFalse(Barber.objects.filter(pk=self.barber_user.pk).exists())


    def test_list_services(self):
        """
        Authenticated barber can list all their services.
        """
        Service.objects.create(barber=self.barber_user, name="Cut", price=Decimal("10.99"))
        Service.objects.create(barber=self.barber_user, name="Shave", price=Decimal("7.99"))
        self.login_as_barber()
        resp = self.client.get(self.services_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["services"]), 2)
        self.assertEqual(resp.data["services"][0]["name"], "Cut")


    def test_list_services_barber_only(self):
        """
        Only authenticated barbers may list services.
        """
        resp = self.client.get(self.services_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.login_as_client()
        resp2 = self.client.get(self.services_url)
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)


    def test_create_service_success(self):
        """
        Barber can create a new service with unique name.
        """
        self.login_as_barber()
        data = {"name": "Buzz Cut", "price": "20.50"}
        resp = self.client.post(self.services_url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("Service added successfully", resp.data["detail"])
        service = Service.objects.get(barber=self.barber_user, name="Buzz Cut")
        self.assertEqual(str(service.price), data["price"])


    def test_create_service_duplicate_name_case_insensitive(self):
        """
        Creating service fails if name exists (case-insensitive).
        """
        Service.objects.create(barber=self.barber_user, name="beard trim", price=Decimal("15.00"))
        self.login_as_barber()
        resp = self.client.post(self.services_url, {"name": "Beard Trim", "price": "25.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(resp.data["detail"]))


    def test_update_service_success(self):
        """
        Barber can patch (partial update) a given service.
        """
        service = Service.objects.create(barber=self.barber_user, name="Trim", price=Decimal("9.99"))
        self.login_as_barber()
        url = reverse("manage_barber_service", kwargs={"service_id": service.id})
        resp = self.client.patch(url, {"price": "11.11"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        service.refresh_from_db()
        self.assertEqual(str(service.price), "11.11")


    def test_update_service_name_duplicate(self):
        """
        Cannot update a service's name to one already in use.
        """
        s1 = Service.objects.create(barber=self.barber_user, name="a", price=1)
        s2 = Service.objects.create(barber=self.barber_user, name="b", price=2)
        self.login_as_barber()
        url = reverse("manage_barber_service", kwargs={"service_id": s2.id})
        resp = self.client.patch(url, {"name": "a"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(resp.data["detail"]))


    def test_update_service_requires_field(self):
        """
        Update service requires at least a name or price.
        """
        service = Service.objects.create(barber=self.barber_user, name="Skin", price=10)
        self.login_as_barber()
        url = reverse("manage_barber_service", kwargs={"service_id": service.id})
        resp = self.client.patch(url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at least one field", str(resp.data["detail"]))


    def test_update_service_not_found(self):
        """
        Updating a non-existent service for this barber returns error.
        """
        self.login_as_barber()
        url = reverse("manage_barber_service", kwargs={"service_id": 9999})
        resp = self.client.patch(url, {"price": "5.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not exist", str(resp.data["detail"]))


    def test_delete_service_success(self):
        """
        Barber can delete one of their own services.
        """
        service = Service.objects.create(barber=self.barber_user, name="Old", price=3)
        self.login_as_barber()
        url = reverse("manage_barber_service", kwargs={"service_id": service.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Service.objects.filter(pk=service.id).exists())


    def test_delete_service_not_found(self):
        """
        Deleting a non-existent service for this barber returns error.
        """
        self.login_as_barber()
        url = reverse("manage_barber_service", kwargs={"service_id": 2299})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not exist", str(resp.data["detail"]))


    def test_list_availabilities(self):
        """
        Only future availabilities and future slots for today are listed.
        """
        now = timezone.now().astimezone(ZoneInfo('Europe/Rome'))

        today = now.date()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        past_hour = (now - datetime.timedelta(hours=1)).time().strftime('%H:%M')
        future_hour = (now + datetime.timedelta(hours=1)).time().strftime('%H:%M')

        # Correct assignment
        past_hour = (now - datetime.timedelta(hours=1)).time().strftime('%H:%M')
        future_hour = (now + datetime.timedelta(hours=1)).time().strftime('%H:%M')

        # For tomorrow (should show up with both slots)
        availability_tomorrow = Availability.objects.create(
            barber=self.barber_user,
            date=tomorrow,
            slots=[past_hour, future_hour]
        )

        # For yesterday (should not show up)
        availability_yesterday = Availability.objects.create(
            barber=self.barber_user,
            date=yesterday,
            slots=[past_hour, future_hour]
        )

        # For today (only future_hour should be visible)
        availability_today = Availability.objects.create(
            barber=self.barber_user,
            date=today,
            slots=[past_hour, future_hour]
        )

        self.login_as_barber()
        response = self.client.get(self.availabilities_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get returned availabilities
        availabilities = response.data["availabilities"]

        # Yesterday shouldn't show up
        self.assertNotIn(availability_yesterday.to_dict(), availabilities)

        # For today: only the future slot should show
        expected_today_dict = availability_today.to_dict()
        expected_today_dict['slots'] = [future_hour]
        self.assertIn(expected_today_dict, availabilities)

        # Both slots should show for tomorrow
        self.assertIn(availability_tomorrow.to_dict(), availabilities)


    def test_list_availabilities_only_barber(self):
        """
        Only barbers can list availabilities.
        """
        resp = self.client.get(self.availabilities_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.login_as_client()
        resp2 = self.client.get(self.availabilities_url)
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)


    def test_list_appointments(self):
        """
        Barber can list all their appointments (ongoing only).
        """
        appointment_1 = Appointment.objects.create(
            client=self.client_user, 
            barber=self.barber_user,
            date=datetime.date.today(), 
            slot=datetime.time(14, 0),
            status=AppointmentStatus.ONGOING.value
        )
        
        client = Client.objects.create_user(username="c2", password="foo", email="c2@e.com", is_active=True)

        appointment_2 = Appointment.objects.create(
            client=client, 
            barber=self.barber_user,
            date=datetime.date.today(), 
            slot=datetime.time(15, 0),
            status=AppointmentStatus.COMPLETED.value
        )
        
        self.login_as_barber()
        resp = self.client.get(self.appointments_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        appointments = resp.data["appointments"]
        self.assertIn(appointment_1.to_dict(), appointments)
        self.assertIn(appointment_2.to_dict(), appointments)


    def test_list_reviews(self):
        """
        Barber can list all reviews received.
        """
        client = Client.objects.create_user(username="c3", password="x", email="c3@e.com", is_active=True)
        app = Appointment.objects.create(
            client=client, 
            barber=self.barber_user,
            date=datetime.date.today(), 
            slot=datetime.time(10, 0),
            status=AppointmentStatus.COMPLETED.value)
        
        rev = Review.objects.create(client=client, barber=self.barber_user, rating=5, comment="Great!")
        self.login_as_barber()
        resp = self.client.get(self.reviews_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # At least one review present with right data
        out_reviews = resp.data["reviews"]
        self.assertTrue(any(r["id"] == rev.id for r in out_reviews))
        self.assertEqual(out_reviews[0]["rating"], 5)


    def test_list_reviews_only_barber(self):
        """
        Only barbers can list their reviews.
        """
        resp = self.client.get(self.reviews_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.login_as_client()
        resp2 = self.client.get(self.reviews_url)
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)
