# -*- coding: utf-8 -*-
import base64
import logging
import os
import string
import threading
from math import radians, atan2, sin, sqrt, cos

import googlemaps
import pytz
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils import timezone
from django.views.generic import View
from django_api_base.models import DeviceID, RefreshToken, AccessToken
from twilio.rest import Client
from django.urls import reverse

from Muberz.settings import get_config
from api_base.models import District, City, RefundManagement, BaseProfile, VehicleDetails, TransferCommodity
from api_base.models import *
logger_me = logging.getLogger('debug')
logger = logging.getLogger(__name__)


def log_me(message):
    logger.info(message)


TransferTypeList = {
    '1': 'Home',
    '2': 'Flat'
}

gmaps = googlemaps.Client(key='AIzaSyBOWcnen7Ga2wfM_vEhhpknHC4wnEJI4z0')

# Function to generate a random string according to input for ACCESS TOKEN
def generate_access_token(user_id, length=15, string_set=string.ascii_letters + string.digits):
    '''
    Returns a string with `length` characters chosen from `stringset`
    >>> len(generate_random_string(20) == 20
    '''

    random_string = ''.join([string_set[i % len(string_set)] for i in [ord(x) for x in os.urandom(length)]])
    hashed_value = base64.b16encode(str(user_id))[-2:]
    random_string = "{0}{1}".format(hashed_value, random_string)
    return random_string


# Function for sending template email
def send_template_email(subject, message, to):
    from_email = "no-reply@section12"
    send_mail(subject, message, recipient_list=to, from_email=from_email, html_message=message, fail_silently=True)


# Function for sending a verification mail on signup
def forgot_password(email, key, name, request):
    subject = "Section-12 Forgot Password"
    to = [email]
    link = "http://{0}/reset-password/{1}".format(request.META['HTTP_HOST'], key)
    ctx = {
        'link': link,
        'name': name,
        'request': request,
    }

    message = get_template('dashboard/email-templates/action.html').render(ctx)
    threading.Thread(target=send_template_email, args=(subject, message, to)).start()


def signup_mail(user, request, password):
    if user.is_superuser:
        subject = "Administration Registration Successful with Section-12"
    else:
        subject = "Council Registration Successful with Section-12"
    to = [user.email]
    link = 'http://' + request.META['HTTP_HOST'] + '/login/'
    ctx = {
        'link': link,
        'user': user,
        'password': password,
    }

    message = get_template('dashboard/email-templates/signup-mail.html').render(ctx)
    threading.Thread(target=send_template_email, args=(subject, message, to)).start()


# Function for sending SMS
def send_sms(mobile, message):
    url = "https://bulksms.vsms.net/eapi/submission/send_sms/2/2.0"
    params = {'username': 'alenpeter', 'password': 'onemillion', 'message': message, 'msisdn': mobile}
    # f = urllib.request.urlopen(url, params)
    f = requests.get(url, params)

    statusCode = f.status_code
    #
    # statusString = result[1]
    #
    # if statusCode != '0':
    #     return "Error: " + statusCode + ": " + statusString
    # else:
    #     return "Message sent: batch ID " + result[2]

    # #alen's edit:
    #
    # url = "http://bhashsms.com/api/sendmsg.php?"
    # params = {
    #     'user': 'alenpeter',
    #     'pass': 'onemillion',
    #     'sender': 'MYTEAM',
    #     'phone': mobile,
    #     'text': message,
    #     'stype': 'normal',
    #     'priority': 'ndnd',
    # }
    # f = requests.get(url, params)
    # print(f.headers)
    # statusCode = f.status_code

    return statusCode


def send_sms_twilio(mobile, message):
    # Your Account Sid and Auth Token from twilio.com/user/account
    account_sid = get_config('TWILIO_ACCOUNT')
    auth_token = get_config('TWILIO_TOKEN')
    client = Client(account_sid, auth_token)
    try:
        client.messages.create(
            mobile,
            body=message,
            from_=get_config('TWILIO_NUMBER')
        )
        status = 200
        # logger_me.debug("%")
        # logger_me.debug(message.status)
        # logger_me.debug(message.sid)
        # logger_me.debug(str(message.error_code))
        # logger_me.debug("%")
    except:
        status = 400
    return status  # CHECK ITS 'failed' or not


