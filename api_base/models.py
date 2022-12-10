# -*- coding: utf-8 -*-
import base64
import json
import os
import string
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from django_api_base.models import UserProfile
from shapely.geometry import Point, Polygon
import commodities
import requests


class BaseModel(models.Model):
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


# Create your models here.

def upload_commodities(added_by_id):

    added_by = BaseProfile.objects.get(id=added_by_id)
    city = added_by.city
    storage_domain = "https://storage.googleapis.com/scenic-style-186704.appspot.com/commodity/"

    commodity_data = []
    img_count = 1
    for data in commodities.DATA:
        commodity_obj = Commodity(
            item_name=data["description"],
            length=data["length"],
            breadth=data["breadth"],
            height=data["height"],
            volume=data["volume"],
            material_type=data["material_type"],
            added_by=added_by,
            city=city,
        )
        if data["installation"] != "":
            commodity_obj.is_plugable = True
            commodity_obj.installation_charge = data["installation"]

        jpeg_url = storage_domain + str(img_count) + ".jpg"
        png_url = storage_domain + str(img_count) + ".png"

        if bool(requests.get(jpeg_url)):
            commodity_obj.image = jpeg_url
        elif bool(requests.get(png_url)):
            commodity_obj.image = png_url

        commodity_data.append(commodity_obj)
        img_count += 1

    Commodity.objects.bulk_create(commodity_data)


def generate_access_token(user_id, length=15, string_set=string.ascii_letters + string.digits):
    '''
    Returns a string with `length` characters chosen from `stringset`
    >>> len(generate_random_string(20) == 20
    '''
    random_string = ''.join([string_set[i % len(string_set)] for i in [ord(x) for x in os.urandom(length)]])
    hashed_value = base64.b16encode(str(user_id))[-2:]
    random_string = "{0}{1}".format(hashed_value, random_string)
    return random_string


class City(BaseModel):
    """
    Model for saving province.
    """
    city_name = models.CharField(max_length=200)
    city_lat = models.CharField(max_length=200)
    city_lng = models.CharField(max_length=200)
    added_on = models.DateTimeField(default=timezone.now)
    polygon_data = models.TextField(default="", null=True)
    cash_only = models.BooleanField(default=False)

    def get_geofence(self):
        return json.loads(self.polygon_data)

    def geofence_contains(self, latitude, longitude):
        point = Point(float(latitude), float(longitude))

        polygon_array = [(i['lat'], i['lng']) for i in self.get_geofence()]
        polygon = Polygon(polygon_array)
        return polygon.contains(point)


class District(BaseModel):
    """
    Model for adding districts for each province
    """
    city = models.ForeignKey(City)
    name = models.CharField(max_length=200)
    latitude = models.CharField(max_length=200)
    longitude = models.CharField(max_length=200)
    added_on = models.DateTimeField(default=timezone.now)