# Decorator for checking the permission of the user
def verify_permission(login=True, level=None, login_url='/'):
    """
    :param login: Whether the user has to be login or not
    :param level: Level of the user (None/superuser/staff)
    :param login_url: redirect url
    """

    def verify_permission_view(func):
        def verify(request, *args, **kwargs):
            if login:
                if request.user.is_authenticated():
                    pass
                    # return redirect(reverse('dashboard/page-login.html'))
                    if level is None:
                        pass
                    elif level == 'superuser':
                        if not request.user.is_superuser:
                            return redirect(reverse('dashboard:404'))

                    elif level == 'staff':
                        if not request.user.is_staff:
                            return redirect(reverse('dashboard:404'))

                    elif level == 'user':
                        if request.user.is_staff or request.user.is_superuser:
                            return redirect(reverse('dashboard:404'))
                else:
                    return redirect(login_url)
            else:
                pass

            return func(request, *args, **kwargs)

        return verify

    return verify_permission_view


def haversine(lat1, lon1, lat2, lon2):
    """
    Haversine formula based function for finding the distance between latitude and longitude
    :param lat1:
    :param lon1:
    :param lat2:
    :param lon2:
    :return: distance in KM
    """

    r = 6372.8  # Earth radius in kilometers

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return r * c


#
# def get_lat_lng_from_address(address):
#     """
#     Finds the latitude and longitude from address
#     :param address:
#     :return: returns latitude and longitude
#     """
#     api_url = "https://maps.googleapis.com/maps/api/geocode/json"
#     dic = {
#         "address": "{0}".format(address),
#         "key": "AIzaSyCSvaUsG8AbpLTPvTB8OWUIbaJQXUAEca4"
#     }
#     response = requests.get(api_url, dic)
#     if response.status_code == 200:
#         try:
#             latitude = response.json()['results'][-1]['geometry']['location']['lat']
#             longitude = response.json()['results'][-1]['geometry']['location']['lng']
#             log_me(latitude + longitude)
#         except Exception, e:
#             log_me(e.message)
#             latitude = None
#             longitude = None
#     else:
#         latitude = None
#         longitude = None
#
#     return latitude, longitude

def get_city_from_location(latitude, longitude):
    city_obj = City.objects.all()
    city_name = ""
    for cities in city_obj:
        if cities.polygon_data != '':
            inside_geo = cities.geofence_contains(latitude, longitude)
            if inside_geo:
                city_name = cities.city_name
                break
        else:
            city_name = ""
    # district = get_district_from_location(latitude, longitude)
    # city = ""
    # if district:
    #     city_objs = City.objects.filter(district__name=district).values_list('city_name', flat=True)
    #     if city_objs:
    #         city = city_objs[0]
    return city_name


def get_district_from_location(latitude, longitude):
    reverse_result = gmaps.reverse_geocode((latitude, longitude))
    all_districts_in_lima = list(District.objects.filter().values_list('name', flat=True))

    def parse_district():
        c_name = ""
        for each_result in reverse_result:
            address_components = each_result["address_components"]
            for each_address in address_components:
                long_name = each_address["long_name"]
                if long_name in all_districts_in_lima:
                    c_name = long_name
                    break
            if c_name:
                break
        return c_name

    c_name = parse_district()
    logger_me.debug("out")
    logger_me.debug(c_name)
    return c_name


def get_address_from_location(latitude, longitude):
    reverse_result = gmaps.reverse_geocode((latitude, longitude))

    def parse_city(category="neighborhood"):
        c_name = ""
        for each_result in reverse_result:
            address_components = each_result["address_components"]
            for each_address in address_components:
                types = each_address["types"]
                if category in types:
                    long_name = each_address["long_name"]
                    if long_name != "":
                        c_name = long_name
                        break
            if c_name:
                break
        return c_name

    c_name = parse_city()
    if not c_name:
        c_name = parse_city("sublocality")
        if not c_name:
            c_name = parse_city("locality")
    return c_name


def get_distance_matrix(from_lat, from_lng, to_lat, to_lng):
    """
    Finds the distance between 2 places
    :param origin:
    :param destination:
    :return: returns json content
    """

    api_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    dic = {
        "origins": from_lat + ',' + from_lng,
        "destinations": to_lat + ',' + to_lng,
        "units": "metric",
        "key": get_config('GOOGLE_API_KEY')
    }
    duration = ''
    distance = ''
    distance_in_km = 0
    duration_in_sec = 0

    response = requests.get(api_url, dic)

    logger_me.debug("% DISTANCE MATRIX API %")
    logger_me.debug(dic)

    if response.status_code == 200:
        if 'rows' in response.json():

            logger_me.debug("% DISTANCE MATRIX RESPONSE %")
            logger_me.debug(response.json())
            try:
                if response.json()['rows'][-1]['elements'][-1]['status'] != 'ZERO_RESULTS':
                    distance = response.json()['rows'][-1]['elements'][-1]['distance']['text']
                    duration = response.json()['rows'][-1]['elements'][-1]['duration']['text']
                    duration_in_sec = response.json()['rows'][-1]['elements'][-1]['duration']['value']
                    if str(duration_in_sec).isdigit():
                        duration_in_sec = int(duration_in_sec)
                    else:
                        duration_in_sec = 0
                    distance_in_km = response.json()['rows'][-1]['elements'][-1]['distance']['value'] / 1000
            except:
                duration = ''
                distance = ''
                distance_in_km = 0
                duration_in_sec = 0
        else:
            duration = ''
            distance = ''
            distance_in_km = 0
            duration_in_sec = 0
    else:
        duration = ''
        distance = ''
        distance_in_km = 0
        duration_in_sec = 0

    if duration_in_sec == 0:
        if duration != '':
            duration_array = duration.split(' ')
            if len(duration_array) == 2:
                if duration_array[0].isdigit():
                    if duration_array[1] == 'min' or duration_array[1] == 'mins':
                        duration_in_sec = int(duration_array[0]) * 60
                    elif duration_array[1] == 'hour' or duration_array[1] == 'hours':
                        duration_in_sec = int(duration_array[0]) * 3600
            elif len(duration_array) == 4:
                if duration_array[0].isdigit() and duration_array[2].isdigit():
                    if duration_array[1] == 'hour' or duration_array[1] == 'hours':
                        duration_in_sec = int(duration_array[0]) * 3600
                    if duration_array[3] == 'min' or duration_array[3] == 'mins':
                        duration_in_sec += int(duration_array[2]) * 60

    return distance, duration, duration_in_sec, distance_in_km


# Function for getting Location name from latitude and longitude
def get_location_name(latitude, longitude):
    """
    Finds the country name from latitude and longitude
    :param latitude:
    :param longitude:
    :return: returns country name
    """
    api_url = "https://maps.googleapis.com/maps/api/geocode/json"
    dic = {
        "latlng": latitude + ',' + longitude,
        "sensor": "false",
        "key": get_config('GOOGLE_API_KEY')
    }
    response = requests.get(api_url, dic)
    if response.status_code == 200:
        try:
            location_name = response.json()['results'][-2]['address_components'][0]['long_name']
            # location_name = response.json()['results'][1]['address_components'][2]['long_name']
        except Exception:
            location_name = None
    else:
        location_name = None
    return location_name


# # Function for sending template email
def send_template_email(subject, message, to):
    from_email = settings.FROM_EMAIL
    send_mail(subject, message, recipient_list=to, from_email=from_email, html_message=message, fail_silently=True)


class SingleAccessTokenManagement(object):

    @staticmethod
    def initialise_access_token(device_id, user):
        """Method for initialising access token, refresh token and device id data for user"""
        try:
            AccessToken.objects.filter(user=user).delete()  # Deleting pre existing access tokens
            device = DeviceID.objects.get(device_id=device_id)
            if device.user == user:
                try:
                    refresh_token = RefreshToken.objects.get(device_id=device, user=user, expire_count__gte=1)

                except RefreshToken.DoesNotExist:
                    refresh_token = RefreshToken.objects.create(user=user, device_id=device)

                access_token = AccessToken.objects.create(user=user)
                refresh_token.expire_count -= 1
                if refresh_token.expire_count == 0:
                    refresh_token.delete()
                    device = DeviceID.objects.get(device_id=device_id)
                    refresh_token = RefreshToken.objects.create(device_id=device, user=device.user)
                else:
                    refresh_token.save()

            else:
                device.delete()
                device = DeviceID.objects.create(device_id=device_id, user=user)
                refresh_token = RefreshToken.objects.create(user=user, device_id=device)
                access_token = AccessToken.objects.create(user=user)

        except DeviceID.DoesNotExist:
            AccessToken.objects.filter(user=user).delete()  # Deleting pre existing access tokens
            device = DeviceID.objects.create(device_id=device_id, user=user)
            refresh_token = RefreshToken.objects.create(user=user, device_id=device)
            access_token = AccessToken.objects.create(user=user)

        # Deleting any other device linked to user other than current device
        DeviceID.objects.filter(user=user).exclude(device_id=device_id).delete()

        return access_token, refresh_token

    @staticmethod
    def refresh_access_token(device_id, refresh_token):
        """
        This method is for refreshing access tokens when they expire. Multiple access tokens will be valid for a user
        """
        try:
            refresh_token = RefreshToken.objects.get(
                token=refresh_token, device_id__device_id=device_id, expire_count__gt=0)
            access_token = AccessToken.objects.create(user=refresh_token.user)
            refresh_token.expire_count -= 1
            if refresh_token.expire_count == 0:
                refresh_token.delete()
                device = DeviceID.objects.get(device_id=device_id)
                refresh_token = RefreshToken.objects.create(device_id=device, user=device.user)
            else:
                refresh_token.save()

            now_date = timezone.now().date()
            if AccessToken.objects.filter(expires__lt=now_date).exists():
                AccessToken.objects.filter(expires__lt=now_date).delete()

        except RefreshToken.DoesNotExist:
            return None, "Invalid Refresh Token"

        return access_token, refresh_token

    @staticmethod
    def refresh_access_token_single(device_id, refresh_token):
        """
        This method is for refreshing access tokens when they expire. Only single access token will be valid for a user
        """
        try:
            refresh_token = RefreshToken.objects.get(
                token=refresh_token, device_id__device_id=device_id, expire_count__gt=0)
            AccessToken.objects.filter(user=refresh_token.user).delete()
            access_token = AccessToken.objects.create(user=refresh_token.user)
            refresh_token.expire_count -= 1
            if refresh_token.expire_count == 0:
                refresh_token.delete()
                device = DeviceID.objects.get(device_id=device_id)
                refresh_token = RefreshToken.objects.create(device_id=device, user=device.user)
            else:
                refresh_token.save()

            now_date = timezone.now().date()
            if AccessToken.objects.filter(expires__lt=now_date).exists():
                AccessToken.objects.filter(expires__lt=now_date).delete()

        except RefreshToken.DoesNotExist:
            return None, "Invalid Refresh Token"

        return access_token, refresh_token

    @staticmethod
    def delete_access_token_permission(user):
        """Method for deleting all the access tokens and refresh tokens of a user"""

        DeviceID.objects.filter(user=user).delete()
        AccessToken.objects.filter(user=user).delete()