class BaseProfile(BaseModel, UserProfile):
    """
    Model for saving extra user credentials like access token, reset key etc.
    """
    CHOICE = (
        ('-', '-'),
        ('male', 'Male'),
        ('female', 'Female'),
    )

    first_time_activation = models.BooleanField(default=True)
    current_lat = models.CharField(max_length=200, default="", blank=True)
    current_lng = models.CharField(max_length=200, default="", blank=True)
    nationality = models.CharField(max_length=200, default="", blank=True)
    age = models.IntegerField(default=0)
    profile_pic = models.CharField(max_length=500, default="", blank=True)

    STATUS = (
        ('active', 'Active'),
        ('blocked', 'Blocked'),
        ('deleted', 'Deleted'),
        ('suspended', 'Suspended'),
        ('fleet_verified', 'Fleet Verified'),
        ('not_verified', 'Not Verified'),
    )

    LANGUAGES = (
        ('EN', 'English'),
        ('ES', 'Spanish')
    )

    language = models.CharField(max_length=10, default='EN', choices=LANGUAGES)
    status = models.CharField(max_length=100, choices=STATUS, default="not_verified")
    designation = models.CharField(max_length=500, default="", blank=True)
    deposit_needed = models.FloatField(default=645)
    # if Fleet Admin
    ceo_id_proof = models.CharField(max_length=200, default="", blank=True)
    address = models.CharField(max_length=200, default="", blank=True)
    registration_date = models.DateTimeField(default=timezone.now)
    approved_on = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey('self', related_name='+', blank=True, null=True)

    TYPES = (
        ('super_user', 'Super User'),
        ('admin_user', 'Admin User'),
        ('fleet_admin', 'Fleet Admin'),
        ('driver', 'Driver'),
        ('app_user', 'App User'),
        ('operator', 'Operator'),
    )
    user_type = models.CharField(max_length=100, choices=TYPES, default="app_user")
    # TODO: To be checked and removed after code change
    serviceable_area = models.CharField(max_length=500, default="", blank=True)
    fleet_id = models.ForeignKey('self', related_name='a+', null=True, blank=True)
    commission = models.FloatField(default=25)  # Affects only individual drivers and fleets
    is_new_user = models.BooleanField(default=False)
    drive_status = models.BooleanField(default=True)  # FOR DRIVERS ONLY
    in_trip = models.BooleanField(default=False)  # FOR DRIVERS ONLY
    # access_token_single = models.CharField(max_length=100, blank=True, null=True)
    # access_token_expiration_single = models.DateField(default=timezone.now)
    # no_tokens = models.IntegerField(default=10, blank=True, null=True)
    # TODO: "city" Change to many to many field for future working
    city = models.ForeignKey(City, blank=True, null=True)
    rating = models.FloatField(default=5)
    visaUserToken = models.CharField(max_length=500, default="", blank=True)
    # FOY FLEET ONLY
    payment_processed = models.BooleanField(default=False)

    def set_language(self, lang):
        if self.language.lower() != lang:
            self.language = str(lang).upper()
            self.save(update_fields=['language'])


# TODO: Model to be deleted.
class ServiceableArea(BaseModel):
    """
            Model for saving Serviceable Area.
            """
    latitude = models.CharField(max_length=100, default="", blank=True)
    longitude = models.CharField(max_length=100, default="", blank=True)
    loc_name = models.CharField(max_length=100, default="", blank=True)
    charge = models.FloatField(default=0)
    added_on = models.DateTimeField(default=timezone.now)
    driver_id = models.ForeignKey(BaseProfile)


class TransferType(BaseModel):
    """
        Model for saving Transfer Types Density Factor.
        """
    TYPES = (
        ('CH', 'CH'),
        ('EMBD', 'EMBD'),
        ('EMAD', 'EMAD'),
    )
    transfer_from = models.CharField(max_length=100, choices=TYPES, default="CH")
    transfer_to = models.CharField(max_length=100, choices=TYPES, default="CH")
    charge = models.FloatField(default=0)
    added_on = models.DateTimeField(default=timezone.now)
    added_by = models.ForeignKey(BaseProfile)
    city = models.ForeignKey(City)


class Commodity(BaseModel):
    """
        Model for saving Commodity.
        """
    item_name = models.CharField(max_length=200)
    length = models.FloatField(default=0)
    breadth = models.FloatField(default=0)
    height = models.FloatField(default=0)
    volume = models.FloatField(default=0)
    image = models.CharField(max_length=200, default="", blank=True)
    charge = models.FloatField(default=0)
    installation_charge = models.FloatField(default=0)
    material_type = models.CharField(max_length=200, default="", blank=True)
    added_on = models.DateTimeField(default=timezone.now)
    added_by = models.ForeignKey(BaseProfile)
    city = models.ForeignKey(City)
    is_plugable = models.BooleanField(default=False)
    loaders = models.IntegerField(default=1)

    def __str__(self):
        return self.item_name