class LanguageConversion(View):
    def get_lang_word(self, language, word):
        if language == 'en':
            language_dict = {
                "lbl_provide_access_token": "PLEASE PROVIDE AN ACCESS TOKEN",
                "lbl_session_expired": "SESSION EXPIRED",
                "lbl_acc_not_active": "Your account is not active. Please contact administrator",
                "lbl_acc_is_blocked": "Your account is blocked. Please contact administrator",
                "lbl_acc_is_suspended": "Your account is suspended. Please contact Fleet Administrator",
                "lbl_otp_sent": "OTP Sent",
                "lbl_otp_resent": "OTP sending failed. Please resend",
                "lbl_provide_all_params": "Please provide all necessary params",
                "lbl_invalid_otp": "Invalid OTP. Please try again.",
                "lbl_success": "Success",
                "lbl_mob_doesnot_exist": "User with the provided mobile number does not exists in the system. Please try signing up",
                "lbl_prof_upd_failed": "Profile Update Failed",
                "lbl_loc_upd_failed": "Location Update Failed",
                "lbl_upd_success": "Successfully Updated",
                "lbl_ass_del_success": "Assistant Deleted Successfully",
                "lbl_invalid_ass": "Invalid Assistant",
                "lbl_invalid_app_user": "This mobile number is already associated with Driver App",
                "lbl_invalid_driver": "This mobile number is already associated with User App",
                "lbl_invalid_service_type": "Invalid Service",
                "lbl_invalid_transfer_type": "Invalid Transfer Type",
                "lbl_invalid_commodity": "Invalid Commodity",
                "lbl_select_commodity": "Please select commodity",
                "lbl_transfer_submitted": "Transfer Request submitted",
                "lbl_invalid_city": "Invalid City",
                "lbl_invalid_transfer_request": "Invalid Transfer Request",
                "lbl_trip_already_accepted": "The trip has been accepted by another driver",
                "lbl_invalid_transfer": "Invalid Transfer ID",
                "lbl_invalid_transfer_location": "Invalid Transfer Location",
                "lbl_transfer_not_completed": "The transfer is not completed. Please complete it to continue.",
                "lbl_transfer_is_already_started": "The transfer has already begun. Then you can not cancel this transfer.",
                "lbl_driver_rating_already_exist": "The rating already added for this driver",
                "lbl_rating_added_driver": "The rating is added for this driver",
                "lbl_user_rating_already_exist": "The rating already added for this user",
                "lbl_rating_added_user": "The rating is added for this user",
                "lbl_trip_not_started": "The trip is not started",
                "lbl_trip_is_already_completed": "This trip has already been completed",
                "lbl_advance_not_received": "The advance amount is not received for this transfer",
                "lbl_damage_report_success": "Reported Successfully",
                "lbl_location_saved": "The Location has been saved",
                "lbl_location_already_save": "The Location is already saved",
                "lbl_trip_cancelled": "Your trip has been canceled",
                "lbl_no_vehicle_message": "Driver don't have any vehicle attached",
                "lbl_push_notification_trip_accepted_heading": "Transfer Accepted",
                "lbl_push_notification_trip_accepted_message": "The transfer you have requested has been accepted by ",
                "lbl_push_notification_trip_completed_heading": "Transfer Completed",
                "lbl_push_notification_trip_completed_message": "The transfer you have requested has been completed",
                "lbl_push_notification_trip_started_heading": "Transfer Started",
                "lbl_push_notification_trip_loading_heading": "Loading Started",
                "lbl_push_notification_trip_loading_message": "Your items are being loaded to the truck.",
                "lbl_push_notification_trip_started_message": "The transfer you have reserved has been started",
                "lbl_push_notification_trip_already_accepted_heading": "Already accepted",
                "lbl_push_notification_trip_already_accepted_message": "The transfer has been already accepted by other driver",
                "lbl_transfer_accepted_by": "Your transfer request has been accepted by ",
                "lbl_driver_name": "Driver Name",
                "lbl_reg_no": "Vehicle Registration No",
                "lbl_volume": "Vehicle Volume",
                "lbl_transfer_volume": "Trip Volume",
                "lbl_payable": "Payable Amount",
                "lbl_payment_mode": "Payment Mode",
                "lbl_fully_paid": "Fully Paid",
                "lbl_scheduled_time": "Scheduled Time",
                "lbl_pickup": "Pickup",
                "lbl_drop": "Drop",
                "lbl_sl_no": "Sl.No.",
                "lbl_name": "Name",
                "lbl_plug_in": "Plug In",
                "lbl_quantity": "Quantity",
                "lbl_yes": "Yes",
                "lbl_no": "No",
                "lbl_thanks": "Thanks for choosing",
                "lbl_commodities": "Commodities",
                "lbl_transfer_confirmed": "Transfer Confirmed",
                "lbl_transfer_auto_cancelled": "Transfer Auto Cancelled",
                "lbl_trip_amount": "Trip Amount",
                "lbl_pending_approval": "Please bring your truck and original documents to our office along with a security deposit " \
                          "of S/. {0} Sol for inspection and approval.",
                "lbl_pending_approval_new": "Please bring your truck and original documents to our office for inspection and approval.",
                "lbl_completed": "Completed",
                "lbl_no_commodity_in_location": "No commodities found in this location",

                "lbl_refund_requested": "Refund requested for your transfer on {0}, as you cancelled the transfer.",
                "lbl_refund_requested_heading": "Refund Requested",
                "lbl_trip_cancelled_heading": "Trip canceled",
                "lbl_trip_cancelled_by_user": "The trip you accepted have been canceled by user. We will find you in another trip",
                "lbl_new_transfer_request": "New transfer request from a user {0}, which is {1} away from your location.",
                "lbl_new_transfer_request_heading": "Trip Request",
                "lbl_service_not_available": "Sorry, your service can not be served, because you are outside the city's range of action.",
                "lbl_truck_types": "Truck Types",
                "lbl_trip_assign_notification": "New Ride is assigned",
                "lbl_trip_assign_message": "Admin assigned new ride to you"
            }

        else:
            language_dict = {
                "lbl_provide_access_token": "POR FAVOR PROPORCIONE UN TOKEN DE ACCESO",
                "lbl_session_expired": "SESIÓN EXPIRADA",
                "lbl_acc_not_active": "Su cuenta no está activa. Por favor contacte al administrador",
                "lbl_acc_is_blocked": "Tu cuenta está bloqueada Por favor contacte al administrador",
                "lbl_acc_is_suspended": "Tu cuenta está suspendida. Por favor, póngase en contacto con el administrador",
                "lbl_otp_sent": "OTP enviado",
                "lbl_otp_resent": "El envío de OTP falló. Por favor, reenviar",
                "lbl_provide_all_params": "Proporcione todos los parámetros necesarios",
                "lbl_invalid_otp": "OTP inválido Inténtalo de nuevo.",
                "lbl_success": "Éxito",
                "lbl_mob_doesnot_exist": "User with the provided mobile number does not exist in the system. Please try signing up",
                "lbl_prof_upd_failed": "La actualización del perfil falló",
                "lbl_loc_upd_failed": "Actualización de ubicación fallida",
                "lbl_upd_success": "Actualizado exitosamente",
                "lbl_ass_del_success": "Asistente eliminado con éxito",
                "lbl_invalid_ass": "Asistente inválido",
                "lbl_invalid_app_user": "Este número de móvil ya está asociado con la aplicación de controlador",
                "lbl_invalid_driver": "Este número de móvil ya está asociado con la aplicación de usuario",
                "lbl_invalid_service_type": "Servicio inválido",
                "lbl_invalid_transfer_type": "Tipo de transferencia no válido",
                "lbl_invalid_commodity": "Mercancía no válida",
                "lbl_select_commodity": "Por favor seleccione mercancía",
                "lbl_transfer_submitted": "Solicitud de transferencia enviada",
                "lbl_invalid_city": "Ciudad inválida",
                "lbl_invalid_transfer_request": "Solicitud de transferencia inválida",
                "lbl_trip_already_accepted": "El viaje ha sido aceptado por otro conductor",
                "lbl_invalid_transfer": "ID de transferencia inválida",
                "lbl_invalid_transfer_location": "Ubicación de transferencia no válida",
                "lbl_transfer_not_completed": "La transferencia no se completa. Por favor, complétalo para continuar.",
                "lbl_transfer_is_already_started": "La transferencia ya ha comenzado. Entonces no puedes cancelar esta transferencia.",
                "lbl_driver_rating_already_exist": "La calificación ya agregada para este controlador",
                "lbl_rating_added_driver": "La calificación se agrega para este controlador",
                "lbl_user_rating_already_exist": "La calificación ya agregada para este usuario",
                "lbl_rating_added_user": "La calificación se agrega para este usuario",
                "lbl_trip_not_started": "El viaje no se inició",
                "lbl_trip_is_already_completed": "Este viaje ya ha sido completado",
                "lbl_advance_not_received": "El monto del anticipo no se recibe para esta transferencia",
                "lbl_damage_report_success": "Reportado exitosamente",
                "lbl_location_saved": "La ubicación se ha guardado",
                "lbl_location_already_save": "La ubicación ya está guardada",
                "lbl_trip_cancelled": "Su viaje ha sido cancelado",
                "lbl_no_vehicle_message": "El conductor no tiene ningún vehículo conectado",
                "lbl_push_notification_trip_accepted_heading": "Transferencia aceptada",
                "lbl_push_notification_trip_accepted_message": "El viaje que ha solicitado ha sido aceptado por el conductor ",
                "lbl_push_notification_trip_completed_heading": "Transferencia completada",
                "lbl_push_notification_trip_completed_message": "La transferencia que ha solicitado ha sido completada",
                "lbl_push_notification_trip_started_heading": "Transferencia iniciada",
                "lbl_push_notification_trip_started_message": "La transferencia que ha reservado ha sido iniciada",
                "lbl_push_notification_trip_loading_heading": "Cargando iniciado",
                "lbl_push_notification_trip_loading_message": "Tus artículos se están cargando en el camión",
                "lbl_push_notification_trip_already_accepted_heading": "Ya aceptada",
                "lbl_push_notification_trip_already_accepted_message": "La transferencia ya ha sido aceptada por otro conductor",
                "lbl_transfer_accepted_by": "Su solicitud de Servicio ha sido aceptada por ",
                "lbl_driver_name": "Conductor",
                "lbl_reg_no": "Placa vehículo",
                "lbl_volume": "Volumen de carga",
                "lbl_transfer_volume": "Volumen de transferencia",
                "lbl_payable": "Importe a pagar",
                "lbl_payment_mode": "Pago en",
                "lbl_fully_paid": "Totalmente pagado",
                "lbl_scheduled_time": "Hora programada",
                "lbl_pickup": "Recoger",
                "lbl_drop": "Entregar",
                "lbl_sl_no": "Si. No.",
                "lbl_name": "Nombre",
                "lbl_plug_in": "Enchufar",
                "lbl_quantity": "Cantidad",
                "lbl_yes": "Sí",
                "lbl_no": "No",
                "lbl_thanks": "Gracias por elegir",
                "lbl_commodities": "Productos básicos",
                "lbl_transfer_confirmed": "Servicio Confirmado",
                "lbl_transfer_auto_cancelled": "Transferencia automática cancelada",
                "lbl_trip_amount": "Monto del viaje",
                "lbl_pending_approval": "Por favor acercarse con su vehículo y documentos originales a las oficinas de Muberz, además de comprobante de deposito de S/. {0} para inspección y aprobación.",
                "lbl_pending_approval_new": "Por favor traiga su camión y documentos originales a nuestra oficina para su inspección y aprobación",
                "lbl_completed": "Completado",
                "lbl_no_commodity_in_location": "No se encontraron productos en esta ubicación",

                "lbl_refund_requested": " Reembolso solicitado para tu viaje en {0},  debido a que canceló su viaje.",
                "lbl_refund_requested_heading": " Reembolso solicitado",
                "lbl_trip_cancelled_heading": "Viaje Cancelado",
                "lbl_trip_cancelled_by_user": "El viaje que usted aceptó ha sido cancelado por el usuario.  Le asignaremos un nuevo viaje.",
                "lbl_new_transfer_request": "Nuevo requerimiento de viaje del usuario {0}, el cual esta {1} de distancia desde tu ubicación.",
                "lbl_new_transfer_request_heading": "Requerimiento de viaje",
                "lbl_service_not_available": "Disculpe, su servicio no puede ser atendido, por encontrarse fuera del rango de acción de la ciudad.",
                "lbl_truck_types": "Tipos de camiones",
                "lbl_trip_assign_notification": "Se asigna un nuevo paseo.",
                "lbl_trip_assign_message": "El administrador te asignó un nuevo viaje"

            }
        return language_dict[word]