# TODO: Edit after discussion
class Service(BaseModel):
    """
        Model for saving Service.
        """
    # TODO: need to delete service_from and service_to
    FROM_TYPES = (
        ('packed', 'Packed'),
        ('unplugged', 'Unplugged'),
    )
    service_from = models.CharField(max_length=100, blank=True, null=True, choices=FROM_TYPES)
    TO_TYPES = (
        ('delivery', 'Delivery'),
        ('plugged', 'Plugged'),
    )
    service_to = models.CharField(max_length=100, blank=True, null=True, choices=TO_TYPES)
    SERVICES = (
        ('packed-packed', 'Transfer'),
        ('unpacked-packed', 'Relocation Package Plus'),
        ('unpacked-unpacked', 'Relocation Package Plus Plus Uncrating'),
    )
    service_name = models.CharField(max_length=100, choices=SERVICES, default="packed-packed")
    # FIELD ONLY USED TO DISPLAY SERVICE NAME IN APP & DASHBOARD
    display_service_name_en = models.CharField(max_length=100, default='', null=True, blank=True)
    service_description_en = models.CharField(max_length=100, default='', null=True, blank=True)
    display_service_name_es = models.CharField(max_length=100, default='', null=True, blank=True)
    service_description_es = models.CharField(max_length=100, default='', null=True, blank=True)
    is_plugable = models.BooleanField(default=False)
    charge = models.FloatField(default=0)
    # charge_10_20 = models.FloatField(default=0)
    # charge_20_30 = models.FloatField(default=0)
    # charge_30_40 = models.FloatField(default=0)
    # charge_40_50 = models.FloatField(default=0)
    # charge_50_60 = models.FloatField(default=0)
    # charge_60_70 = models.FloatField(default=0)
    added_on = models.DateTimeField(default=timezone.now)
    added_by = models.ForeignKey(BaseProfile)
    city = models.ForeignKey(City)

    def set_as_plugable(self):
        if self.service_to == 'plugged':
            self.is_plugable = True
        else:
            self.is_plugable = False
        self.save()


class Assistants(BaseModel):
    """
        Model for saving Assistants.
        """
    assistant_name = models.CharField(max_length=200, default="", blank=True)
    id_proof = models.CharField(max_length=200, default="", blank=True)
    photo = models.CharField(max_length=200, default="", blank=True)
    added_on = models.DateTimeField(default=timezone.now)
    driver_id = models.ForeignKey(BaseProfile)


class Transfer(BaseModel):
    """
        Model for saving Transfer.
        """
    no_items = models.IntegerField(default=0)
    TYPE = (
        ('commodity', 'Commodity'),
        ('truck', 'Truck'),
    )
    source = models.CharField(max_length=100, blank=True, null=True, choices=TYPE)

    tot_volume = models.FloatField(default=0)
    transfer_on = models.DateTimeField(blank=True, null=True)
    driver = models.ForeignKey(BaseProfile, related_name='+', blank=True, null=True)

    # FOR CURRENT PHASE, FOR MULTI PICKUP AND DROP, USE TRANSFER LOCATION TABLE
    transfer_type = models.ForeignKey(TransferType, blank=True, null=True)
    service_type = models.ForeignKey(Service, blank=True, null=True)

    commission = models.FloatField(default=0)
    total_amount = models.FloatField(default=0)
    amount_paid = models.FloatField(default=0)
    damage_refund = models.FloatField(default=0)
    penalty = models.FloatField(default=0)
    advance_received = models.BooleanField(default=False)
    payment_received = models.BooleanField(default=False)
    advance_amount = models.FloatField(default=0)
    payable_amount = models.FloatField(default=0)
    TYPE = (
        ('cash', 'Cash Payment'),
        ('card', 'Card Payment'),
    )
    payment_type = models.CharField(max_length=100, blank=True, null=True, choices=TYPE)
    instant_search = models.BooleanField(default=True)  # TRUE FOR REQUEST NOW

    STATUS = (
        ('not_paid', 'Not Paid'),
        ('active', 'Active'),
        ('accepted', 'Accepted'),
        ('cancelled', 'Cancelled'),
        ('auto_cancelled', 'Auto Cancelled'),
        ('loading', 'Loading'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
    )
    status = models.CharField(max_length=100, choices=STATUS, default="not_paid")
    cancel_comments = models.TextField(default="", null=True)
    # Transfer timedout - driver couldnt reach at time.
    transfer_timed_out = models.BooleanField(default=False)
    started_on = models.DateTimeField(blank=True, null=True)
    completed_on = models.DateTimeField(blank=True, null=True)
    added_on = models.DateTimeField(default=timezone.now)
    added_by = models.ForeignKey(BaseProfile, related_name='a+')
    installation_charge = models.FloatField(default=0)
    service_charge = models.FloatField(default=0)
    density_charge = models.FloatField(default=0)
    discount_offered = models.FloatField(default=0)
    distance = models.CharField(max_length=200, blank=True, null=True)
    duration = models.CharField(max_length=200, blank=True, null=True)
    city = models.ForeignKey(City)
    damage_resolved = models.BooleanField(default=False)
    refund_initiated = models.BooleanField(default=False)
    helpers = models.ManyToManyField(Assistants, blank=True)
    helper_amount = models.FloatField(default=0)
    helper_count = models.IntegerField(default=0)
    cancel_notify_admin = models.BooleanField(default=False)
    is_special_handling_required = models.BooleanField(default=False)
    special_handling_fee = models.FloatField(default=0)
    share_trip = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class TransferLocation(BaseModel):
    """
        Model for saving Multiple Pickup and drop locations Locations.
        """
    transfer_id = models.ForeignKey(Transfer)
    floor = models.IntegerField(default=0)
    # ONLY USED FOR MULTI PICKUP AND DROP STAGE
    transfer_type = models.ForeignKey(TransferType, blank=True, null=True)
    service_type = models.ForeignKey(Service, blank=True, null=True)

    TRANSFER_TYPES = (
        ('1', 'House'),
        ('2', 'Apartment'),
        ('3', 'Flat'),
        ('4', 'Shop/Office'),
    )
    # TODO: Need to changed after discussion
    transfer_loc = models.CharField(max_length=100, blank=True, null=True, choices=TRANSFER_TYPES)
    loc_lat = models.CharField(max_length=200)
    loc_lng = models.CharField(max_length=200)

    # TODO: Need to not nullable field after new changes implemented
    location_name = models.CharField(max_length=200, default="", blank=True)
    LOC_TYPES = (
        ('pickup', 'Pickup'),
        ('drop', 'Drop'),
    )
    loc_type = models.CharField(max_length=100, choices=LOC_TYPES, default="pickup")

    def __str__(self):
        return str(self.id)


class TransferCommodity(BaseModel):
    """
        Model for saving Transfer Commodity for each pickup and drop separately.
        """
    transfer_loc_id = models.ForeignKey(TransferLocation)
    item = models.ForeignKey(Commodity)
    added_by = models.ForeignKey(BaseProfile)
    need_plugged = models.BooleanField(default=False)


"""
Model For Offer Management
Author: Hari
Date:12-03-2018
"""


class DriverOffer(BaseModel):
    TYPES = (
        ('time', 'TIME'),
        ('trip', 'TRIP'),
    )
    APPLIEDTO = (
        ('fleet', 'FLEET'),
        ('user', 'USER'),
    )
    OFFER = (
        ('cash', 'CASH'),
        ('discount', 'DISCOUNT'),
    )
    OFFER_BASE = (
        ('daily', 'DAILY'),
        ('weekly', 'WEEKLY'),
    )

    offer_based_on = models.CharField(max_length=20, default='time', choices=TYPES)
    offer_applied_to = models.CharField(max_length=20, default='fleet', choices=APPLIEDTO)
    offer_type = models.CharField(max_length=20, default='cash', choices=OFFER)
    total_duration = models.FloatField(default=0)
    total_trip_count = models.IntegerField(default=0)
    offer_base = models.CharField(max_length=20, default='daily', choices=OFFER_BASE)
    offer_commission_cash = models.FloatField(default=0)
    offer_commission_percent = models.FloatField(default=0)
    offer_valid_from = models.DateField(default=timezone.now)
    offer_valid_to = models.DateField(default=timezone.now)
    added_by = models.ForeignKey(BaseProfile)

    def __str__(self):
        return str(self.id)


class Notifications(BaseModel):
    """
        Model for saving Notifications.
        """
    message_headline = models.CharField(max_length=200, default="", blank=True)
    message = models.TextField(default="", blank=True)
    transfer_id = models.ForeignKey(Transfer, blank=True, null=True, default=None)
    offer_id = models.ForeignKey(DriverOffer, blank=True, null=True, default=None)
    receiver = models.ForeignKey(BaseProfile, blank=True, null=True, default=None)
    TYPES = (
        ('trip_request', 'Trip Requested'),
        ('trip_scheduled', 'Trip Scheduled'),
        ('trip_reminder', 'Trip Reminder'),
        ('trip_cancelled', 'Trip Cancelled'),
        ('already_accepted', 'Already Accepted'),
        ('trip_accepted', 'Trip Accepted'),
        ('start_loading', 'Start Loading'),
        ('trip_started', 'Trip Started'),
        ('trip_completed', 'Trip Completed'),
        ('search_failed', 'Search Failed'),
        ('promotion', 'Promotion'),
        ('offer', 'Offer'),
        ('missed_transfer', 'Missed Transfer'),
        ('refund_initiated', 'Refund Initiated')
    )
    type = models.CharField(max_length=100, choices=TYPES, default="trip_request")

    def __str__(self):
        return str(self.id)


class NotificationHistory(BaseModel):
    """
        Model for saving Notification History.
        """
    notification_id = models.ForeignKey(Notifications)
    user = models.ForeignKey(BaseProfile)
    sent_on = models.DateTimeField(default=timezone.now)
    read_status = models.BooleanField(default=False)
    read_on = models.DateTimeField(blank=True, null=True)
    is_valid = models.BooleanField(default=True)
    time_out = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class TruckRequest(BaseModel):
    """
        Model for saving Truck Request.
        """
    transfer_id = models.ForeignKey(Transfer)
    driver_id = models.ForeignKey(BaseProfile)
    STATUS = (
        ('sent', 'Sent'),
        ('time_out', 'Time Out'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('requested', 'Requested'),
        ('auto_cancel', 'Auto Cancel'),
    )
    status = models.CharField(max_length=100, choices=STATUS, default="sent")
    sent_on = models.DateTimeField(default=timezone.now)


class Attachments(BaseModel):
    """
        Model for saving Attachments.
        """
    attachment = models.CharField(max_length=200, default="", blank=True)
    TYPES = (
        ('fitness_certificate', 'Fitness Certificate'),
        ('tax_certificate', 'Tax Certificate'),
        ('driver_license', 'Driver License'),
        ('commercial_insurance', 'Commercial Insurance'),
        ('registration_certificate', 'Registration Certificate'),
    )
    doc_type = models.CharField(max_length=100, choices=TYPES, default="driver_license")
    added_on = models.DateTimeField(default=timezone.now)
    driver_id = models.ForeignKey(BaseProfile)


class VehicleDetails(BaseModel):
    """
        Model for saving Vehicle Details.
        """
    driver_id = models.OneToOneField(BaseProfile)
    security_deposit = models.FloatField(default=0)
    balance_deposit = models.FloatField(default=0)
    reg_no = models.CharField(max_length=200, default="", blank=True)
    location = models.CharField(max_length=200, default="", blank=True)
    no_assistants = models.IntegerField(default=0)
    drive_status = models.BooleanField(default=True)
    STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('verified', 'Verified'),
    )
    status = models.CharField(max_length=100, choices=STATUS, default="pending")
    approved_on = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(BaseProfile, related_name='+', blank=True, null=True)
    added_by = models.ForeignKey(BaseProfile, related_name='a+')
    added_on = models.DateTimeField(default=timezone.now)
    vehicle_volume = models.FloatField(default=0)
    vehicle_height = models.FloatField(default=0)


class DamageReportPhotos(BaseModel):
    """Model for saving all the damage photos of a transfer"""

    transfer = models.ForeignKey(Transfer)
    photo = models.CharField(max_length=200)

    def __str__(self):
        return self.transfer.id


class Damage(BaseModel):
    """
        Model for saving Damage.
        """
    transfer_id = models.ForeignKey(Transfer)
    count = models.IntegerField(default=0)
    photo = models.CharField(max_length=200, default="", blank=True)

    TYPES = (
        ('partial', 'Partial Damage'),
        ('full', 'Full Damage'),
        ('stolen', 'Stolen'),
    )
    damage_type = models.CharField(max_length=100, choices=TYPES, default="partial")
    added_on = models.DateTimeField(default=timezone.now)
    description = models.TextField(default="", blank=True)
    # TODO: Check after discussion
    item_id = models.ForeignKey(Commodity, blank=True, null=True)

    # def __str__(self):
    #     return self.transfer_id.id


# TODO: Check after discussion
class DamagePhotos(BaseModel):
    """Model for saving all the damage photos of each damage reported"""

    transfer_id = models.ForeignKey(Transfer, blank=True, null=True)
    item_id = models.ForeignKey(Commodity, blank=True, null=True)
    photo = models.CharField(max_length=200)

    # def __str__(self):
    #     return self.damaged_item.transfer_loc_id.transfer_id.id


class DamageDescriptions(BaseModel):
    """
    To save descriptions of damages added
    """
    transfer_id = models.ForeignKey(Transfer)
    description = models.TextField(default="", blank=True)


class Promotions(BaseModel):
    """
        Model for saving Promotions.
        """
    transfer_id = models.ForeignKey(Transfer)
    damaged_item = models.ForeignKey(TransferCommodity)
    promo_text = models.CharField(max_length=200, default="", blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_through = models.DateTimeField(default=timezone.now)
    percentage = models.FloatField(default=0)
    added_on = models.DateTimeField(default=timezone.now)


class NotificationsSettings(BaseModel):
    """
    Notification Settings for users
    """
    user_profile = models.OneToOneField(BaseProfile)
    promotions = models.BooleanField(default=True)
    momentalert = models.BooleanField(default=True)


class Discount(BaseModel):
    """
        Model for saving Discounts for each services.
        """

    service_type = models.ForeignKey(Service)
    rate_from = models.FloatField(default=0)
    rate_to = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    added_on = models.DateTimeField(default=timezone.now)
    added_by = models.ForeignKey(BaseProfile)
    STATUS = (
        ('active', 'Active'),
        ('deleted', 'Deleted'),
    )
    status = models.CharField(max_length=100, choices=STATUS, default="active")

class TruckTypes(models.Model):
    TYPE = (
        ('Trailer Truck', 'Trailer Truck'),
        ('Semi-Trailer Truck', 'Semi-Trailer Truck'),
        ('Large Truck', 'Large Truck'),
        ('Medium Truck', 'Medium Truck')
    )
    category_name = models.CharField(max_length=100, default='Trailer Truck', choices=TYPE)
    vol_min = models.FloatField(default=1)
    vol_max = models.FloatField(default=5)
    image = models.CharField(max_length=200, default="", blank=True)


class TruckCrew(BaseModel):
    """
        Model for saving Truck crews.
        """

    capacity_from = models.FloatField(default=0)
    capacity_to = models.FloatField(default=0)
    no_drivers = models.IntegerField(default=1)
    a = models.FloatField(default=1)
    b = models.FloatField(default=1)
    c = models.FloatField(default=1)
    amount_per_helper = models.FloatField(default=2)
    loading_peoples = models.IntegerField(default=0)
    added_by = models.ForeignKey(BaseProfile)


class Rating(models.Model):
    """
    Model for Rating for drivers.
    """

    rating_from = models.ForeignKey(BaseProfile, related_name='+')
    rating_to = models.ForeignKey(BaseProfile, related_name='a+')
    transfer_id = models.ForeignKey(Transfer)
    rating_value = models.FloatField(default=1)
    added_on = models.DateTimeField(default=timezone.now)
    status = models.BooleanField(default=True)
    description = models.TextField(default="", blank=True)


class Documents(models.Model):
    """
    Model for System Documents like FAQ, Privacy Policy etc.
    """

    document = models.CharField(max_length=200, default="", blank=True)
    TYPES = (
        ('faq', 'FAQ'),
        ('privacy_policy', 'Privacy Policy'),
        ('terms_conditions', 'Terms & Conditions'),
    )
    document_type = models.CharField(max_length=100, choices=TYPES, default="faq")

    LANGUAGE = (
        ('en', 'English'),
        ('es', 'Español'),
    )
    language = models.CharField(max_length=100, choices=LANGUAGE, default="es")
    APP_TYPE = (
        ('user', 'User App'),
        ('partner', 'Partner App'),
    )
    app_type = models.CharField(max_length=100, choices=APP_TYPE, default="user")


# TODO: To be deleted after code check
class SavedLocations(BaseModel):
    """
            Model for saving Pickup locations of user.
            """
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    loc_name = models.CharField(max_length=200, blank=True, null=True)
    added_on = models.DateTimeField(default=timezone.now)
    user_id = models.ForeignKey(BaseProfile)


class SecurityDepositHistory(BaseModel):
    """ Model for saving Security Deposits added by driver and fleets
               """
    user_id = models.ForeignKey(BaseProfile)
    security_deposit = models.FloatField(default=0)
    added_on = models.DateTimeField(default=timezone.now)


class DriveStatusHistory(BaseModel):
    """
        Model for saving Drive status for offer Calculation
    """
    driver = models.ForeignKey(BaseProfile)
    status_from = models.DateTimeField(default=timezone.now)
    status_to = models.DateTimeField(blank=True, null=True)


class PayoutHistory(BaseModel):
    """
        Model for saving payout history of drivers
    """

    driver = models.ForeignKey(BaseProfile)
    date = models.DateTimeField(blank=True, null=True)
    total_bookings_amount = models.FloatField(default=0)
    commission_amount_to_muberz = models.FloatField(default=0)
    transfer_cash_in_drivers_hand = models.FloatField(default=0)
    cash_incentives_earned_by_driver = models.FloatField(default=0)
    drivers_earnings_from_transfers = models.FloatField(default=0)
    drivers_earnings_from_discounts = models.FloatField(default=0)
    net_payable_for_driver = models.FloatField(default=0)
    amount_to_be_collected_from_driver = models.FloatField(default=0)
    payment_processed = models.BooleanField(default=False)
    transfers = models.ManyToManyField(Transfer, blank=True)


class SecurityDeposit(BaseModel):
    """
        Model for saving Security Deposit of each volume trucks
        """

    capacity_from = models.FloatField(default=0)
    capacity_to = models.FloatField(default=0)
    deposit_needed = models.FloatField(default=0)
    added_by = models.ForeignKey(BaseProfile)


class RefundManagement(BaseModel):
    STATUS = (
        ('requested', 'Refund Requested'),
        ('processing', 'Refund In Process'),
        ('initiated', 'Refund Initiated'),
        ('completed', 'Refund Complete'),
    )
    added_by = models.ForeignKey(BaseProfile, null=True)
    refund_cause = models.TextField()
    date_added = models.DateTimeField(auto_now=True)
    amount_to_refund = models.FloatField(default=0)
    transfer = models.ForeignKey(Transfer)
    status = models.CharField(max_length=20, default='requested', choices=STATUS)


class Transaction(BaseModel):
    STATUS = (
        ('pending', 'Payment Pending'),
        ('processing', 'Payment in Process'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
    )
    transfer = models.ForeignKey(Transfer)
    date = models.DateTimeField(default=timezone.now())
    transactionID = models.CharField(max_length=500, default="", blank=True)
    eTicket = models.CharField(max_length=500, default="", blank=True)
    uniqueID = models.CharField(max_length=500, default="", blank=True)
    amount = models.FloatField(default=0)
    status = models.CharField(max_length=100, default='pending', choices=STATUS)
    payee = models.ForeignKey(BaseProfile)


class SearchFailedLog(BaseModel):
    transfer = models.ForeignKey(Transfer)
    user = models.CharField(max_length=500, default="", blank=True)
    excluded_driver = models.ForeignKey(BaseProfile)
    reason = models.CharField(max_length=500, default="", blank=True)


class Promotion(models.Model):
    added_by = models.ForeignKey(BaseProfile, null=True, blank=True)
    name = models.CharField(max_length=100, default="")
    percentage = models.FloatField(default=0)
    short_description = models.CharField(max_length=500, default="", blank=True)
    description = models.TextField(default="", null=True)
    expiry = models.DateTimeField(blank=True, null=True)
    added_on = models.DateTimeField(default=timezone.now)


class Advertisement(models.Model):
    added_by = models.ForeignKey(BaseProfile, null=True, blank=True)
    name = models.CharField(max_length=150, default="")
    date_start = models.DateTimeField(blank=True, null=True)
    date_end = models.DateTimeField(blank=True, null=True)
    image = models.CharField(max_length=200, default="", blank=True)
    user = models.BooleanField(default=False)
    partner = models.BooleanField(default=False)
    added_on = models.DateTimeField(default=timezone.now)


class OnOffSwitch(models.Model):
    start_date = models.TimeField(blank=True, null=True)
    end_date = models.TimeField(blank=True, null=True)
    status = models.BooleanField(default=True)
    added_by = models.ForeignKey(BaseProfile, null=True, blank=True)