lang_obj = LanguageConversion()


def test_confirm_mail(transfer_id):
    from api_base.models import Transfer, VehicleDetails, TransferCommodity, TransferLocation
    from django.db import models
    from threading import Thread
    import pytz

    transfer_obj = Transfer.objects.get(id=transfer_id)
    driver_vehicle = VehicleDetails.objects.filter(driver_id=transfer_obj.driver).latest('id')
    transfer_commodities = TransferCommodity.objects.filter(
        transfer_loc_id__transfer_id=transfer_obj, transfer_loc_id__loc_type="pickup").values(
        'item__item_name', 'need_plugged').distinct().annotate(models.Count('item'))

    transfer_locations = TransferLocation.objects.filter(
        transfer_id=transfer_obj).values('loc_type', 'location_name')

    context = {
        "transfer": transfer_obj,
        "driver": transfer_obj.driver,
        "reg_no": driver_vehicle.reg_no or "",
        "vehicle_volume": driver_vehicle.vehicle_volume,
        "commodities": transfer_commodities,
        "lbl_transfer_accepted_by": lang_obj.get_lang_word('en', 'lbl_transfer_accepted_by'),
        "lbl_driver_name": lang_obj.get_lang_word('en', 'lbl_driver_name'),
        "lbl_reg_no": lang_obj.get_lang_word('en', 'lbl_reg_no'),
        "lbl_volume": lang_obj.get_lang_word('en', 'lbl_volume'),
        "lbl_transfer_volume": lang_obj.get_lang_word('en', 'lbl_transfer_volume'),
        "lbl_payable": lang_obj.get_lang_word('en', 'lbl_payable'),
        "lbl_payment_mode": lang_obj.get_lang_word('en', 'lbl_payment_mode'),
        "lbl_fully_paid": lang_obj.get_lang_word('en', 'lbl_fully_paid'),
        "lbl_scheduled_time": lang_obj.get_lang_word('en', 'lbl_scheduled_time'),
        "lbl_pickup": lang_obj.get_lang_word('en', 'lbl_pickup'),
        "lbl_drop": lang_obj.get_lang_word('en', 'lbl_drop'),
        "lbl_sl_no": lang_obj.get_lang_word('en', 'lbl_sl_no'),
        "lbl_name": lang_obj.get_lang_word('en', 'lbl_name'),
        "lbl_plug_in": lang_obj.get_lang_word('en', 'lbl_plug_in'),
        "lbl_quantity": lang_obj.get_lang_word('en', 'lbl_quantity'),
        "lbl_yes": lang_obj.get_lang_word('en', 'lbl_yes'),
        "lbl_no": lang_obj.get_lang_word('en', 'lbl_no'),
        "lbl_thanks": lang_obj.get_lang_word('en', 'lbl_thanks'),
        "lbl_commodities": lang_obj.get_lang_word('en', 'lbl_commodities'),
        "lbl_transfer_confirmed": lang_obj.get_lang_word('en', 'lbl_transfer_confirmed'),
    }

    for location in transfer_locations:
        context[location['loc_type']] = location['location_name'] or ""

    if not transfer_obj.instant_search:
        target_timezone = pytz.timezone('America/Lima')
        scheduled_time = transfer_obj.transfer_on.astimezone(target_timezone)
        context["scheduled_time"] = scheduled_time

    message = get_template('dashboard/email-templates/transfer-confirm-mail.html').render(context)
    # Starting a new thread for sending confirmation mail
    email_thread = Thread(target=send_template_email,
                          args=("Transfer confirmed", message, ['maneesh@goodbits.in']))
    email_thread.start()  # Starts thread
    email_thread.join()


# Decorator for checking the permission of the operator
def disable_operator_permission(login_url='/'):
    """

    :param login_url:
    :return:
    """

    def operator_permission(func):
        def verify(request, *args, **kwargs):
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                if admin_profile.user_type == 'operator':
                    return redirect(reverse('dashboard:404'))
                else:
                    pass
            except BaseProfile.DoesNotExist:
                return redirect(login_url)
            return func(request, *args, **kwargs)
        return verify

    return operator_permission


def auto_cancelled_email_to_admin(transfer):

    # try:

    # MAIL NOTIFICATION TO CITY ADMIN
    try:
        context={}
        transfer_commodities = TransferCommodity.objects.filter(
            transfer_loc_id__transfer_id=transfer, transfer_loc_id__loc_type="pickup").values(
            'item__item_name', 'need_plugged').distinct().annotate(models.Count('item'))

        transfer_locations = TransferLocation.objects.filter(
            transfer_id=transfer).values('loc_type', 'location_name')
        logger_me.debug('transfer-id' + str(transfer.id))
        logger_me.debug('auto_cancelled_email_to_admin1')

        context = {
            "transfer": transfer,
            "cancellation_comment": transfer.cancel_comments,
            "driver": transfer.driver,
            "commodities": transfer_commodities,
            "lbl_transfer_accepted_by": lang_obj.get_lang_word('es',
                                                               'lbl_transfer_accepted_by'),
            "lbl_driver_name": lang_obj.get_lang_word('es', 'lbl_driver_name'),
            "lbl_transfer_auto_cancelled": lang_obj.get_lang_word('es', 'lbl_transfer_auto_cancelled'),
            "lbl_reg_no": lang_obj.get_lang_word('es', 'lbl_reg_no'),
            "lbl_volume": lang_obj.get_lang_word('es', 'lbl_volume'),
            "lbl_transfer_volume": lang_obj.get_lang_word('es', 'lbl_transfer_volume'),
            "lbl_payable": lang_obj.get_lang_word('es', 'lbl_payable'),
            "lbl_payment_mode": lang_obj.get_lang_word('es', 'lbl_payment_mode'),
            "lbl_fully_paid": lang_obj.get_lang_word('es', 'lbl_fully_paid'),
            "lbl_scheduled_time": lang_obj.get_lang_word('es', 'lbl_scheduled_time'),
            "lbl_pickup": lang_obj.get_lang_word('es', 'lbl_pickup'),
            "lbl_drop": lang_obj.get_lang_word('es', 'lbl_drop'),
            "lbl_sl_no": lang_obj.get_lang_word('es', 'lbl_sl_no'),
            "lbl_name": lang_obj.get_lang_word('es', 'lbl_name'),
            "lbl_plug_in": lang_obj.get_lang_word('es', 'lbl_plug_in'),
            "lbl_quantity": lang_obj.get_lang_word('es', 'lbl_quantity'),
            "lbl_yes": lang_obj.get_lang_word('es', 'lbl_yes'),
            "lbl_no": lang_obj.get_lang_word('es', 'lbl_no'),
            "lbl_thanks": lang_obj.get_lang_word('es', 'lbl_thanks'),
            "lbl_commodities": lang_obj.get_lang_word('es', 'lbl_commodities'),
            "lbl_transfer_confirmed": lang_obj.get_lang_word('es',
                                                             'lbl_transfer_confirmed'),
            "lbl_trip_amount": lang_obj.get_lang_word('es', 'lbl_trip_amount'),
        }
        if transfer.driver:
            driver_vehicle = VehicleDetails.objects.filter(driver_id=transfer.driver)
            if driver_vehicle:
                context["reg_no"] = driver_vehicle.reg_no[0] or ""
                context["vehicle_volume"] = driver_vehicle[0].vehicle_volume
        logger_me.debug('auto_cancelled_email_to_admin2')
        for location in transfer_locations:
            context[location['loc_type']] = location['location_name'] or ""

        if not transfer.instant_search:
            target_timezone = pytz.timezone('America/Lima')
            scheduled_time = transfer.transfer_on.astimezone(target_timezone).strftime("%d-%m-%Y %I:%M %p")
            context["scheduled_time"] = scheduled_time
        logger_me.debug('auto_cancelled_email_to_admin3')
        # Starting a new thread for sending confirmation mail
        city_admins = BaseProfile.objects.filter(user_type='admin_user', status='active', city=transfer.city)
        logger_me.debug('auto_cancelled_email_to_admin4')
        for admin in city_admins:
            logger_me.debug('admin')
            logger_me.debug(admin)
            try:
                message = get_template('dashboard/email-templates/mail_auto_cancelled.html').render(context)
                email_thread = threading.Thread(
                    target=send_template_email,
                    args=(lang_obj.get_lang_word('es', 'lbl_transfer_auto_cancelled'),
                          message, [admin.user.email]))
                email_thread.start()  # Starts thread
            except Exception as e:
                logger_me.debug(str(e))

            logger_me.debug('mail sent')
        # MAIL NOTIFICATION TO CITY ADMIN

        # except:
        #     pass
    except Exception as e:
        logger_me.debug("Trip error")
        logger_me.debug(str(e))
    return 1
