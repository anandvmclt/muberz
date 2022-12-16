# -*- coding: utf-8 -*-
from datetime import timedelta
from threading import Thread

from django.db.models import Avg
from django.db.models import Q
from django.utils.decorators import method_decorator
from django_api_base.api_base import *
from django_api_base.utils import send_template_email
from django_api_base.utils import random_number_generator
from push_notifications.models import APNSDevice
from push_notifications.models import GCMDevice
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api_base.default import *
from api_base.default import send_sms_twilio, get_distance_matrix, get_location_name, LanguageConversion
from api_base.models import *
from api_base.search_driver import SearchDrivers, create_notification, send_push_notification, delete_notification
from api_base.serializers import CommoditySerializer, ServiceSerializer, TransferTypeSerializer
# from dashboard.payout import calculate_driver_payout
from dashboard.payout import calculate_driver_payout
from Muberz.settings import get_config, LIVE_ENV

lang_obj = LanguageConversion()

logger_me = logging.getLogger('debug')

white_listed_mobile_numbers = ['+918893625121', '+919495274267', '+51940496176', '+51997880679', '+918281727497',
                               '+918547789587', '+918281352457', '+919539576687', '+918281709967', '+919562168314',
                               '+917349554683', '+918547863695', '+918891802218', '+919446330504', '+917012731225',
                               '+918089848062', '+919633144006', '+918129460051', '+51940496176', '+51997880679',
                               '+51985534240', '+919847191829', '+111111111111', '+51989029590', '+51985534240',
                               '+919446439494', '+916282311231', '+912349875567', '+914455667744', '+913366778899',
                               '+12029993756', '+917012529039', '+919074989337', '+919048031397']


def verify_access_token(func):
    def verify(request, *args, **kwargs):
        flag = StatusCode.HTTP_400_BAD_REQUEST
        access_token = request.META.get('HTTP_ACCESS_TOKEN')
        language = request.META.get('HTTP_LANGUAGE')
        if access_token is not None:
            try:
                access_token = AccessToken.objects.get(token=access_token, expires__gte=timezone.now().date())
                request.user_profile = BaseProfile.objects.get(user=access_token.user)
                if language == '':
                    request.language = 'en'
                else:
                    request.language = language
                    request.user_profile.set_language(language)
            except AccessToken.DoesNotExist:
                dic = {"message": "SESSION EXPIRED"}
                flag = StatusCode.HTTP_401_UNAUTHORIZED
                return JsonWrapper(dic, flag)

            except BaseProfile.DoesNotExist:
                pass

        else:
            dic = {"message": "PLEASE PROVIDE AN ACCESS TOKEN"}
            return JsonWrapper(dic, flag)

        return func(request, *args, **kwargs)

    return verify


def get_no_assistant(volume, city):
    no_assistants = 1
    try:
        crew_obj = TruckCrew.objects.get(capacity_from__lte=volume, capacity_to__gte=volume, added_by__city=city)
        no_assistants = crew_obj.loading_peoples
    except TruckCrew.DoesNotExist:
        pass
    return no_assistants


def get_security_deposit(volume, city):
    deposit_needed = 645
    try:
        deposit_obj = SecurityDeposit.objects.get(capacity_from__lte=volume, capacity_to__gte=volume,
                                                  added_by__city=city)
        deposit_needed = deposit_obj.deposit_needed
    except SecurityDeposit.DoesNotExist:
        pass
    return deposit_needed


class UpdateRegKey(ApiView):
    """
    An api for Update Reg Key for device
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request):
        dic = {}
        user_id = request.user_profile.user
        registration_id = request.DATA.get('reg_id', '')
        device_type = request.DATA.get('device_type', '')

        if registration_id not in self.NULL_VALUE_VALIDATE:
            # DELETE ALL EXISTING RECORDS AND ADD NEW
            GCMDevice.objects.filter(Q(user=user_id) | Q(registration_id=registration_id)).delete()
            APNSDevice.objects.filter(Q(user=user_id) | Q(registration_id=registration_id)).delete()
            if device_type == 'android':
                token_obj = GCMDevice(user=user_id, cloud_message_type='FCM')
                token_obj.registration_id = registration_id
                token_obj.save()
                dic['message'] = "Added"
            else:
                token_obj = APNSDevice(user=user_id)
                token_obj.registration_id = registration_id
                token_obj.save()
                dic['message'] = "Added"
            self.flag = StatusCode.HTTP_200_OK
        else:
            dic['message'] = "Invalid Registration ID"
            self.flag = StatusCode.HTTP_403_FORBIDDEN

        return JsonWrapper(dic, self.flag)


class RemoveDevice(ApiView):
    """
    An api for Remove Device
    """

    @method_decorator(get_raw_data)
    @method_decorator(verify_access_token)
    def post(self, request):
        dic = {}
        registration_id = request.DATA.get('reg_id', '')
        device_type = request.DATA.get('device_type', '')
        user_id = request.user_profile.user

        if registration_id not in self.NULL_VALUE_VALIDATE:
            # checking if the register id exists or not
            if device_type == 'android':
                GCMDevice.objects.filter(user=user_id, registration_id=registration_id).delete()
            else:
                APNSDevice.objects.filter(user=user_id, registration_id=registration_id).delete()
            # REMOVE ACCESS TOKEN
            AccessTokenManagement.delete_access_token_permission(user_id)
            dic['message'] = "Removed"
            self.flag = StatusCode.HTTP_200_OK

        else:
            dic['message'] = "Invalid Registration ID"
            self.flag = StatusCode.HTTP_403_FORBIDDEN

        return JsonWrapper(dic, self.flag)


class UserSignupApi(ApiView):
    """Api for the user to create a new user if not exists and send otp"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        mobile_number = request.DATA.get('mobile_number', '')
        hash_key = request.DATA.get('hash_key', '')
        language = request.META.get('HTTP_LANGUAGE')
        if language == '':
            request.language = 'en'
        else:
            request.language = language

        signup_flag = False
        if User.objects.filter(username=mobile_number).exists():
            user_obj = User.objects.get(username=mobile_number)
        else:
            signup_flag = True
            user_obj = User.objects.create_user(username=mobile_number)
            user_obj.status = 'active'
            user_obj.save()
        if not user_obj.is_active:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_acc_not_active')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        else:
            try:
                user_profile = BaseProfile.objects.get(user=user_obj)
            except BaseProfile.DoesNotExist:
                user_profile = BaseProfile.objects.create(user=user_obj, user_type='app_user')
            if signup_flag:
                user_profile.is_new_user = True
                user_profile.status = 'active'
                user_obj.status = 'active'
            user_obj.save()
            user_profile.save()

            if user_profile.user_type == 'app_user':
                user_profile.set_otp()
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_otp_sent')
                self.flag = StatusCode.HTTP_200_OK
                
                #TODO Uncomment later.
                # user_profile.set_otp()
                # otp_text = "<#> " + user_profile.raw_otp + " is your verification code for Muberz User App. \n" + hash_key
                # if send_sms_twilio(mobile_number, otp_text) == 200:
                #     logger_me.debug(request.language)
                #     logger_me.debug('----request.language')
                #     dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_otp_sent')
                #     self.flag = StatusCode.HTTP_200_OK
                # else:
                #     dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_otp_resent')
                #     self.flag = StatusCode.HTTP_400_BAD_REQUEST
            
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_app_user')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            user_profile.save()

        return JsonWrapper(dic, self.flag)


class UserLoginApi(ApiView):
    """Api for the user to login and get the access credentials and other details"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        mobile_number = request.DATA.get('mobile_number', '')
        password = request.DATA.get('otp', '')
        language = request.META.get('HTTP_LANGUAGE')
        # device_id = request.META.get('HTTP_DEVICE')
        device_id = random_number_generator()
        if language == '':
            request.language = 'en'
        else:
            request.language = language

        if mobile_number and password != '':
            try:
                user = User.objects.get(username=mobile_number)
                user_profile = BaseProfile.objects.get(user=user)
                if user_profile.verify_otp(password):
                    if user.is_active:
                        try:
                            notifications_settings = NotificationsSettings.objects.get(user_profile=user_profile)
                        except NotificationsSettings.DoesNotExist:
                            notifications_settings = NotificationsSettings.objects.create(user_profile=user_profile,
                                                                                          promotions=True,
                                                                                          momentalert=True)
                            notifications_settings.save()
                        user_profile.no_tokens = 10
                        user_profile.save()

                        dic['full_name'] = user.last_name
                        dic['email'] = user.email
                        # print(user_profile)
                        tokens = SingleAccessTokenManagement.initialise_access_token(device_id, user)
                        if tokens[0]:
                            dic["access_token"] = tokens[0].token
                            dic["refresh_token"] = tokens[1].token

                        # dic['access_token'] = user_profile.get_access_token()
                        dic['user_type'] = user_profile.user_type
                        dic['user_id'] = user_profile.id
                        dic['is_new_user'] = user_profile.is_new_user

                        dic['location'] = {
                            'lat': user_profile.current_lat,
                            'long': user_profile.current_lng,
                        }
                        dic['settings'] = {
                            'promotions': notifications_settings.promotions,
                            'moment_alert': notifications_settings.momentalert,
                        }
                        # ################################
                        dic['rating'] = round(user_profile.rating, 1)
                        # #################################
                        dic['email'] = user_profile.user.email
                        dic['mobile_number'] = str(user_profile.user.username)
                        dic['designation'] = user_profile.designation
                        dic['profile_image'] = user_profile.profile_pic
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_success')
                        self.flag = StatusCode.HTTP_200_OK
                        user_profile.no_tokens = 10
                        user_profile.save()

                    else:
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_acc_not_active')
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
                elif mobile_number in white_listed_mobile_numbers:
                    if user.is_active:
                        try:
                            notifications_settings = NotificationsSettings.objects.get(user_profile=user_profile)
                        except NotificationsSettings.DoesNotExist:
                            notifications_settings = NotificationsSettings.objects.create(user_profile=user_profile,
                                                                                          promotions=True,
                                                                                          momentalert=True)
                            notifications_settings.save()
                        user_profile.no_tokens = 10
                        user_profile.save()

                        dic['full_name'] = "{0} {1}".format(user.first_name, user.last_name)
                        dic['email'] = user.email
                        # print(user_profile)
                        tokens = SingleAccessTokenManagement.initialise_access_token(device_id, user)
                        if tokens[0]:
                            dic["access_token"] = tokens[0].token
                            dic["refresh_token"] = tokens[1].token

                        # dic['access_token'] = user_profile.get_access_token()
                        dic['user_type'] = user_profile.user_type
                        dic['user_id'] = user_profile.id
                        dic['is_new_user'] = user_profile.is_new_user
                        dic['location'] = {
                            'lat': user_profile.current_lat,
                            'long': user_profile.current_lng,
                        }
                        dic['settings'] = {
                            'promotions': notifications_settings.promotions,
                            'moment_alert': notifications_settings.momentalert,
                        }
                        # ################################
                        dic['rating'] = round(user_profile.rating, 1)
                        # #################################
                        dic['email'] = user_profile.user.email
                        dic['mobile_number'] = str(user_profile.user.username)
                        dic['designation'] = user_profile.designation
                        dic['profile_image'] = user_profile.profile_pic
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_success')
                        self.flag = StatusCode.HTTP_200_OK
                        user_profile.no_tokens = 10
                        user_profile.save()
                else:
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_otp')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST

            except User.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_mob_doesnot_exist')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            except BaseProfile.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_mob_doesnot_exist')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


# REST API COMMODITY LISTING VIEW
# @method_decorator(verify_access_token())

class TransferTypeListingView(ListAPIView):
    @method_decorator(verify_access_token)
    def list(self, request, *args, **kwargs):
        queryset = TransferType.objects.all()
        serializer = TransferTypeSerializer(queryset, many=True)
        return Response({'status': 200, 'data': serializer.data})


class CommodityListingView(ListAPIView):
    @method_decorator(verify_access_token)
    def list(self, request, *args, **kwargs):
        queryset = Commodity.objects.all()
        serializer = CommoditySerializer(queryset, many=True)
        return Response({'status': 200, 'data': serializer.data})


# REST API SERVICE LISTING VIEW
# @method_decorator(verify_access_token())

class ServiceListingView(ListAPIView):
    @method_decorator(verify_access_token)
    def list(self, request, *args, **kwargs):
        queryset = Service.objects.all()
        serializer = ServiceSerializer(queryset, many=True)
        return Response({'status': 200, 'data': serializer.data})


# API SERVICE FOR PROFILE UPDATE
@method_decorator(verify_access_token, name='dispatch')
class UpdateUserProfile(ApiView):

    def get(self, request):
        dic = {}
        dic['name'] = request.user_profile.user.first_name
        dic['email'] = request.user_profile.user.email
        request.language = request.META.get('HTTP_LANGUAGE')
        dic['profile_pic'] = request.user_profile.profile_pic
        dic['drive_status'] = request.user_profile.drive_status

        dic['status'] = request.user_profile.status
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)

    @method_decorator(get_raw_data)
    def post(self, request):
        dic = {}
        full_name = request.DATA.get('full_name', '')
        email = request.DATA.get('email', '')
        profile_image = request.DATA.get('profile_image', '')
        try:
            user_profile = BaseProfile.objects.get(id=request.user_profile.id)
            user_profile.user.first_name = full_name
            user_profile.user.last_name = ''
            user_profile.user.email = email
            user_profile.user.save()
            user_profile.is_new_user = False
            user_profile.profile_pic = profile_image
            user_profile.save()
            dic['full_name'] = user_profile.user.first_name
            dic['email'] = user_profile.user.email
            dic['profile_image'] = user_profile.profile_pic
            self.flag = StatusCode.HTTP_200_OK
        except BaseProfile.DoesNotExist:
            dic = {"message": lang_obj.get_lang_word(request.language, 'lbl_session_expired')}
            self.flag = StatusCode.HTTP_401_UNAUTHORIZED
        except:
            dic = {"message": lang_obj.get_lang_word(request.language, 'lbl_prof_upd_failed')}
            self.flag = StatusCode.HTTP_503_SERVICE_UNAVAILABLE

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class UpdateNotificationSettingsApi(ApiView):
    """Api for the user to Update Notification Settings for UserApp and Partner APp"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        promotions = request.DATA.get('promotions', '')
        momentalert = request.DATA.get('momentalert', '')
        user_profile = request.user_profile
        try:
            notifications_settings = NotificationsSettings.objects.get(user_profile=user_profile)
            notifications_settings.promotions = promotions
            notifications_settings.momentalert = momentalert
            notifications_settings.save()
        except NotificationsSettings.DoesNotExist:
            notifications_settings = NotificationsSettings.objects.get_or_create(user_profile=user_profile,
                                                                                 promotions=True,
                                                                                 momentalert=True)
            notifications_settings.save()
        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class CommodityListCityBasedApi(ApiView):
    """
     Api for the  to list the commodity based on city of transfer
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        commodity_list = []
        pickup_lat = request.DATA.get('pickup_lat', '')
        pickup_lng = request.DATA.get('pickup_lng', '')
        drop_lat = request.DATA.get('drop_lat', '')
        drop_lng = request.DATA.get('drop_lng', '')

        location_name = get_city_from_location(pickup_lat, pickup_lng)
        logger_me.debug("COMMODITY_LISTING_LOCATION_NAME : {0}".format(location_name))

        try:
            city_obj = City.objects.get(city_name=location_name)
            cashorcard = city_obj.cash_only
            logger_me.debug("COMMODITY_LISTING_CITY_ID : {0}".format(city_obj.id))
            commodities = Commodity.objects. \
                filter(city=city_obj).extra(select={'lower_name': 'lower(item_name)'}).order_by('lower_name')
            for commodity_obj in commodities:
                commodity_dict = {}
                commodity_dict['id'] = commodity_obj.id
                commodity_dict['item_name'] = commodity_obj.item_name
                commodity_dict['volume'] = commodity_obj.volume
                commodity_dict['image'] = commodity_obj.image
                commodity_dict['charge'] = commodity_obj.charge
                commodity_dict['material_type'] = commodity_obj.material_type
                commodity_dict['is_plugable'] = commodity_obj.is_plugable
                commodity_dict['is_cash'] = cashorcard
                commodity_list.append(commodity_dict)
            # dic = sorted(commodity_list, key=lambda i: i['item_name'])
            dic = commodity_list
            self.flag = StatusCode.HTTP_200_OK
        except City.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_no_commodity_in_location')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


class ServiceListCityBasedApi(ApiView):
    """
     Api for the  to list the Services based on city of transfer
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        service_list = []
        pickup_lat = request.DATA.get('pickup_lat', '')
        pickup_lng = request.DATA.get('pickup_lng', '')
        location_name = get_city_from_location(pickup_lat, pickup_lng)
        try:
            city_obj = City.objects.get(city_name=location_name)
            services = Service.objects.filter(city=city_obj)
            for service_obj in services:
                service_dict = {}
                service_dict['id'] = service_obj.id
                if service_obj.service_name == 'packed-packed':
                    service_dict['type'] = 1
                elif service_obj.service_name == 'unpacked-packed':
                    service_dict['type'] = 2
                else:
                    service_dict['type'] = 3
                if request.language == 'en':
                    service_dict['service_name'] = service_obj.display_service_name_en
                    service_dict['service_description'] = service_obj.service_description_en
                else:
                    service_dict['service_name'] = service_obj.display_service_name_es
                    service_dict['service_description'] = service_obj.service_description_es
                service_list.append(service_dict)
            dic = service_list
            self.flag = StatusCode.HTTP_200_OK
        except City.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_city')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


class TransferSubmitApi(ApiView):
    """
     Api for the user to Submit a transfer
    """

    @method_decorator((verify_access_token, get_raw_data))
    def put(self, request, **kwargs):
        dic = {}
        user_id = request.user_profile
        pickup_lat = str(request.DATA.get('pickup_lat', ''))
        pickup_lng = str(request.DATA.get('pickup_lng', ''))
        pickup_address = str(request.DATA.get('pickup_address', ''))
        drop_address = str(request.DATA.get('drop_address', ''))
        drop_lat = str(request.DATA.get('drop_lat', ''))
        drop_lng = str(request.DATA.get('drop_lng', ''))
        transfer_type = request.DATA.get('transfer_type', '')
        transfer_from = int(request.DATA.get('transfer_from', ''))
        transfer_to = int(request.DATA.get('transfer_to', ''))
        service = int(request.DATA.get('service', ''))
        # Get value from app 1- packed-packed , 2 - unpacked-packed, 3 - unpacked-unpacked
        commodity = request.DATA.get('commodity', '')
        transfer_on = request.DATA.get('transfer_on', '')
        from_floor = int(request.DATA.get('from_floor', ''))
        to_floor = int(request.DATA.get('to_floor', ''))
        instant_search = request.DATA.get('instant_search', '')
        is_plugged = request.DATA.get('is_plugged', '')
        source = request.DATA.get('source', 'Commodity')
        # helper_count = request.DATA.get('helper_count', 0)
        volume = request.DATA.get('volume')
        is_special_handling_required = request.DATA.get('is_special_handling_required')

        start_time = OnOffSwitch.objects.get(id=1).start_date
        end_time = OnOffSwitch.objects.get(id=1).end_date
        input_date = datetime.fromtimestamp(int(float(transfer_on)) / 1000)
        start = datetime.combine(input_date, start_time)
        end = datetime.combine(input_date + timedelta(days=1), end_time)
        logger_me.debug("the dates are")
        logger_me.debug(input_date)
        logger_me.debug(start)
        logger_me.debug(end)
        # if not start < input_date && not end < input_date:
        if not start <= input_date <= end:
            if pickup_lat and pickup_lng and drop_lat and drop_lng and transfer_on and transfer_from and transfer_to and service not in self.NULL_VALUE_VALIDATE:
                location_name = get_city_from_location(pickup_lat, pickup_lng)
                try:
                    city_obj = City.objects.get(city_name=location_name)
                    try:
                        # CALCULATE DISTANCE OF THE TRIP
                        distance, duration, duration_in_sec, trip_distance = get_distance_matrix(pickup_lat, pickup_lng,
                                                                                                 drop_lat, drop_lng)
                        try:
                            # if service == "1":
                            #     service_name = "packed-packed"
                            # elif service == "2":
                            #     service_name = "unpacked-packed"
                            # else:
                            #     service_name = "unpacked-unpacked"

                            service_obj = Service.objects.get(id=service)
                            # service_obj = Service.objects.get(service_name=service_name, city=city_obj)
                            #
                            tot_volume = 0
                            installation_charge = 0
                            discount_offered = 0
                            # commission = 13
                            total_amount = service_charge = 0
                            # damage_refund = 13
                            # penalty = 13
                            # helper_amount = 0
                            if (len(commodity) > 0 and source == 'Commodity') or source == 'Truck':
                                transfer_obj = Transfer.objects.create(no_items=len(commodity), added_by=user_id,
                                                                       city=city_obj, source=source,
                                                                       is_special_handling_required=is_special_handling_required)
                                transfer_obj.transfer_on = datetime.fromtimestamp(int(float(transfer_on)) / 1000)
                                transfer_obj.service_type = service_obj
                                transfer_obj.status = 'not_paid'
                                transfer_obj.payment_received = False
                                transfer_obj.advance_received = False
                                transfer_obj.added_by = user_id
                                transfer_obj.instant_search = instant_search
                                transfer_obj.distance = distance
                                transfer_obj.duration = duration
                                transfer_obj.save()
                                # UPDATE LOCATION TABLE FOR BOTH PICKUP AND DROP
                                pick_loc_obj = TransferLocation.objects.create(transfer_loc=transfer_from,
                                                                               loc_type='pickup',
                                                                               transfer_id=transfer_obj)
                                pick_loc_obj.loc_lat = pickup_lat
                                pick_loc_obj.loc_lng = pickup_lng
                                pick_loc_obj.floor = from_floor
                                if pickup_address != '':
                                    location_name = pickup_address
                                else:
                                    location_name = get_address_from_location(pickup_lat, pickup_lng)
                                pick_loc_obj.location_name = location_name
                                pick_loc_obj.save()
                                # UPDATE DROP LOCATION
                                drop_loc_obj = TransferLocation.objects.create(transfer_loc=transfer_to,
                                                                               loc_type='drop',
                                                                               transfer_id=transfer_obj)
                                drop_loc_obj.loc_lat = drop_lat
                                drop_loc_obj.loc_lng = drop_lng
                                drop_loc_obj.floor = to_floor
                                if drop_address != '':
                                    location_name = drop_address
                                else:
                                    location_name = get_address_from_location(drop_lat, drop_lng)
                                drop_loc_obj.location_name = location_name
                                drop_loc_obj.save()

                                commodity_helper_count_list=[]
                                for commodity_dict in commodity:
                                    quantity = commodity_dict['quantity']
                                    commodity_id = commodity_dict['commodity_id']
                                    need_plugged = commodity_dict['need_plugged']
                                    try:
                                        commodity_obj = Commodity.objects.get(id=commodity_id)
                                        commodity_helper_count_list.append(commodity_obj.loaders)
                                        count = 1
                                        while count <= int(quantity):
                                            transfer_commodity = TransferCommodity(transfer_loc_id=pick_loc_obj,
                                                                                   item=commodity_obj, added_by=user_id)
                                            transfer_commodity.need_plugged = need_plugged
                                            transfer_commodity.save()
                                            # CALCULATE TOTAL VOLUME OF THE COMMODITIES

                                            tot_volume += float(commodity_obj.volume)
                                            if need_plugged:
                                                if float(commodity_obj.installation_charge) > 0:
                                                    installation_charge += float(commodity_obj.installation_charge)
                                            count += 1
                                    except Commodity.DoesNotExist:
                                        pass
                                        # dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_commodity')
                                        # self.flag = StatusCode.HTTP_400_BAD_REQUEST
                                if (source == 'Truck'):
                                    transfer_obj.tot_volume = volume
                                else:
                                    transfer_obj.tot_volume = tot_volume
                                if float(installation_charge) > 0:
                                    transfer_obj.installation_charge = installation_charge
                                transfer_obj.save()

                                # CALCULATE SERVICE CHARGE BASED ON DISTANCE
                                # if trip_distance <= 10:
                                #     service_charge = service_obj.charge_0_10
                                # elif trip_distance <= 20:
                                #     service_charge = service_obj.charge_10_20
                                # elif trip_distance <= 30:
                                #     service_charge = service_obj.charge_20_30
                                # elif trip_distance <= 40:
                                #     service_charge = service_obj.charge_30_40
                                # elif trip_distance <= 50:
                                #     service_charge = service_obj.charge_40_50
                                # elif trip_distance <= 60:
                                #     service_charge = service_obj.charge_50_60
                                # elif trip_distance <= 70:
                                # else:
                                service_charge = service_obj.charge
                                transfer_obj.city = city_obj
                                if service_charge > 0:
                                    transfer_obj.service_charge = service_charge
                                transfer_obj.save()

                                # DENSITY FACTOR CALCULATION

                                if transfer_from == 1:
                                    density_from = 'CH'
                                elif from_floor <= 5:
                                    density_from = 'EMBD'
                                else:
                                    density_from = 'EMAD'

                                if transfer_to == 1:
                                    density_to = 'CH'
                                elif to_floor <= 5:
                                    density_to = 'EMBD'
                                else:
                                    density_to = 'EMAD'
                                transfer_obj.density_charge = 0
                                transfer_obj.save()
                                try:
                                    density_obj = TransferType.objects.get(city=city_obj, transfer_from=density_from,
                                                                           transfer_to=density_to)
                                    density_factor = density_obj.charge

                                    transfer_obj.density_charge = density_factor
                                    transfer_obj.save()
                                except TransferType.DoesNotExist:
                                    pass

                                # TOTAL CALCULATION
                                tot_volume = transfer_obj.tot_volume

                                if tot_volume < 1:
                                    tot_volume = 1
                                try:
                                    truck_crew = TruckCrew.objects.get(capacity_from__lte=tot_volume,
                                                                       capacity_to__gte=tot_volume,
                                                                       added_by__city=city_obj)
                                except TruckCrew.DoesNotExist:
                                    dic['message'] = "No Trucks are available to contain the selected commodities"
                                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
                                    return JsonWrapper(dic, self.flag)
                                # if source == 'Truck':
                                # TRUCK FACTORS
                                a = truck_crew.a
                                b = truck_crew.b
                                c = truck_crew.c
                                x = (a * (trip_distance ** 2)) + (b * trip_distance) + c

                                logger_me.debug(trip_distance)
                                # else:
                                #     x = tot_volume
                                if transfer_obj.service_charge:
                                    total_amount = (x * transfer_obj.service_charge)
                                if transfer_obj.density_charge:
                                    total_amount *= transfer_obj.density_charge
                                if transfer_obj.installation_charge:
                                    total_amount += transfer_obj.installation_charge
                                transfer_obj.total_amount = total_amount
                                transfer_obj.save()

                                try:
                                    # DISCOUNT CALCULATION
                                    discount_obj = Discount.objects.get(service_type=service_obj,
                                                                        rate_from__lte=total_amount,
                                                                        rate_to__gte=total_amount, status='active')
                                    discount = discount_obj.discount
                                    if discount > 0:
                                        discount_offered = (total_amount * discount) / 100
                                        discount_after_commision = total_amount - discount_offered
                                        transfer_obj.discount_offered = discount_offered
                                        transfer_obj.total_amount = discount_after_commision
                                        transfer_obj.save()
                                except Discount.DoesNotExist:
                                    pass

                                dic['message'] = lang_obj.get_lang_word(request.language,
                                                                        'lbl_transfer_submitted')
                                # TODO: REMOVE AFTER VISA TESTING
                                # transfer_obj.total_amount = 1
                                # transfer_obj.save()

                                dic['total_amount'] = round(transfer_obj.total_amount, 2)
                                dic['transfer_id'] = transfer_obj.id
                                if (source == 'Truck'):
                                    dic['recommended_helpers'] = truck_crew.loading_peoples
                                else:
                                    dic['recommended_helpers'] = max(commodity_helper_count_list)

                                dic['amount_per_helper'] = truck_crew.amount_per_helper
                                dic['is_cash'] = city_obj.cash_only
                                self.flag = StatusCode.HTTP_200_OK
                            else:
                                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_select_commodity')
                                self.flag = StatusCode.HTTP_400_BAD_REQUEST

                        except Service.DoesNotExist:
                            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_service_type')
                            self.flag = StatusCode.HTTP_400_BAD_REQUEST
                    except Exception as e:
                        dic['message'] = e
                        # except:
                        #     dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_request')
                        #     self.flag = StatusCode.HTTP_400_BAD_REQUEST
                except City.DoesNotExist:
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_city')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'Service is not availabe ')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        return JsonWrapper(dic, self.flag)


class PaymentSubmitApi(ApiView):
    """
     Api for the user to Submit a Payment
    """

    @method_decorator((verify_access_token, get_raw_data))
    def put(self, request, **kwargs):
        dic = {}

        transfer_id = request.DATA.get('transfer_id', '')
        payment_type = request.DATA.get('payment_type', '')
        userTokenID = request.DATA.get('userTokenID', '')  # Optional used for fetch cards in client side
        date_raw = request.DATA.get('date', '')
        transaction_id = request.DATA.get('transaction_id', '')
        eTicket = request.DATA.get('eTicket', '')
        uniqueID = request.DATA.get('uniqueID', '')
        amount = request.DATA.get('amount', '')
        status = request.DATA.get('payment_received', '')
        helper_count = request.DATA.get('helper_count', 0)

        if payment_type and transfer_id not in self.NULL_VALUE_VALIDATE:
            try:
                transfer_obj = Transfer.objects.get(id=transfer_id)

                proceed_to_search = False
                if payment_type == 'cash':
                    transfer_obj.payment_type = payment_type
                    transfer_obj.advance_amount = 0
                    transfer_obj.payable_amount = transfer_obj.total_amount
                    transfer_obj.advance_received = True
                    proceed_to_search = True
                elif payment_type == 'card':
                    # and (
                    #     date_raw and transaction_id and eTicket and uniqueID
                    #     and amount and status not in self.NULL_VALUE_VALIDATE):
                    try:
                        transaction_date = datetime.fromtimestamp(int(float(date_raw)) / 1000)
                        try:
                            if status == '000':
                                status = 'completed'
                                transfer_obj.payment_type = payment_type
                                try:
                                    if transfer_obj.total_amount - float(amount) <= 1:
                                        amount = transfer_obj.total_amount
                                except:
                                    pass
                                transfer_obj.advance_amount = amount
                                payable_amount = transfer_obj.total_amount - float(amount)
                                if abs(payable_amount) <= 1:
                                    payable_amount = 0
                                transfer_obj.payable_amount = payable_amount
                                transfer_obj.advance_received = True
                                proceed_to_search = True
                            else:
                                status = 'failed'
                            Transaction.objects.create(transfer=transfer_obj, date=transaction_date,
                                                       transactionID=transaction_id, eTicket=eTicket,
                                                       uniqueID=uniqueID, amount=amount,
                                                       status=status, payee=transfer_obj.added_by)
                            if userTokenID != '':
                                transfer_obj.added_by.visaUserToken = userTokenID
                                transfer_obj.added_by.save()
                            else:
                                logger_me.debug("% Token Error %")
                        except Exception as e:
                            dic['message'] = "Could not create Transaction"
                    except:
                        dic['message'] = "Please provide valid date & time"
                    logger_me.debug('payment completed')
                else:
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
                if proceed_to_search:
                    transfer_obj.status = 'active'
                    if transfer_obj.instant_search:
                        transfer_obj.transfer_on = timezone.now()

                    pickup_loc = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')

                    location_name = get_city_from_location(pickup_loc.loc_lat, pickup_loc.loc_lng)

                    city_obj = City.objects.get(city_name=location_name)

                    truck_crew = TruckCrew.objects.get(capacity_from__lte=transfer_obj.tot_volume,
                                                       capacity_to__gte=transfer_obj.tot_volume,
                                                       added_by__city=city_obj)

                    transfer_obj.helper_count = helper_count

                    helper_amount = truck_crew.amount_per_helper * helper_count

                    transfer_obj.total_amount += helper_amount
                    transfer_obj.special_handling_fee = transfer_obj.total_amount * 30 / 100
                    transfer_obj.save()
                    if not TruckRequest.objects.filter(transfer_id=transfer_obj):
                        try:
                            search_obj = SearchDrivers()
                            search_obj.search_drivers(transfer_obj, transfer_obj.instant_search, request.language)
                        except:
                            pass
                    if transfer_obj.instant_search:
                        transfer_obj.transfer_on = timezone.now()
                        transfer_obj.save()
                    self.flag = StatusCode.HTTP_200_OK
                else:
                    self.flag = StatusCode.HTTP_200_OK
                    dic['message'] = 'Payment Failed'
            except Transfer.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


# ######################################### PARTNER APP ##############################################


class PartnerSignupApi(ApiView):
    """Api for the user to create a new partner user if not exists and send otp"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        mobile_number = request.DATA.get('mobile_number', '')
        hash_key = request.DATA.get('hash_key', '')
        language = request.META.get('HTTP_LANGUAGE')

        if language == '':
            request.language = 'en'
        else:
            request.language = language
        signup_flag = False
        if User.objects.filter(username=mobile_number).exists():
            user_obj = User.objects.get(username=mobile_number)
        else:
            signup_flag = True
            user_obj = User.objects.create_user(username=mobile_number)
        try:
            user_profile = BaseProfile.objects.get(user=user_obj)
        except BaseProfile.DoesNotExist:
            user_profile = BaseProfile.objects.create(user=user_obj, user_type='driver', status='not_verified')
        if signup_flag:
            user_profile.is_new_user = True
            user_obj.status = 'active'
            user_obj.save()
            user_profile.save()
        user_obj.save()
        user_profile.save()
        if user_profile.status == 'blocked':
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_acc_is_blocked')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        elif user_profile.status == 'suspended':
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_acc_is_suspended')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        else:
            if user_obj.is_active:
                if user_profile.user_type == 'driver':
                    user_profile.set_otp()
                    otp_text = "<#> " + user_profile.raw_otp + " is your verification code for Muberz Driver App. \n" + hash_key
                    if send_sms_twilio(mobile_number, otp_text) == 200:
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_otp_sent')
                        self.flag = StatusCode.HTTP_200_OK
                    else:
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_otp_resent')
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
                else:
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_driver')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
                user_profile.save()
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_acc_not_active')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST

        # user_profile, created = BaseProfile.objects.get_or_create(user=user_obj)
        # user_profile.set_otp()
        # otp_text = user_profile.raw_otp + " is your verification code for Muberz Driver App."
        # send_sms_twilio(mobile_number, otp_text)
        # user_profile.user_type = 'driver'
        # user_profile.is_new_user = True
        # user_obj.save()
        # user_profile.save()
        # dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_otp_sent')
        # self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class PartnerLoginApi(ApiView):
    """Api for the Partner to login and get the access credentials and other details"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        mobile_number = request.DATA.get('mobile_number', '')
        password = request.DATA.get('otp', '')
        language = request.META.get('HTTP_LANGUAGE')
        device_id = request.META.get('HTTP_DEVICE')
        if language == '':
            request.language = 'en'
        else:
            request.language = language
        if mobile_number and password != '':
            try:
                user = User.objects.get(username=mobile_number)
                user_profile = BaseProfile.objects.get(user=user)
                if user_profile.verify_otp(password) or mobile_number in white_listed_mobile_numbers:
                    user_profile.no_tokens = 10
                    user_profile.save()

                    dic['name'] = "{0} {1}".format(user.first_name, user.last_name)
                    dic['email'] = user.email
                    # print(user_profile)
                    tokens = SingleAccessTokenManagement.initialise_access_token(device_id, user)
                    if tokens[0]:
                        dic["access_token"] = tokens[0].token
                        dic["refresh_token"] = tokens[1].token

                    # dic['access_token'] = user_profile.get_access_token()
                    # STORING DRIVE STATUS HISTORY FOR HANDLING OFFERS
                    if not DriveStatusHistory.objects.filter(driver=user_profile):
                        DriveStatusHistory.objects.create(driver=user_profile, status_from=timezone.now())
                    try:
                        notifications_settings = NotificationsSettings.objects.get(user_profile=user_profile)
                    except NotificationsSettings.DoesNotExist:
                        notifications_settings = NotificationsSettings.objects.create(user_profile=user_profile,
                                                                                      promotions=True)
                        notifications_settings.save()
                    dic['settings'] = {
                        'promotions': notifications_settings.promotions,
                    }
                    dic['user_type'] = user_profile.user_type
                    dic['user_id'] = user_profile.id
                    dic['is_new_user'] = user_profile.is_new_user
                    dic['status'] = user_profile.status  # IF STATUS IS ACTIVE THEN ONLY DRIVER CAN ACCEPT TRIPS
                    # ################################
                    dic['rating'] = round(user_profile.rating, 1)
                    # #################################
                    dic['name'] = user_profile.user.first_name
                    dic['email'] = user_profile.user.email
                    dic['mobile_number'] = str(user_profile.user.username)
                    dic['designation'] = user_profile.designation
                    dic['profile_pic'] = user_profile.profile_pic
                    if user_profile.fleet_id:
                        is_fleet = True
                    else:
                        is_fleet = False
                    dic['is_fleet'] = is_fleet

                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_success')
                    try:
                        attach = Attachments.objects.get(doc_type='fitness_certificate', driver_id=user_profile)
                        dic['fitness_certificate'] = attach.attachment
                    except Attachments.DoesNotExist:
                        dic['fitness_certificate'] = ''
                    try:
                        attach = Attachments.objects.get(doc_type='tax_certificate', driver_id=user_profile)
                        dic['tax_certificate'] = attach.attachment
                    except Attachments.DoesNotExist:
                        dic['tax_certificate'] = ''
                    try:
                        attach = Attachments.objects.get(doc_type='driver_license', driver_id=user_profile)
                        dic['driver_license'] = attach.attachment
                    except Attachments.DoesNotExist:
                        dic['driver_license'] = ''
                    try:
                        attach = Attachments.objects.get(doc_type='commercial_insurance', driver_id=user_profile)
                        dic['commercial_insurance'] = attach.attachment
                    except Attachments.DoesNotExist:
                        dic['commercial_insurance'] = ''
                    try:
                        attach = Attachments.objects.get(doc_type='registration_certificate', driver_id=user_profile)
                        dic['registration_certificate'] = attach.attachment
                    except Attachments.DoesNotExist:
                        dic['registration_certificate'] = ''
                    try:
                        vehicle_profile = VehicleDetails.objects.get(driver_id=user_profile)
                        dic['deposit_amount'] = vehicle_profile.security_deposit
                        dic['vehicle_volume'] = vehicle_profile.vehicle_volume
                    except VehicleDetails.DoesNotExist:
                        dic['deposit_amount'] = ''
                        dic['vehicle_volume'] = ''

                    # GETTING ALL SERVICEABLE AREA OF THE DRIVER
                    serviceable_areas = ServiceableArea.objects.filter(driver_id=user_profile)
                    serviceable_area_list = []
                    for serviceable_area in serviceable_areas:
                        area_dict = {}
                        area_dict['latitude'] = serviceable_area.latitude
                        area_dict['longitude'] = serviceable_area.longitude
                        area_dict['loc_name'] = serviceable_area.loc_name
                        serviceable_area_list.append(area_dict)
                    dic['serviceable_area'] = serviceable_area_list
                    try:
                        fleet_id = user_profile.fleet_id.id
                    except:
                        fleet_id = 0
                    dic['fleet_id'] = fleet_id
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')

                    self.flag = StatusCode.HTTP_200_OK
                    user_profile.no_tokens = 10
                    user_profile.save()
                else:
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_otp')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST

            except User.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_mob_doesnot_exist')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            except BaseProfile.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_mob_doesnot_exist')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class UpdatePartnerProfile(ApiView):
    """Api for showing the profile of the partner """

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        name = request.DATA.get('name', '')
        email = request.DATA.get('email', '')
        profile_pic = request.DATA.get('profile_pic', '')
        fitness_certificate = request.DATA.get('fitness_certificate', '')
        tax_certificate = request.DATA.get('tax_certificate', '')
        driver_license = request.DATA.get('driver_license', '')
        commercial_insurance = request.DATA.get('commercial_insurance', '')
        registration_certificate = request.DATA.get('registration_certificate', '')
        deposit_amount = request.DATA.get('deposit_amount', '')
        vehicle_volume = request.DATA.get('vehicle_volume', '')
        vehicle_height = request.DATA.get('vehicle_height', '')
        serviceable_area = request.DATA.get('serviceable_area', '')
        user_profile = request.user_profile
        registration_number = request.DATA.get('registration_number', '')

        if name not in self.NULL_VALUE_VALIDATE:
            user_profile.email = email
            user_profile.user.email = email
            user_profile.user.first_name = name

            if serviceable_area:
                try:
                    user_profile.city = City.objects.get(city_name=serviceable_area['loc_name'])
                    user_profile.save()
                except City.DoesNotExist:
                    error_dict = {'message': "Invalid city provided"}
                    self.flag = StatusCode.HTTP_403_FORBIDDEN
                    return JsonWrapper(error_dict, self.flag)

            # if serviceable_area:
            #     # Deleting existing serviceable_areas
            #     ServiceableArea.objects.filter(driver_id=user_profile).delete()
            #
            #     # and adding new serviceable_areas
            #     for serviceable_area_dict in serviceable_area:
            #         latitude = serviceable_area_dict['latitude']
            #         longitude = serviceable_area_dict['longitude']
            #         if 'loc_name' in serviceable_area_dict:
            #             loc_name = serviceable_area_dict['loc_name']
            #         else:
            #             loc_name = get_location_name(latitude, longitude)
            #         servobj_obj = ServiceableArea(
            #             latitude=latitude, longitude=longitude, loc_name=loc_name, driver_id=user_profile)
            #         servobj_obj.save()

            if profile_pic not in self.NULL_VALUE_VALIDATE:
                user_profile.profile_pic = str(profile_pic)

            user_profile.is_new_user = False
            user_profile.save()
            user_profile.user.save()
            vehicle_profile, created = VehicleDetails.objects.get_or_create(driver_id=user_profile,
                                                                            added_by=user_profile)

            if registration_number != "":
                vehicle_profile.reg_no = registration_number
            if deposit_amount:
                vehicle_profile.security_deposit = deposit_amount
            vehicle_profile.vehicle_volume = vehicle_volume
            vehicle_profile.vehicle_height = vehicle_height
            vehicle_profile.save()
            if fitness_certificate not in self.NULL_VALUE_VALIDATE:
                try:
                    attach_obj = Attachments.objects.get(doc_type='fitness_certificate', driver_id=user_profile)
                    attach_obj.attachment = fitness_certificate
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=fitness_certificate,
                                                            doc_type='fitness_certificate', driver_id=user_profile)
                    attach_obj.save()
            if tax_certificate not in self.NULL_VALUE_VALIDATE:
                try:
                    attach_obj = Attachments.objects.get(doc_type='tax_certificate', driver_id=user_profile)
                    attach_obj.attachment = tax_certificate
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=tax_certificate, doc_type='tax_certificate',
                                                            driver_id=user_profile)
                    attach_obj.save()

            if driver_license not in self.NULL_VALUE_VALIDATE:
                try:
                    attach_obj = Attachments.objects.get(doc_type='driver_license', driver_id=user_profile)
                    attach_obj.attachment = driver_license
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=driver_license, doc_type='driver_license',
                                                            driver_id=user_profile)
                    attach_obj.save()

            if commercial_insurance not in self.NULL_VALUE_VALIDATE:
                try:
                    attach_obj = Attachments.objects.get(doc_type='commercial_insurance', driver_id=user_profile)
                    attach_obj.attachment = commercial_insurance
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=commercial_insurance,
                                                            doc_type='commercial_insurance', driver_id=user_profile)
                    attach_obj.save()

            if registration_certificate not in self.NULL_VALUE_VALIDATE:
                try:
                    attach_obj = Attachments.objects.get(doc_type='registration_certificate', driver_id=user_profile)
                    attach_obj.attachment = registration_certificate
                    attach_obj.save()
                except:
                    attach_obj = Attachments.objects.create(attachment=registration_certificate,
                                                            doc_type='registration_certificate', driver_id=user_profile)
                    attach_obj.save()

            # GET NO OF ASSISTANTS
            no_assistants = get_no_assistant(vehicle_volume, user_profile.city)
            vehicle_profile.no_assistants = no_assistants

            # GET SECURITY DEPOSIT

            deposit_needed = get_security_deposit(vehicle_volume, user_profile.city)

            user_profile.deposit_needed = deposit_needed

            vehicle_profile.save()
            user_profile.save()
            user_profile.user.save()

            dic['no_trasnsit'] = no_assistants
            dic['added_transit_count'] = Assistants.objects.filter(driver_id=user_profile).count()
            dic['name'] = name
            dic['email'] = email
            dic['profile_pic'] = profile_pic
            dic['fitness_certificate'] = fitness_certificate
            dic['tax_certificate'] = tax_certificate
            dic['driver_license'] = driver_license
            dic['commercial_insurance'] = commercial_insurance
            dic['registration_certificate'] = registration_certificate
            dic['deposit_amount'] = deposit_amount
            dic['vehicle_volume'] = vehicle_volume
            dic['serviceable_area'] = serviceable_area
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
            self.flag = StatusCode.HTTP_200_OK

        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class BasicProfileUpdate(ApiView):
    """Api for showing the Basic profile of the partner """

    def get(self, request):
        dic = {}
        dic['name'] = request.user_profile.user.first_name
        dic['email'] = request.user_profile.user.email
        request.language = request.META.get('HTTP_LANGUAGE')
        dic['rating'] = round(request.user_profile.rating, 1)
        dic['profile_pic'] = request.user_profile.profile_pic
        dic['drive_status'] = request.user_profile.drive_status
        try:
            vehicle_profile = VehicleDetails.objects.get(driver_id=request.user_profile)
            dic['no_trasnsit'] = get_no_assistant(vehicle_profile.vehicle_volume, request.user_profile.city)
            dic['added_transit_count'] = Assistants.objects.filter(driver_id=request.user_profile).count()
        except:
            pass
        try:
            notifications_settings = NotificationsSettings.objects.get(user_profile=request.user_profile)
        except NotificationsSettings.DoesNotExist:
            notifications_settings = NotificationsSettings.objects.create(user_profile=request.user_profile,
                                                                          promotions=True)
            notifications_settings.save()
        dic['settings'] = {
            'promotions': notifications_settings.promotions,
        }
        dic['status'] = request.user_profile.status
        if request.user_profile.fleet_id:
            is_fleet = True
        else:
            is_fleet = False

        not_count = get_notification_count(request.user_profile)

        dic['not_count'] = not_count
        dic['is_fleet'] = is_fleet
        dic['status'] = request.user_profile.status
        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
        try:
            statuses = ['in_transit', 'loading']
            current_trip = Transfer.objects.filter(driver=request.user_profile, status__in=statuses).latest('id')
            dic['current_trip_id'] = current_trip.id
            dic['trip_status'] = current_trip.status
        except Transfer.DoesNotExist:
            dic['current_trip_id'] = 0
            request.user_profile.in_trip = False
            request.user_profile.save()

        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        name = request.DATA.get('name', '')
        email = request.DATA.get('email', '')
        profile_pic = request.DATA.get('profile_pic', '')
        drive_status = request.DATA.get('drive_status', '')
        user_profile = request.user_profile

        if name not in self.NULL_VALUE_VALIDATE:
            user_profile.email = email
            user_profile.user.email = email
            user_profile.user.first_name = name
            user_profile.drive_status = drive_status
            # STORING DRIVE STATUS HISTORY FOR HANDLING OFFERS
            try:  # IF STATUS_TO ISNULL
                stat_obj = DriveStatusHistory.objects.get(driver=user_profile, status_to__isnull=True,
                                                          status_from__isnull=False)
                stat_obj.status_to = timezone.now()
                stat_obj.save()
            except DriveStatusHistory.DoesNotExist:  # IF STATUS_FROM AND STATUS_TO ISNULL
                DriveStatusHistory.objects.create(driver=user_profile, status_from=timezone.now())

            dic['name'] = request.user_profile.user.first_name
            dic['email'] = request.user_profile.user.email
            if profile_pic not in self.NULL_VALUE_VALIDATE:
                user_profile.profile_pic = str(profile_pic)

            user_profile.save()
            user_profile.user.save()
            dic['profile_pic'] = request.user_profile.profile_pic
            dic['drive_status'] = request.user_profile.drive_status
            dic['status'] = request.user_profile.status
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
            self.flag = StatusCode.HTTP_200_OK

        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class UpdateAssistantsProfile(ApiView):
    """Api for update assistants of the partner """

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        assistant_name = request.DATA.get('assistant_name', '')
        id_proof = request.DATA.get('id_proof', '')
        photo = request.DATA.get('photo', '')
        assistant_id = request.DATA.get('assistant_id', '')
        user_profile = request.user_profile
        if assistant_name and id_proof not in self.NULL_VALUE_VALIDATE:
            try:
                if assistant_id > 0:
                    assist_obj = Assistants.objects.get(id=assistant_id)
                    assist_obj.assistant_name = assistant_name
                    assist_obj.id_proof = id_proof
                    assist_obj.photo = photo
                    assist_obj.save()
                else:
                    assist_obj = Assistants(assistant_name=assistant_name, id_proof=id_proof, photo=photo,
                                            driver_id=user_profile)
            except:
                assist_obj = Assistants(assistant_name=assistant_name, id_proof=id_proof, photo=photo,
                                        driver_id=user_profile)

            assist_obj.save()
        print(request.language)
        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
        self.flag = StatusCode.HTTP_200_OK

        return JsonWrapper(dic, self.flag)


class FleetList(ApiView):
    """
      Api for Fleet list
      """

    @method_decorator(verify_access_token)
    def get(self, request, **kwargs):
        dic = {}
        fleet_list = []
        fleets = BaseProfile.objects.filter(user_type='fleet_admin')
        for fleet in fleets:
            fleet_dict = {}
            fleet_dict['id'] = fleet.id
            fleet_dict['name'] = fleet.user.first_name
            fleet_dict['phone_number'] = fleet.phone_number
            fleet_list.append(fleet_dict)
        dic = fleet_list
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class AssistantsList(ApiView):
    """
      Api for Assistants List
      """

    @method_decorator(verify_access_token)
    def get(self, request, **kwargs):
        dic = {}
        assistants_list = []
        assistants = Assistants.objects.filter(driver_id=request.user_profile)
        for assistant in assistants:
            assistant_dict = {}
            assistant_dict['assistant_id'] = assistant.id
            assistant_dict['assistant_name'] = assistant.assistant_name
            assistant_dict['id_proof'] = assistant.id_proof
            assistant_dict['photo'] = assistant.photo
            assistants_list.append(assistant_dict)
        dic = assistants_list
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class DeleteAssistants(ApiView):
    """Api for delete an  assistants"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        assistant_id = request.DATA.get('assistant_id', '')
        user_profile = request.user_profile

        try:
            if assistant_id > 0:
                assist_obj = Assistants.objects.get(id=assistant_id)
                assist_obj.delete()
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_access_token')
                self.flag = StatusCode.HTTP_200_OK

            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_ass')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_ass')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(get_raw_data, name='dispatch')
class RefreshAccessToken(ApiView):
    """Api for refreshing access token"""

    def post(self, request, *args, **kwargs):
        dic = {}

        refresh_token = request.DATA.get('refresh_token', '')
        device_id = request.DATA.get('device_id', '')

        if refresh_token and device_id not in self.NULL_VALUE_VALIDATE:
            tokens = SingleAccessTokenManagement.refresh_access_token_single(device_id, refresh_token)
            if tokens[0]:
                dic["access_token"] = tokens[0].token
                dic["refresh_token"] = tokens[1].token
                self.flag = StatusCode.HTTP_200_OK

            else:
                dic["message"] = tokens[1]

        else:
            dic["message"] = "Please provide valid params"
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator((verify_access_token, get_raw_data), name='dispatch')
class DamageReportApi(ApiView):
    """Api for reporting damaged commodity during trip"""

    def post(self, request, *args, **kwargs):
        dic = {}

        transfer_id = request.DATA.get('transfer_id', '')
        item_id = request.DATA.get('item_id', '')
        description = request.DATA.get('description', '')
        partially_damaged = request.DATA.get('partially_damaged', '')
        fully_damaged = request.DATA.get('fully_damaged', '')
        stolen = request.DATA.get('stolen', '')
        photos = request.DATA.get('photos', [])

        if transfer_id not in self.NULL_VALUE_VALIDATE:

            try:
                damage_timeout = timezone.now() - timedelta(hours=48)
                transfer = Transfer.objects.get(id=transfer_id)
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer, loc_type='pickup')
                if transfer.completed_on:
                    if transfer.completed_on < damage_timeout:
                        dic['message'] = "Cannot report damage for transfers older than 48 hours"
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
                    else:
                        damaged_item_photos = []
                        try:
                            commodity_obj = Commodity.objects.get(id=item_id)
                            if partially_damaged > 0:
                                try:
                                    damage_obj = Damage.objects.get(transfer_id=transfer, item_id=commodity_obj,
                                                                    damage_type='partial')
                                    damage_obj.count += partially_damaged
                                    damage_obj.save()
                                except Damage.DoesNotExist:
                                    Damage.objects.create(transfer_id=transfer, item_id=commodity_obj,
                                                          damage_type='partial', count=partially_damaged)
                            if fully_damaged > 0:
                                try:
                                    damage_obj = Damage.objects.get(transfer_id=transfer, item_id=commodity_obj,
                                                                    damage_type='full')
                                    damage_obj.count += fully_damaged
                                    damage_obj.save()
                                except Damage.DoesNotExist:
                                    Damage.objects.create(transfer_id=transfer, item_id=commodity_obj,
                                                          damage_type='full', count=fully_damaged)

                            if stolen > 0:
                                try:
                                    damage_obj = Damage.objects.get(transfer_id=transfer, item_id=commodity_obj,
                                                                    damage_type='stolen')
                                    damage_obj.count += stolen
                                    damage_obj.save()
                                except Damage.DoesNotExist:
                                    Damage.objects.create(transfer_id=transfer, item_id=commodity_obj,
                                                          damage_type='stolen', count=stolen)

                            for photo in photos:
                                damaged_item_photos.append(
                                    DamagePhotos(transfer_id=transfer, item_id=commodity_obj, photo=photo))
                            if description:
                                DamageDescriptions.objects.create(transfer_id=transfer, description=description)
                        except Commodity.DoesNotExist:
                            pass
                        except TransferLocation.DoesNotExist:
                            pass
                        DamagePhotos.objects.bulk_create(damaged_item_photos)
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_damage_report_success')
                        dic['damage_report'] = get_report_damage_status(transfer, transfer_pickup)
                        self.flag = StatusCode.HTTP_200_OK
                else:
                    dic['message'] = "The trip is not completed"
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
            except Transfer.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            except TransferLocation.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


class CommodityListTransferBasedApi(ApiView):
    """
     Api for the  to list the commodity of a transfer for damage reporting
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        commodity_list = []
        transfer_id = request.DATA.get('transfer_id', '')

        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            try:
                transfer_loc = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
                commodities = TransferCommodity.objects.filter(transfer_loc_id=transfer_loc).values(
                    'item__id').distinct().annotate(models.Count('id'))
                for commodity_obj in commodities:
                    try:
                        commodity_dict = {}
                        total = 0
                        comm_obj = Commodity.objects.get(id=commodity_obj['item__id'])
                        cashorcard = comm_obj.city.cash_only
                        for damage in Damage.objects.filter(transfer_id=transfer_obj, item_id=comm_obj):
                            total += damage.count
                        if int(commodity_obj['id__count']) > int(total):
                            commodity_dict['total'] = total
                            commodity_dict['id'] = comm_obj.id
                            commodity_dict['item_name'] = comm_obj.item_name
                            commodity_dict['image'] = comm_obj.image
                            commodity_dict['volume'] = str(int(commodity_obj['id__count']) - int(total))
                            commodity_dict['cash'] = cashorcard
                            commodity_list.append(commodity_dict)
                    except Commodity.DoesNotExist:
                        pass
                dic = sorted(commodity_list, key=lambda i: i['item_name'])
                self.flag = StatusCode.HTTP_200_OK
            except TransferLocation.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                self.flag = StatusCode.HTTP_403_FORBIDDEN
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


class DamagedCommoditiesApi(ApiView):
    """
     Api for the  to list the damaged commodities of a transfer
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        commodity_list = []
        transfer_id = request.DATA.get('transfer_id', '')
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            try:
                transfer_loc = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
                commodities = TransferCommodity.objects.filter(transfer_loc_id=transfer_loc).values(
                    'item').distinct()
                for commodity_obj in commodities:
                    try:
                        comm_obj = Commodity.objects.get(id=commodity_obj['item'])
                        damages_reported = Damage.objects.filter(transfer_id=transfer_obj, item_id=comm_obj)
                        if damages_reported.count() > 0:
                            commodity_dict = {}
                            comm_obj = Commodity.objects.get(id=commodity_obj['item'])
                            commodity_dict['id'] = comm_obj.id
                            commodity_dict['item_name'] = comm_obj.item_name
                            commodity_dict['image'] = comm_obj.image

                            partial = full = stolen = 0
                            try:
                                partial_query = damages_reported.get(damage_type='partial')
                                partial = partial_query.count
                            except:
                                pass
                            try:
                                full_query = damages_reported.get(damage_type='full')
                                full = full_query.count
                            except:
                                pass
                            try:
                                stolen_query = damages_reported.get(damage_type='stolen')
                                stolen = stolen_query.count
                            except:
                                pass

                            commodity_dict['partial'] = partial
                            commodity_dict['full'] = full
                            commodity_dict['stolen'] = stolen
                            image_list = []
                            for image in DamagePhotos.objects.filter(transfer_id=transfer_obj, item_id=comm_obj):
                                image_list.append(image.photo)
                            commodity_dict['photos'] = image_list
                            commodity_list.append(commodity_dict)
                    except Commodity.DoesNotExist:
                        pass
                dic = sorted(commodity_list, key=lambda i: i['item_name'])
                self.flag = StatusCode.HTTP_200_OK
            except TransferLocation.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                self.flag = StatusCode.HTTP_403_FORBIDDEN
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class UpdateDriverLocation(ApiView):
    """Api for Update Driver Location """

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        latitude = request.DATA.get('latitude', '')
        longitude = request.DATA.get('longitude', '')
        user_profile = request.user_profile

        if latitude and longitude not in self.NULL_VALUE_VALIDATE:
            user_profile.current_lat = latitude
            user_profile.current_lng = longitude
            user_profile.save()
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
            self.flag = StatusCode.HTTP_200_OK

        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


def get_rating(user_prof):
    ratings = Rating.objects.filter(rating_to=user_prof)
    rating = 5
    if ratings.count() > 0:
        rating = ratings.aggregate(rating_value=Avg('rating_value'))["rating_value"]
    return float(rating)


def get_assistants(driver_id):
    dic = {}
    assistants_list = []
    assistants = Assistants.objects.filter(driver_id=driver_id, deleted=False)
    for assistant in assistants:
        assistant_dict = {}
        assistant_dict['assistant_id'] = assistant.id
        assistant_dict['assistant_name'] = assistant.assistant_name
        assistant_dict['photo'] = assistant.photo
        assistants_list.append(assistant_dict)
    dic['list'] = assistants_list
    dic['no_assistants'] = assistants.count()
    return dic


def get_transfer_assistants(transfer_obj):
    dic = {}
    assistants_list = []
    assistants = transfer_obj.helpers.all()
    for assistant in assistants:
        assistant_dict = {}
        assistant_dict['assistant_id'] = assistant.id
        assistant_dict['assistant_name'] = assistant.assistant_name
        assistant_dict['photo'] = assistant.photo
        assistants_list.append(assistant_dict)
    dic['list'] = assistants_list
    dic['no_assistants'] = assistants.count()
    return dic


class UserTransferListApi(ApiView):
    """
     Api for the  to list the history / Schedule / Active Booking in user app
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = []
        transfer_list = []
        user_profile = request.user_profile
        list_type = request.DATA.get('list_type', '')
        # list_type='history' , list_type = 'schedule'
        if list_type == 'history':
            status = ['completed', 'in_transit', 'loading', 'auto_cancelled', 'cancelled']
            transfers = Transfer.objects.filter(added_by=user_profile, status__in=status).order_by('-id')
        else:
            status = ['accepted', 'active']
            transfers = Transfer.objects.filter(added_by=user_profile, status__in=status,
                                                instant_search=False).order_by('-id')

        for transfer_obj in transfers:
            try:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')
                items = TransferCommodity.objects.filter(transfer_loc_id=transfer_pickup).values(
                    'item__id').distinct().annotate(models.Count('id'))

                transfer_dict = {}
                if transfer_obj.driver:
                    transfer_dict[
                        'driver_name'] = transfer_obj.driver.user.first_name + " " + transfer_obj.driver.user.last_name
                    transfer_dict['profile_pic'] = transfer_obj.driver.profile_pic
                    transfer_dict['assistant_list'] = get_transfer_assistants(transfer_obj)
                    transfer_dict['rating'] = round(transfer_obj.driver.rating, 1)
                    transfer_dict['contact_number'] = transfer_obj.driver.user.username
                else:
                    transfer_dict['driver_name'] = ''
                    transfer_dict['profile_pic'] = ''
                    transfer_dict['assistant_list'] = {}
                    transfer_dict['rating'] = 0.0
                    transfer_dict['contact_number'] = ''

                transfer_dict['pickup_loc'] = transfer_pickup.location_name
                transfer_dict['pickup_lat'] = transfer_pickup.loc_lat
                transfer_dict['pickup_lng'] = transfer_pickup.loc_lng
                transfer_dict['drop_loc'] = transfer_drop.location_name
                transfer_dict['drop_lat'] = transfer_drop.loc_lat
                transfer_dict['drop_lng'] = transfer_drop.loc_lng
                # NEED TO CHANGE PICKUP TIME AND DROP TIME
                if transfer_obj.started_on:
                    transfer_dict['pickup_time'] = int(transfer_obj.started_on.strftime('%s')) * 1000
                if transfer_obj.completed_on:
                    transfer_dict['drop_time'] = int(transfer_obj.completed_on.strftime('%s')) * 1000
                transfer_dict['transfer_on'] = int(transfer_obj.transfer_on.strftime('%s')) * 1000
                transfer_dict['duration'] = transfer_obj.duration
                transfer_dict['distance'] = transfer_obj.distance
                transfer_dict['total_amount'] = round(transfer_obj.total_amount, 2)

                transfer_dict['transfer_id'] = transfer_obj.id
                transfer_dict['payment_type'] = transfer_obj.payment_type
                transfer_dict['added_on'] = int(transfer_obj.added_on.strftime('%s')) * 1000
                transfer_dict['no_items'] = items.count()
                transfer_dict['transfer_type_from'] = transfer_pickup.transfer_loc
                transfer_dict['transfer_type_to'] = transfer_drop.transfer_loc
                if request.language == 'en':
                    transfer_dict['service_name'] = transfer_obj.service_type.display_service_name_en
                else:
                    transfer_dict['service_name'] = transfer_obj.service_type.display_service_name_es

                # transfer_dict['service_name'] = transfer_obj.service_type.get_service_name_display()
                transfer_dict['refund_initiated'] = transfer_obj.refund_initiated
                transfer_dict['from_floor'] = transfer_pickup.floor
                transfer_dict['to_floor'] = transfer_drop.floor
                if transfer_obj.refund_initiated:
                    refund_status = list(RefundManagement.objects.filter(transfer=transfer_obj))
                    if refund_status:
                        transfer_dict['refund_status'] = refund_status[0].status
                if transfer_obj.status == 'active':
                    transfer_dict['status'] = 'pending'
                else:
                    transfer_dict['status'] = transfer_obj.status
                if (
                        transfer_obj.status == 'in_transit' or transfer_obj.status == 'accepted' or transfer_obj.status == 'loading') and timezone.now() >= transfer_obj.transfer_on - timedelta(
                    hours=1):
                    transfer_dict['tracking'] = True
                else:
                    transfer_dict['tracking'] = False

                if transfer_obj.completed_on:
                    if transfer_obj.completed_on >= (timezone.now() - timedelta(
                            hours=48)) and transfer_obj.status == 'completed' and get_report_damage_status(transfer_obj,
                                                                                                           transfer_pickup):
                        transfer_dict['damage_report'] = True
                    else:
                        transfer_dict['damage_report'] = False
                else:
                    transfer_dict['damage_report'] = False

                transfer_dict['can_rate_trip'] = get_user_can_rate_trip(transfer_obj, request.user_profile)
                # GET COMMODITY LIST
                commodity_details = []
                for item in items:
                    try:
                        comm_obj = Commodity.objects.get(id=item['item__id'])
                        commodity_dict = dict(total=item['id__count'], id=comm_obj.id, name=comm_obj.item_name,
                                              volume=int(item['id__count']))
                        commodity_details.append(commodity_dict)
                    except Commodity.DoesNotExist:
                        pass
                transfer_dict['commodity_details'] = sorted(commodity_details, key=lambda i: i['name'])

                transfer_list.append(transfer_dict)
                self.flag = StatusCode.HTTP_200_OK
            except TransferLocation.DoesNotExist:
                pass
        dic = transfer_list
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class ContinueSearchApi(ApiView):
    """Api for search to continue for 1 hour"""

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')
        user_profile = request.user_profile
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id, status='auto_cancelled')
            if not transfer_obj.refund_initiated:
                # UPDATE TRANSFER TIME + 1 HR TO CONTINUE SEARCH
                transfer_time = timezone.now()
                transfer_obj.transfer_on = transfer_time
                transfer_obj.instant_search = True
                transfer_obj.status = 'active'
                transfer_obj.save()

                search_failed_notifications = Notifications.objects.filter(transfer_id=transfer_obj,
                                                                           type='search_failed')
                search_failed_notifications.delete()

                try:
                    search_obj = SearchDrivers()
                    logger_me.debug('language--search')
                    logger_me.debug(request.language)
                    search_obj.search_drivers(transfer_obj, transfer_obj.instant_search, request.language)
                except:
                    pass
                if transfer_obj.instant_search:
                    transfer_obj.transfer_on = timezone.now()
                    transfer_obj.save()
                self.flag = StatusCode.HTTP_200_OK
            else:
                dic['message'] = "Auto refund initiated for your transfer, as we couldn't find suitable trucks."
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


class AcceptRejectApi(ApiView):
    """Api for search to continue for 1 hour"""

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')
        status = request.DATA.get('status', '')
        user_profile = request.user_profile
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
            transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')
            items = TransferCommodity.objects.filter(transfer_loc_id=transfer_pickup).values(
                'item__id').distinct().annotate(models.Count('id'))
            accept_statuses = ['accepted', 'loading', 'in_transit', 'completed']
            if transfer_obj.status == 'active':
                try:
                    truck_req = TruckRequest.objects.get(transfer_id=transfer_obj, driver_id=user_profile,
                                                         status='sent')
                    truck_req.status = status
                    truck_req.save()
                    if status == 'accepted' and transfer_obj.status == 'active' and not transfer_obj.driver:
                        transfer_obj.driver = user_profile
                        transfer_obj.status = status
                        transfer_obj.helpers.add(
                            *list(Assistants.objects.filter(driver_id=user_profile, deleted=False)))
                        # UPDATE COMMISSION TO MUBERZ
                        commission_amount = 0
                        if user_profile.fleet_id:
                            commision = user_profile.fleet_id.commission
                        else:
                            commision = user_profile.commission

                        total_amount = transfer_obj.total_amount
                        if commision > 0:
                            commission_amount = (total_amount * commision) / 100
                        transfer_obj.commission = commission_amount
                        transfer_obj.share_trip = False
                        transfer_obj.save(update_fields=["driver", "status", "commission", "share_trip"])
                        transfer_obj.refresh_from_db()

                        dic['transfer_id'] = transfer_obj.id

                        # PUSH NOTIFICATION TO USER APP
                        notify_obj = create_notification(transfer_obj, 'trip_accepted')
                        # DELETE NOTIFICATIONS SENT BEFORE AGAINST THIS TRANSFER LIKE TRIP_REQUEST, REMINDER ETC
                        delete_notification(transfer_obj, 'trip_accepted', '')
                        heading = lang_obj.get_lang_word(request.language,
                                                         'lbl_push_notification_trip_accepted_heading')
                        message = lang_obj.get_lang_word(request.language,
                                                         'lbl_push_notification_trip_accepted_message') + transfer_obj.driver.user.first_name
                        send_push_notification(transfer_obj, transfer_obj.added_by,
                                               message, heading, True, 0, notify_obj)

                        # PUSH NOTIFICATION TO OTHER PARTNERS

                        notify_obj = create_notification(transfer_obj, 'already_accepted')
                        notify_objs = NotificationHistory.objects.filter(~Q(user=transfer_obj.driver),
                                                                         notification_id__transfer_id=transfer_obj,
                                                                         notification_id__type='trip_request')
                        heading = lang_obj.get_lang_word(request.language,
                                                         'lbl_push_notification_trip_already_accepted_heading')
                        message = lang_obj.get_lang_word(request.language,
                                                         'lbl_push_notification_trip_already_accepted_message')
                        for notify in notify_objs:
                            notify.time_out = timezone.now()
                            notify.save()
                            send_push_notification(transfer_obj, notify.user,
                                                   message, heading, False, 0, notify_obj)

                        # MAIL NOTIFICATION TO USER APP
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
                            "lbl_transfer_accepted_by": lang_obj.get_lang_word(request.language,
                                                                               'lbl_transfer_accepted_by'),
                            "lbl_driver_name": lang_obj.get_lang_word(request.language, 'lbl_driver_name'),
                            "lbl_reg_no": lang_obj.get_lang_word(request.language, 'lbl_reg_no'),
                            "lbl_volume": lang_obj.get_lang_word(request.language, 'lbl_volume'),
                            "lbl_payable": lang_obj.get_lang_word(request.language, 'lbl_payable'),
                            "lbl_payment_mode": lang_obj.get_lang_word(request.language, 'lbl_payment_mode'),
                            "lbl_fully_paid": lang_obj.get_lang_word(request.language, 'lbl_fully_paid'),
                            "lbl_scheduled_time": lang_obj.get_lang_word(request.language, 'lbl_scheduled_time'),
                            "lbl_pickup": lang_obj.get_lang_word(request.language, 'lbl_pickup'),
                            "lbl_drop": lang_obj.get_lang_word(request.language, 'lbl_drop'),
                            "lbl_sl_no": lang_obj.get_lang_word(request.language, 'lbl_sl_no'),
                            "lbl_name": lang_obj.get_lang_word(request.language, 'lbl_name'),
                            "lbl_plug_in": lang_obj.get_lang_word(request.language, 'lbl_plug_in'),
                            "lbl_quantity": lang_obj.get_lang_word(request.language, 'lbl_quantity'),
                            "lbl_yes": lang_obj.get_lang_word(request.language, 'lbl_yes'),
                            "lbl_no": lang_obj.get_lang_word(request.language, 'lbl_no'),
                            "lbl_thanks": lang_obj.get_lang_word(request.language, 'lbl_thanks'),
                            "lbl_commodities": lang_obj.get_lang_word(request.language, 'lbl_commodities'),
                            "lbl_transfer_confirmed": lang_obj.get_lang_word(request.language,
                                                                             'lbl_transfer_confirmed'),
                            "lbl_trip_amount": lang_obj.get_lang_word(request.language, 'lbl_trip_amount'),
                        }

                        for location in transfer_locations:
                            context[location['loc_type']] = location['location_name'] or ""

                        if not transfer_obj.instant_search:
                            target_timezone = pytz.timezone('America/Lima')
                            scheduled_time = transfer_obj.transfer_on.astimezone(target_timezone).strftime(
                                "%d-%m-%Y %I:%M %p")
                            context["scheduled_time"] = scheduled_time

                        message = get_template('dashboard/email-templates/transfer-confirm-mail.html').render(context)
                        # Starting a new thread for sending confirmation mail
                        email_thread = Thread(
                            target=send_template_email,
                            args=(lang_obj.get_lang_word(request.language, 'lbl_transfer_confirmed'),
                                  message, [transfer_obj.added_by.user.email]))
                        email_thread.start()  # Starts thread
                        # MAIL NOTIFICATION TO USER APP

                        user_dict = {}
                        commodity_list = []
                        for item in items:
                            try:
                                commodity_dict = {}
                                total = 0
                                comm_obj = Commodity.objects.get(id=item['item__id'])
                                commodity_dict['total'] = item['id__count']
                                commodity_dict['id'] = comm_obj.id
                                commodity_dict['name'] = comm_obj.item_name
                                commodity_dict['volume'] = int(item['id__count'])
                                commodity_list.append(commodity_dict)
                            except Commodity.DoesNotExist:
                                pass
                        dic['items'] = sorted(commodity_list, key=lambda i: i['name'])
                        user_dict[
                            'user_name'] = transfer_obj.added_by.user.first_name + " " + transfer_obj.added_by.user.last_name
                        user_dict['user_profile_pic'] = transfer_obj.added_by.profile_pic
                        user_dict['user_rating'] = round(transfer_obj.added_by.rating, 1)
                        user_dict['contact_number'] = transfer_obj.added_by.user.username
                        dic['user_details'] = user_dict

                        dic['pickup_loc'] = transfer_pickup.location_name
                        dic['pickup_lat'] = float(transfer_pickup.loc_lat)
                        dic['pickup_lng'] = float(transfer_pickup.loc_lng)
                        dic['drop_lat'] = float(transfer_drop.loc_lat)
                        dic['drop_lng'] = float(transfer_drop.loc_lng)
                        dic['transfer_on'] = int(transfer_obj.transfer_on.strftime('%s')) * 1000
                        dic['drop_loc'] = transfer_drop.location_name
                        dic['trip_status'] = transfer_obj.status
                        # NEED TO CHANGE PICKUP TIME AND DROP TIME
                        dic['duration'] = transfer_obj.duration
                        dic['distance'] = transfer_obj.distance
                        if transfer_obj.payment_type == 'card':
                            dic['total_amount'] = transfer_obj.total_amount - transfer_obj.commission
                        else:
                            dic['total_amount'] = transfer_obj.total_amount
                        dic['payment_type'] = transfer_obj.payment_type
                        dic['commission'] = transfer_obj.commission
                        dic['added_on'] = int(transfer_obj.added_on.strftime('%s')) * 1000
                        dic['no_items'] = items.count()
                        if request.language == 'en':
                            dic['service_name'] = transfer_obj.service_type.display_service_name_en
                        else:
                            dic['service_name'] = transfer_obj.service_type.display_service_name_es
                        # dic['service_to'] = transfer_obj.service_type.get_service_to_display()
                        dic['transfer_type_from'] = int(transfer_pickup.transfer_loc)
                        dic['transfer_type_to'] = int(transfer_drop.transfer_loc)
                        dic['from_floor'] = transfer_pickup.floor
                        dic['to_floor'] = transfer_drop.floor
                        dic['can_rate_trip'] = get_user_can_rate_trip(transfer_obj, request.user_profile)
                        self.flag = StatusCode.HTTP_200_OK
                    elif transfer_obj.status == 'accepted' or transfer_obj.status == 'loading':
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_trip_already_accepted')
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
                    else:
                        dic['message'] = ''
                        self.flag = StatusCode.HTTP_200_OK
                        # DELETE THE TRIP_REQUEST FOR REJECTED TRANSFERS
                        try:
                            not_obj = Notifications.objects.get(transfer_id=transfer_obj, type='trip_request',
                                                                deleted=False)
                            NotificationHistory.objects.filter(user=user_profile, notification_id=not_obj).update(
                                deleted=True)
                        except Notifications.DoesNotExist:
                            pass
                except TruckRequest.DoesNotExist:
                    dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_request')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
            elif transfer_obj.status in accept_statuses:
                dic['message'] = 'The trip is already taken by another driver'
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            elif transfer_obj.status == 'auto_cancelled':
                dic['message'] = 'The request is timed-out'
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            else:
                dic['message'] = 'The trip is cancelled'
                self.flag = StatusCode.HTTP_400_BAD_REQUEST

        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except TransferLocation.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_location')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


class PartnerTransferBasicDetailsApi(ApiView):
    """
      Api for Transfer Basic Details for Partner App
      """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        transfer_id = request.DATA.get('transfer_id', '')
        dic = {}
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)

            transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
            transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')

            dic['transfer_id'] = transfer_obj.id

            user_dict = {}
            user_dict['user_name'] = transfer_obj.added_by.user.first_name + " " + transfer_obj.added_by.user.last_name
            user_dict['user_profile_pic'] = transfer_obj.added_by.profile_pic
            user_dict['user_rating'] = round(transfer_obj.added_by.rating, 1)

            dic['user_details'] = user_dict
            dic['drop_loc'] = transfer_drop.location_name
            dic['drop_lat'] = float(transfer_drop.loc_lat)
            dic['drop_lng'] = float(transfer_drop.loc_lng)
            dic['pickup_loc'] = transfer_pickup.location_name
            dic['pickup_lat'] = float(transfer_pickup.loc_lat)
            dic['pickup_lng'] = float(transfer_pickup.loc_lng)
            dic['transfer_on'] = int(transfer_obj.transfer_on.strftime('%s')) * 1000
            dic['instant_search'] = transfer_obj.instant_search
            dic['is_special_handling_required'] = transfer_obj.is_special_handling_required
            dic['special_handling_fee'] = transfer_obj.special_handling_fee
            self.flag = StatusCode.HTTP_200_OK
            return JsonWrapper(dic, self.flag)
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except TransferLocation.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_location')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
            return JsonWrapper(dic, self.flag)
        return JsonWrapper(dic, self.flag)


class PartnerTransferDetailsApi(ApiView):
    """
      Api for Transfer Details for Partner App
      """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        transfer_id = request.DATA.get('transfer_id', '')
        dic = {}
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)

            transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
            items = TransferCommodity.objects.filter(transfer_loc_id=transfer_pickup).values(
                'item__id').distinct().annotate(models.Count('id'))
            transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')
            dic['transfer_id'] = transfer_obj.id

            user_dict = {}

            commodity_list = []
            for item in items:
                try:
                    commodity_dict = {}
                    total = 0
                    comm_obj = Commodity.objects.get(id=item['item__id'])
                    commodity_dict['total'] = item['id__count']
                    commodity_dict['id'] = comm_obj.id
                    commodity_dict['name'] = comm_obj.item_name
                    commodity_dict['volume'] = int(item['id__count'])
                    commodity_list.append(commodity_dict)
                except Commodity.DoesNotExist:
                    pass
            dic['items'] = sorted(commodity_list, key=lambda i: i['name'])

            user_dict[
                'user_name'] = transfer_obj.added_by.user.first_name + " " + transfer_obj.added_by.user.last_name
            user_dict['user_profile_pic'] = transfer_obj.added_by.profile_pic
            user_dict['user_rating'] = round(transfer_obj.added_by.rating, 1)
            user_dict['contact_number'] = transfer_obj.added_by.user.username
            dic['user_details'] = user_dict

            dic['pickup_loc'] = transfer_pickup.location_name
            dic['pickup_lat'] = float(transfer_pickup.loc_lat)
            dic['pickup_lng'] = float(transfer_pickup.loc_lng)
            dic['drop_lat'] = float(transfer_drop.loc_lat)
            dic['drop_lng'] = float(transfer_drop.loc_lng)
            dic['transfer_on'] = int(transfer_obj.transfer_on.strftime('%s')) * 1000
            dic['drop_loc'] = transfer_drop.location_name
            dic['trip_status'] = transfer_obj.status
            dic['is_special_handling_required'] = transfer_obj.is_special_handling_required
            dic['special_handling_fee'] = transfer_obj.special_handling_fee

            # NEED TO CHANGE PICKUP TIME AND DROP TIME
            dic['duration'] = transfer_obj.duration
            dic['distance'] = transfer_obj.distance
            if transfer_obj.payment_type == 'card':
                dic['total_amount'] = transfer_obj.total_amount - transfer_obj.commission
            else:
                dic['total_amount'] = transfer_obj.total_amount

            dic['payment_type'] = transfer_obj.payment_type
            dic['commission'] = transfer_obj.commission
            dic['added_on'] = int(transfer_obj.added_on.strftime('%s')) * 1000
            dic['no_items'] = items.count()
            if request.language == 'en':
                dic['service_name'] = transfer_obj.service_type.display_service_name_en
            else:
                dic['service_name'] = transfer_obj.service_type.display_service_name_es

            # dic['service_to'] = transfer_obj.service_type.get_service_to_display()
            dic['transfer_type_from'] = int(transfer_pickup.transfer_loc)
            dic['transfer_type_to'] = int(transfer_drop.transfer_loc)
            dic['instant_search'] = transfer_obj.instant_search
            dic['from_floor'] = transfer_pickup.floor
            dic['to_floor'] = transfer_drop.floor
            dic['can_rate_trip'] = get_user_can_rate_trip(transfer_obj, request.user_profile)
            self.flag = StatusCode.HTTP_200_OK
            return JsonWrapper(dic, self.flag)
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except TransferLocation.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_location')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
            return JsonWrapper(dic, self.flag)
        return JsonWrapper(dic, self.flag)


class UserTransferDetailsApi(ApiView):
    """
      Api for Transfer Details for User App
      """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        transfer_id = request.DATA.get('transfer_id', '')
        dic = {}
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
            transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')
            items = TransferCommodity.objects.filter(transfer_loc_id=transfer_pickup).values(
                'item__id').distinct().annotate(models.Count('id'))
            dic['transfer_id'] = transfer_obj.id
            dic['user_name'] = transfer_obj.added_by.user.first_name + " " + transfer_obj.added_by.user.last_name
            dic['pickup_loc'] = transfer_pickup.location_name
            dic['pickup_lat'] = float(transfer_pickup.loc_lat)
            dic['pickup_lng'] = float(transfer_pickup.loc_lng)
            dic['drop_loc'] = transfer_drop.location_name
            dic['drop_lat'] = float(transfer_drop.loc_lat)
            dic['drop_lng'] = float(transfer_drop.loc_lng)
            if transfer_obj.started_on:
                dic['pickup_time'] = int(transfer_obj.started_on.strftime('%s')) * 1000
            if transfer_obj.completed_on:
                dic['drop_time'] = int(transfer_obj.completed_on.strftime('%s')) * 1000
            dic['transfer_on'] = int(transfer_obj.transfer_on.strftime('%s')) * 1000
            dic['duration'] = transfer_obj.duration
            dic['distance'] = transfer_obj.distance
            # if transfer_obj.payment_type == 'card':
            #     dic['total_amount'] = round(transfer_obj.total_amount - transfer_obj.commission, 2)
            # else:
            dic['total_amount'] = round(transfer_obj.total_amount, 2)
            dic['profile_pic'] = transfer_obj.added_by.profile_pic
            dic['payment_type'] = transfer_obj.payment_type
            dic['commission'] = transfer_obj.commission
            dic['added_on'] = int(transfer_obj.added_on.strftime('%s')) * 1000
            dic['no_items'] = items.count()
            if request.language == 'en':
                dic['service_name'] = transfer_obj.service_type.display_service_name_en
            else:
                dic['service_name'] = transfer_obj.service_type.display_service_name_es
            # dic['service_to'] = transfer_obj.service_type.get_service_to_display()
            dic['transfer_type_from'] = int(transfer_pickup.transfer_loc)
            dic['transfer_type_to'] = int(transfer_drop.transfer_loc)
            dic['transfer_status'] = transfer_obj.status
            dic['instant_search'] = transfer_obj.instant_search
            dic['from_floor'] = transfer_pickup.floor
            dic['to_floor'] = transfer_drop.floor
            dic['can_rate_trip'] = get_user_can_rate_trip(transfer_obj, request.user_profile)

            if transfer_obj.completed_on:
                if transfer_obj.completed_on >= (
                        timezone.now() - timedelta(
                    hours=48)) and transfer_obj.status == 'completed' and get_report_damage_status(transfer_obj,
                                                                                                   transfer_pickup):
                    dic['damage_report'] = True
                else:
                    dic['damage_report'] = False
            else:
                dic['damage_report'] = False

            dic['refund_initiated'] = transfer_obj.refund_initiated
            if transfer_obj.refund_initiated:
                refund_status = list(RefundManagement.objects.filter(transfer=transfer_obj).order_by('-id'))
                if refund_status:
                    dic['refund_status'] = refund_status[0].status
            if transfer_obj.driver:
                try:
                    vehicle = VehicleDetails.objects.get(driver_id=transfer_obj.driver)
                    assistants = Assistants.objects.filter(driver_id=transfer_obj.driver).values('assistant_name',
                                                                                                 'photo')[
                                 :transfer_obj.helper_count]
                    driver_details = dict(contact_number=transfer_obj.driver.user.username,
                                          driver_photo=transfer_obj.driver.profile_pic,
                                          trip_amount=transfer_obj.total_amount, payment_type=transfer_obj.payment_type,
                                          reg_no=vehicle.reg_no,
                                          no_assistants=get_transfer_assistants(transfer_obj)['no_assistants'],
                                          assistants=list(assistants), driver_name=transfer_obj.driver.user.first_name,
                                          rating=transfer_obj.driver.rating)
                    if (
                            transfer_obj.status == 'in_transit' or transfer_obj.status == 'accepted' or transfer_obj.status == 'loading') and timezone.now() >= transfer_obj.transfer_on - timedelta(
                        hours=1):
                        dic['tracking'] = True
                    else:
                        dic['tracking'] = False
                except VehicleDetails.DoesNotExist:
                    driver_details = dict(message="No such vehicle found")
                dic['driver_details'] = driver_details
            try:
                commodity_details = []
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
                items = TransferCommodity.objects.filter(transfer_loc_id=transfer_pickup).values(
                    'item__id').distinct().annotate(models.Count('id'))
                for item in items:
                    try:
                        comm_obj = Commodity.objects.get(id=item['item__id'])
                        commodity_dict = dict(total=item['id__count'], id=comm_obj.id, name=comm_obj.item_name,
                                              volume=int(item['id__count']))
                        commodity_details.append(commodity_dict)
                    except Commodity.DoesNotExist:
                        pass
                dic['commodity_details'] = commodity_details
            except TransferLocation.DoesNotExist:
                dic['commodity_details'] = "No such transfer location found"
                pass
            except TransferCommodity.DoesNotExist:
                dic['commodity_details'] = "No such transfer commodity found"
                pass
            self.flag = StatusCode.HTTP_200_OK
            return JsonWrapper(dic, self.flag)
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except TransferLocation.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_location')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
            return JsonWrapper(dic, self.flag)
        return JsonWrapper(dic, self.flag)


class PartnerTransferListApi(ApiView):
    """
     Api for the  to list the history / Schedule in partner app
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        transfer_list = []
        user_profile = request.user_profile
        list_type = request.DATA.get('list_type', '')
        # list_type='history' , list_type = 'schedule'
        if list_type == 'history':
            status = ['completed', 'in_transit', 'loading', 'cancelled', 'auto_cancelled']
        else:
            status = ['accepted']

        transfers = Transfer.objects.filter(driver=user_profile, status__in=status).order_by('-id')
        for transfer_obj in transfers:
            try:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')
                transfer_dict = {}
                transfer_dict[
                    'user_name'] = transfer_obj.added_by.user.first_name + " " + transfer_obj.added_by.user.last_name
                transfer_dict['pickup_loc'] = transfer_pickup.location_name
                transfer_dict['drop_loc'] = transfer_drop.location_name
                # NEED TO CHANGE PICKUP TIME AND DROP TIME
                if transfer_obj.started_on:
                    transfer_dict['pickup_time'] = int(transfer_obj.started_on.strftime('%s')) * 1000
                if transfer_obj.completed_on:
                    transfer_dict['drop_time'] = int(transfer_obj.completed_on.strftime('%s')) * 1000
                transfer_dict['transfer_on'] = int(transfer_obj.transfer_on.strftime('%s')) * 1000
                transfer_dict['duration'] = transfer_obj.duration
                transfer_dict['distance'] = transfer_obj.distance
                if transfer_obj.payment_type == 'card':
                    transfer_dict['total_amount'] = transfer_obj.total_amount - transfer_obj.commission
                else:
                    transfer_dict['total_amount'] = transfer_obj.total_amount
                transfer_dict['commission'] = transfer_obj.commission
                transfer_dict['profile_pic'] = transfer_obj.added_by.profile_pic
                transfer_dict['transfer_id'] = transfer_obj.id
                transfer_dict['rating'] = round(transfer_obj.added_by.rating, 1)
                transfer_dict['status'] = transfer_obj.get_status_display()
                if transfer_obj.status == 'completed':
                    transfer_dict['status_text'] = lang_obj.get_lang_word(request.language, 'lbl_completed')
                else:
                    transfer_dict['status_text'] = transfer_obj.get_status_display()
                transfer_dict['from_floor'] = transfer_pickup.floor
                transfer_dict['to_floor'] = transfer_drop.floor
                transfer_list.append(transfer_dict)

                transfer_dict['can_rate_trip'] = get_user_can_rate_trip(transfer_obj, request.user_profile)

            except TransferLocation.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer_location')
                self.flag = StatusCode.HTTP_403_FORBIDDEN
                return JsonWrapper(dic, self.flag)
        dic = transfer_list
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class RateUsersApi(ApiView):
    """Api for saving the driver/User rating"""

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')
        rating = request.DATA.get('rating', '')
        description = request.DATA.get('description', '')
        user_profile = request.user_profile

        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            if transfer_obj.status == 'completed':
                if user_profile.user_type == 'app_user':
                    if not Rating.objects.filter(rating_from=user_profile, rating_to=transfer_obj.driver,
                                                 transfer_id=transfer_obj).exists():
                        # UPDATE TRANSFER TIME + 1 HR TO CONTINUE SEARCH
                        rate_obj = Rating(rating_from=user_profile, rating_to=transfer_obj.driver,
                                          transfer_id=transfer_obj)
                        rate_obj.rating_value = rating
                        rate_obj.description = description
                        rate_obj.added_on = timezone.now()
                        rate_obj.status = True
                        rate_obj.save()
                        user_rating = get_rating(transfer_obj.driver)
                        transfer_obj.driver.rating = user_rating
                        transfer_obj.driver.save()
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_rating_added_driver')
                        self.flag = StatusCode.HTTP_200_OK
                    else:
                        dic['message'] = lang_obj.get_lang_word(request.language,
                                                                'lbl_driver_rating_already_exist')
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
                else:
                    if not Rating.objects.filter(rating_from=user_profile, rating_to=transfer_obj.added_by,
                                                 transfer_id=transfer_obj).exists():
                        # UPDATE TRANSFER TIME + 1 HR TO CONTINUE SEARCH
                        rate_obj = Rating(rating_from=user_profile, rating_to=transfer_obj.added_by,
                                          transfer_id=transfer_obj)
                        rate_obj.rating_value = rating
                        rate_obj.description = description
                        rate_obj.added_on = timezone.now()
                        rate_obj.status = True
                        rate_obj.save()
                        user_rating = get_rating(transfer_obj.added_by)
                        transfer_obj.added_by.rating = user_rating
                        transfer_obj.added_by.save()
                        dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_rating_added_user')
                        self.flag = StatusCode.HTTP_200_OK
                    else:
                        dic['message'] = lang_obj.get_lang_word(request.language,
                                                                'lbl_user_rating_already_exist')
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_transfer_not_completed')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


class CompleteTransferApi(ApiView):
    """Api for complete a trip"""

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')
        special_handling_fee = request.DATA.get('special_handling_fee', '')
        is_special_handling_required = request.DATA.get('is_special_handling_required', '')
        user_profile = request.user_profile

        logger_me.debug("special hand")
        logger_me.debug(is_special_handling_required)

        try:
            transfer_obj = Transfer.objects.get(id=transfer_id, driver=user_profile)
            if transfer_obj.status == 'in_transit':
                # UPDATE TRANSFER TIME + 1 HR TO CONTINUE SEARCH
                transfer_obj.completed_on = timezone.now()
                transfer_obj.payment_received = True
                transfer_obj.status = 'completed'
                if is_special_handling_required:
                    transfer_obj.is_special_handling_required = is_special_handling_required
                    if special_handling_fee > transfer_obj.total_amount:
                        dic['message'] = "The handling fee can not be more than total amount"
                        self.flag = StatusCode.HTTP_400_BAD_REQUEST
                        return JsonWrapper(dic, self.flag)
                    transfer_obj.special_handling_fee = special_handling_fee
                    transfer_obj.total_amount += special_handling_fee
                transfer_obj.payable_amount = transfer_obj.total_amount
                transfer_obj.save()
                transfer_obj.driver.in_trip = False
                transfer_obj.driver.save()
                dic['amount_to_be_collected'] = transfer_obj.payable_amount

                # DELETE trip_started
                delete_notification(transfer_obj, 'trip_completed', 'user')

                # PUSH NOTIFICATION TO USER APP
                notify_obj = create_notification(transfer_obj, 'trip_completed')
                time_out = int(timezone.timedelta(minutes=10).total_seconds() * 1000)

                heading = lang_obj.get_lang_word(request.language,
                                                 'lbl_push_notification_trip_completed_heading')
                message = lang_obj.get_lang_word(request.language,
                                                 'lbl_push_notification_trip_completed_message')
                send_push_notification(transfer_obj, transfer_obj.added_by, message, heading, True, time_out,
                                       notify_obj)

                self.flag = StatusCode.HTTP_200_OK
            elif transfer_obj.status == 'completed':
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_trip_is_already_completed')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_trip_not_started')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


class StartTransferApi(ApiView):
    """Api to start a trip"""

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')
        user_profile = request.user_profile

        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            if transfer_obj.advance_received and transfer_obj.status == 'loading':
                # UPDATE TRANSFER TIME + 1 HR TO CONTINUE SEARCH
                transfer_obj.started_on = timezone.now()
                transfer_obj.status = 'in_transit'
                transfer_obj.save()

                # PUSH NOTIFICATION TO USER APP
                notify_obj = create_notification(transfer_obj, 'trip_started')
                time_out = int(timezone.timedelta(minutes=10).total_seconds() * 1000)

                heading = lang_obj.get_lang_word(request.language,
                                                 'lbl_push_notification_trip_started_heading')
                message = lang_obj.get_lang_word(request.language,
                                                 'lbl_push_notification_trip_started_message')

                # DELETE start_loading
                delete_notification(transfer_obj, 'trip_started', 'user')

                send_push_notification(transfer_obj, transfer_obj.added_by, message, heading, True, time_out,
                                       notify_obj)

                self.flag = StatusCode.HTTP_200_OK
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_advance_not_received')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST
        except Transfer.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class UpdatePartnerServiceableArea(ApiView):
    """Api for showing the serviceable area and update the same in partner app"""

    def get(self, request):
        dic = {}
        # GETTING ALL SERVICEABLE AREA OF THE DRIVER
        serviceable_areas = ServiceableArea.objects.filter(driver_id=request.user_profile)
        serviceable_area_list = []
        for serviceable_area in serviceable_areas:
            area_dict = {}
            area_dict['latitude'] = serviceable_area.latitude
            area_dict['longitude'] = serviceable_area.longitude
            area_dict['loc_name'] = serviceable_area.loc_name
            serviceable_area_list.append(area_dict)
        dic['serviceable_area'] = serviceable_area_list

        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        serviceable_area = request.DATA.get('serviceable_area', '')
        user_profile = request.user_profile

        if serviceable_area not in self.NULL_VALUE_VALIDATE:
            # Deleting existing serviceable_areas
            ServiceableArea.objects.filter(driver_id=user_profile).delete()

            # and adding new serviceable_areas
            for serviceable_area_dict in serviceable_area:
                latitude = serviceable_area_dict['latitude']
                longitude = serviceable_area_dict['longitude']
                if 'loc_name' in serviceable_area_dict:
                    loc_name = serviceable_area_dict['loc_name']
                else:
                    loc_name = get_city_from_location(latitude, longitude)
                servobj_obj = ServiceableArea(
                    latitude=latitude, longitude=longitude, loc_name=loc_name, driver_id=user_profile)
                servobj_obj.save()
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_upd_success')
            self.flag = StatusCode.HTTP_200_OK
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class SaveLocationApi(ApiView):
    """Api for saving the locations from user app and listing them"""

    def get(self, request):
        dic = {}
        # GETTING ALL SERVICEABLE AREA OF THE DRIVER
        saved_locations = SavedLocations.objects.filter(user_id=request.user_profile)
        saved_list = []
        for loc in saved_locations:
            area_dict = {}
            area_dict['id'] = loc.id
            area_dict['latitude'] = loc.latitude
            area_dict['longitude'] = loc.longitude
            area_dict['location_name'] = loc.loc_name
            saved_list.append(area_dict)
        dic['saved_locations'] = saved_list

        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        latitude = request.DATA.get('latitude', '')
        longitude = request.DATA.get('longitude', '')
        location_name = request.DATA.get('location_name', '')
        user_profile = request.user_profile

        if latitude and longitude and location_name not in self.NULL_VALUE_VALIDATE:
            # saving new location
            if not SavedLocations.objects.filter(latitude=latitude, longitude=longitude, user_id=user_profile).exists():
                loc_obj = SavedLocations(
                    latitude=latitude, longitude=longitude, loc_name=location_name, user_id=user_profile)
                loc_obj.save()
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_location_saved')
                self.flag = StatusCode.HTTP_200_OK
            else:
                dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_location_already_save')
                self.flag = StatusCode.HTTP_200_OK
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)

    @method_decorator(get_raw_data)
    def delete(self, request, **kwargs):
        dic = {}
        loc_id = request.DATA.get('loc_id', '')
        user_profile = request.user_profile

        if loc_id not in self.NULL_VALUE_VALIDATE:
            # Deleting the saved location
            SavedLocations.objects.filter(id=loc_id, user_id=user_profile).delete()
            self.flag = StatusCode.HTTP_200_OK
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class ViewDocumentsApi(ApiView):
    """Api for listing the documents"""

    def get(self, request):
        dic = {}
        # GETTING ALL documents wih type
        if request.language == 'en':
            documents = Documents.objects.filter(language='en')
        else:
            documents = Documents.objects.filter(language='es')
        document_list = []
        for document in documents:
            document_dict = {}
            document_dict['document_type'] = document.document_type
            document_dict['document'] = document.document
            document_list.append(document_dict)
        dic['documents'] = document_list
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class DriverLocationApi(ApiView):
    """Api for driver location for trip details map"""

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')

        # trip_status = Transfer.objects.filter(id=transfer_id).values('status').order_by('-id')
        # try:
        # statuses = ['accepted', 'loading', 'in_transit', 'completed']
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id, added_by=request.user_profile)
            # if trip_status:
            if transfer_obj.status not in ['completed', 'cancelled', 'auto_cancelled'] and transfer_obj.driver:
                dic['driver_lat'] = transfer_obj.driver.current_lat
                dic['driver_lng'] = transfer_obj.driver.current_lng
            dic['trip_status'] = {"status": transfer_obj.status}
            self.flag = StatusCode.HTTP_200_OK
        except:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        # except Transfer.DoesNotExist:
        #     dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
        #     self.flag = StatusCode.HTTP_400_BAD_REQUEST
        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class NotificationListApi(ApiView):
    """
    Api for Notification list
    """

    def get(self, request, **kwargs):
        notifications = NotificationHistory.objects.filter(user=request.user_profile, is_valid=True,
                                                           deleted=False).order_by('-id')
        history = []
        for notification in notifications:
            if notification.time_out:
                if notification.time_out < timezone.now():
                    continue
            # DELETE INVALID OFFERS
            if notification.notification_id.type in ['offer']:
                if notification.notification_id.offer_id.offer_valid_to < timezone.now().date():
                    notification.notification_id.deleted = True
                    notification.notification_id.is_valid = False
                    notification.notification_id.save()
                    continue

            if notification.notification_id.type == 'missed_transfer':
                continue
            dic = dict(id=notification.id, type=notification.notification_id.type,
                       headline=notification.notification_id.message_headline,
                       message=notification.notification_id.message,
                       time=int(notification.sent_on.strftime('%s')) * 1000, is_read=notification.read_status)
            if notification.notification_id.type not in ['promotion', 'offer']:
                dic['is_instant'] = notification.notification_id.transfer_id.instant_search
                dic['status'] = notification.notification_id.transfer_id.status
            if notification.notification_id.type == 'offer':
                dic['item_id'] = notification.notification_id.offer_id.id  # TODO: Change to promotion ID
            else:
                dic['item_id'] = notification.notification_id.transfer_id.id
            if notification.read_on:
                dic['read_on'] = int(notification.read_on.strftime('%s')) * 1000
            history.append(dic)

        return_history = []
        for each in history:
            flag = False
            for h in history:
                if h['item_id'] == each['item_id']:
                    if h['id'] > each['id']:
                        flag = True
                        continue
            if flag:
                continue
            return_history.append(each)

        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(return_history, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class NotificationStatusUpdateApi(ApiView):
    '''
    API to update notification read status from clients
    '''

    @method_decorator(get_raw_data)
    def post(self, request, *args, **kwargs):
        read_status = request.DATA.get('read', False)
        notification_id = request.DATA.get('notification_id', '')
        dic = []
        try:
            notify_obj = NotificationHistory.objects.get(id=notification_id)
            notify_obj.read_status = read_status
            notify_obj.read_on = timezone.now()
            notify_obj.save(update_fields=['read_status', 'read_on'])
            self.flag = StatusCode.HTTP_200_OK

        except NotificationHistory.DoesNotExist:
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class PartnerEarningsDetails(ApiView):
    """Api for getting all the earning details of partner"""

    def get(self, request, *args, **kwargs):
        dic = {}

        transfers = []
        for transfer in Transfer.objects.filter(driver=request.user_profile, status="completed").prefetch_related(
                'transferlocation_set').order_by('-id')[:10]:
            transfer_dict = {}
            locations = transfer.transferlocation_set.all()
            transfer_dict["id"] = transfer.id
            transfer_dict["user"] = transfer.added_by.user.get_full_name()
            transfer_dict["user_profile_pic"] = transfer.added_by.profile_pic or ""
            transfer_dict["amount"] = transfer.total_amount
            transfer_dict["payment_type"] = transfer.payment_type
            if len(locations) > 1:
                transfer_dict[locations[0].loc_type] = locations[0].location_name or ""
                transfer_dict[locations[1].loc_type] = locations[1].location_name or ""
            else:
                transfer_dict["pickup"] = ""
                transfer_dict["drop"] = ""

            transfers.append(transfer_dict)

        dic["transfers"] = transfers
        dic["security_deposit"] = "{0:.2f}".format(request.user_profile.vehicledetails.security_deposit)
        try:
            last_payout = PayoutHistory.objects.filter(driver=request.user_profile, date__date=timezone.now().date(),
                                                       payment_processed=False).latest('id')
            if last_payout:
                dic["payout"] = "{0:.2f}".format(last_payout.net_payable_for_driver)
        except:
            dic["payout"] = "0.00"
            dic["earnings"] = "0.00"
        current_payout = calculate_driver_payout(request.user_profile, timezone.now() + timedelta(days=1),
                                                 shouldSave=False)
        if current_payout:
            earnings = current_payout['total_bookings_amount'] - current_payout['commission_amount_to_muberz']
            dic["earnings"] = "{0:.2f}".format(earnings)
        else:
            dic["payout"] = "0.00"
            dic["earnings"] = "0.00"
        return JsonWrapper(dic, StatusCode.HTTP_200_OK)


@method_decorator((verify_access_token, get_raw_data), name='dispatch')
class UserTransferCancelApi(ApiView):
    """Api for cancelling a trip/transfer"""

    def put(self, request, *args, **kwargs):
        dic = {}

        transfer_id = request.DATA.get('transfer_id', '')

        if transfer_id not in self.NULL_VALUE_VALIDATE:
            try:
                transfer = Transfer.objects.get(id=transfer_id, added_by=request.user_profile)
                if transfer.status != 'cancelled' and transfer.status != 'auto_cancelled':
                    transfer.status = "cancelled"
                    notification_types = ['trip_request', 'trip_scheduled', 'trip_reminder']
                    NotificationHistory.objects.filter(notification_id__transfer_id=transfer,
                                                       notification_id__type__in=notification_types).update(
                        is_valid=False)
                    transfer.save(update_fields=['status'])

                    '''
                    Initiate Refund
                    '''
                    try:
                        if not transfer.refund_initiated and transfer.payment_type == 'card':
                            peru_timezone = pytz.timezone('America/Lima')
                            RefundManagement.objects.create(added_by=transfer.added_by,
                                                            refund_cause='User cancelled the transfer',
                                                            date_added=timezone.now(),
                                                            amount_to_refund=transfer.total_amount,
                                                            transfer=transfer, status='requested')
                            transfer.refund_initiated = True
                            transfer.save()
                            notify_obj = create_notification(transfer, "refund_initiated")
                            transfer_time = transfer.transfer_on.astimezone(peru_timezone).strftime(
                                "%A, %B %d at %I:%M %p")
                            logger_me.debug('request.language')
                            logger_me.debug(request.language)
                            status = send_push_notification(transfer, transfer.added_by,
                                                            lang_obj.get_lang_word(request.language,
                                                                                   'lbl_refund_requested').format(
                                                                transfer_time), lang_obj.get_lang_word(request.language,
                                                                                                       'lbl_refund_requested_heading'),
                                                            time_out=0,
                                                            notify_obj=notify_obj, should_save=True)
                            if status == 1:
                                logger_me.debug("User notified about refund request - trip cancellation")
                            else:
                                notify_obj.delete()
                                logger_me.debug("APNS failed!")
                    except:
                        logger_me.debug("Couldn't create an refund management object")

                    '''
                    Refund Completed
                    '''

                    dic["message"] = lang_obj.get_lang_word(request.language, 'lbl_trip_cancelled')
                    self.flag = StatusCode.HTTP_200_OK
                    # PUSH TO DRIVER
                    if transfer.driver:
                        if transfer.driver.user:
                            heading = lang_obj.get_lang_word(request.language, 'lbl_trip_cancelled_heading')
                            message_body = lang_obj.get_lang_word(request.language, 'lbl_trip_cancelled_by_user')
                            notify_obj = create_notification(transfer, 'trip_cancelled')
                            # DELETE TRIP ACCEPTED 'trip_request' or 'trip_reminder'
                            delete_notification(transfer, 'trip_cancelled', 'user')
                            send_push_notification(transfer, transfer.driver, message_body, heading, True, 0,
                                                   notify_obj)

                elif transfer.status == 'in_transit' or transfer.status == 'loading':
                    dic["message"] = lang_obj.get_lang_word(request.language,
                                                            'lbl_transfer_is_already_started')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
                elif transfer.status == 'cancelled' or transfer.status == 'auto_cancelled':
                    dic["message"] = "This transfer is already canceled"
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST
                else:
                    dic["message"] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                    self.flag = StatusCode.HTTP_400_BAD_REQUEST

            except Transfer.DoesNotExist:
                dic["message"] = lang_obj.get_lang_word(request.language, 'lbl_invalid_transfer')
                self.flag = StatusCode.HTTP_400_BAD_REQUEST

        else:
            dic["message"] = lang_obj.get_lang_word(request.language, 'lbl_provide_all_params')
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class PayoutRequest(ApiView):
    """
        API for testing
    """

    def get(self, request, *args, **kwargs):
        go_back = 1
        driver_obj = request.user_profile
        dic = {}
        # dic = calculate_driver_payout(driver_obj, shouldSave=False)
        logger_me.debug("days goback:")
        logger_me.debug(timezone.now() - timedelta(go_back))
        dic = calculate_driver_payout(driver_obj, shouldSave=False)
        # if dic:
        #     dic = {'message': 'Payout calculation succeeded'}
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class CityNameFromLocation(ApiView):
    def get(self, request, *args, **kwargs):
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        district_name = get_city_from_location(lat, lng)
        result = {}
        if district_name != "":
            result["city"] = district_name
            self.flag = StatusCode.HTTP_200_OK
        else:
            result['message'] = "Muberz do not have services in this city"
        return JsonWrapper(result, self.flag)


class DistrictNameFromLocation(ApiView):
    def get(self, request, *args, **kwargs):
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        city_name = get_district_from_location(lat, lng)
        result = {}
        if city_name != "":
            result["city"] = city_name
            self.flag = StatusCode.HTTP_200_OK
        else:
            result['message'] = "Muberz do not have services in this district"
        return JsonWrapper(result, self.flag)


class AddressFromLocation(ApiView):
    def get(self, request, *args, **kwargs):
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        city_name = get_address_from_location(lat, lng)
        result = {}
        if city_name != "":
            result["Place"] = city_name
            self.flag = StatusCode.HTTP_200_OK
        else:
            result['message'] = "Muberz donot have services in this city"
        return JsonWrapper(result, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class StartLoadingRequest(ApiView):
    '''
    API for partners to initiate loading of commodities
    '''

    @method_decorator(get_raw_data)
    def post(self, request, *args, **kwargs):
        latitude = request.DATA.get('latitude', "")
        longitude = request.DATA.get('longitude', "")
        trip_id = request.DATA.get('trip_id', "")
        dict = {
            "message": "Failure"
        }
        if latitude != "" and longitude != "" and trip_id != "":
            transfers = Transfer.objects.filter(id=trip_id, status='accepted').order_by('-id')
            if transfers:
                transfer = transfers[0]
                transfer.status = 'loading'
                transfer.save()
                dict["message"] = "Success"
                transfer.driver.in_trip = True
                transfer.driver.save()
                if transfer.added_by.user:
                    heading = lang_obj.get_lang_word(request.language,
                                                     'lbl_push_notification_trip_loading_heading')
                    message_body = lang_obj.get_lang_word(request.language,
                                                          'lbl_push_notification_trip_loading_message')

                    # DELETE start_accepted
                    delete_notification(transfer, 'start_loading', 'user')

                    notify_obj = create_notification(transfer, 'start_loading')
                    send_push_notification(transfer, transfer.added_by, message_body, heading, True, 0, notify_obj)
                self.flag = StatusCode.HTTP_200_OK
            else:
                self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dict, self.flag)


@method_decorator((verify_access_token, get_raw_data), name='dispatch')
class GetVehicleDetails(ApiView):
    '''
    API to get the vehicle details based on the trip ID
    '''

    def post(self, request, *args, **kwargs):
        transfer_id = request.DATA.get('transfer_id')
        details = {}
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id, added_by=request.user_profile)
            if transfer_obj.driver:
                try:
                    vehicle = VehicleDetails.objects.get(driver_id=transfer_obj.driver)
                    assistants = Assistants.objects.filter(driver_id=transfer_obj.driver).values('assistant_name',
                                                                                                 'photo')

                    details['driver_name'] = transfer_obj.driver.user.get_full_name()
                    details['contact_number'] = transfer_obj.driver.user.username
                    details['driver_photo'] = transfer_obj.driver.profile_pic
                    details['trip_amount'] = round(transfer_obj.total_amount, 2)
                    details['payment_type'] = transfer_obj.payment_type
                    details['reg_no'] = vehicle.reg_no
                    details['no_assistants'] = get_no_assistant(vehicle.vehicle_volume, transfer_obj.driver.city)
                    details['assistants'] = list(assistants)
                    self.flag = StatusCode.HTTP_200_OK

                except VehicleDetails.DoesNotExist:
                    details['message'] = "No such vehicle found"
                    self.flag = StatusCode.HTTP_403_FORBIDDEN

        except Transfer.DoesNotExist:
            details['message'] = "No such transfer found"
            self.flag = StatusCode.HTTP_403_FORBIDDEN

        return JsonWrapper(details, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class UserAppStatusCheckAPI(ApiView):
    '''
    API to get the vehicle details based on the trip ID
    '''

    def get(self, request, *args, **kwargs):
        response_dict = {}
        statuses = ['active', 'accepted', 'loading', 'in_transit']
        transfer_objects = Transfer.objects.filter(added_by=request.user_profile, status__in=statuses,
                                                   instant_search=True).order_by(
            '-id')
        if transfer_objects:
            response_dict['status'] = transfer_objects[0].status
            response_dict['transfer_id'] = transfer_objects[0].id
        else:
            response_dict['message'] = "you are clear to request a new transfer"

        response_dict['user_rating'] = round(request.user_profile.rating, 1)
        response_dict['userTokenID'] = request.user_profile.visaUserToken
        not_count = get_notification_count(request.user_profile)

        response_dict['not_count'] = not_count
        self.flag = StatusCode.HTTP_200_OK

        return JsonWrapper(response_dict, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class PartnerPendingApproval(ApiView):
    '''
    API to get the vehicle details based on the trip ID
    '''

    def get(self, request, *args, **kwargs):
        response_dict = {}
        if request.user_profile.status == 'active':
            message = "Truck Approved"
            self.flag = StatusCode.HTTP_200_OK
        else:
            vehicle = VehicleDetails.objects.get(driver_id=request.user_profile)
            required_deposit = SecurityDeposit.objects.filter(capacity_from__lte=vehicle.vehicle_volume,
                                                              capacity_to__gte=vehicle.vehicle_volume,
                                                              added_by__city=request.user_profile.city).values(
                'deposit_needed')
            if required_deposit:
                message = lang_obj.get_lang_word(request.language, 'lbl_pending_approval').format(
                    required_deposit[0]['deposit_needed'])

                # message = "Please bring your truck and original documents to our office along with a security deposit " \
                #           "of {0} Sol for inspection and approval.".format(required_deposit[0]['deposit_needed'])
                response_dict['message'] = message
            else:
                message = lang_obj.get_lang_word(request.language, 'lbl_pending_approval_new')

        response_dict['message'] = message
        return JsonWrapper(response_dict, self.flag)


def get_report_damage_status(transfer_obj, transfer_loc):
    """
    :param transfer_obj:
    :param transfer_loc:
    :return: true, if report damage flag need to be shown in app.
    """
    commodity_list = []
    commodities = TransferCommodity.objects.filter(transfer_loc_id=transfer_loc).values(
        'item__id').distinct().annotate(models.Count('id'))
    for commodity_obj in commodities:
        try:
            total = 0
            comm_obj = Commodity.objects.get(id=commodity_obj['item__id'])
            for damage in Damage.objects.filter(transfer_id=transfer_obj, item_id=comm_obj):
                total += damage.count
            if int(commodity_obj['id__count']) > int(total):
                commodity_list.append(comm_obj.id)
        except Commodity.DoesNotExist:
            pass
    if commodity_list:
        return True
    else:
        return False


def get_notification_count(base_profile):
    """
    :param: base_profile
    :return: notification count
    """
    notifications = NotificationHistory.objects.filter(user=base_profile, is_valid=True,
                                                       deleted=False).order_by('-id')
    history = []
    for notification in notifications:
        if notification.time_out:
            if notification.time_out < timezone.now():
                continue
        if notification.notification_id.type == 'missed_transfer':
            continue
        dic = dict(id=notification.id, is_read=notification.read_status)
        if notification.notification_id.type == 'offer':
            dic['item_id'] = notification.notification_id.offer_id.id  # TODO: Change to promotion ID
        else:
            dic['item_id'] = notification.notification_id.transfer_id.id
        if notification.read_on:
            dic['read_on'] = int(notification.read_on.strftime('%s')) * 1000
        history.append(dic)

    return_history = []
    for each in history:
        flag = False
        for h in history:
            if h['item_id'] == each['item_id']:
                if h['id'] > each['id']:
                    flag = True
                    continue
        if flag:
            continue
        if not each['is_read']:
            return_history.append(each)
    return len(return_history)


def get_user_can_rate_trip(transfer, user):
    """

    :param transfer: transfer object
    :param user: user obj
    :return: if user can rate(trip completed & no rated before) return true, else false
    """
    if transfer.status == 'completed':
        if not Rating.objects.filter(rating_from=user, transfer_id=transfer):
            return True
        else:
            return False
    else:
        return False


@method_decorator((verify_access_token, get_raw_data), name='dispatch')
class GetPaymentStatus(ApiView):
    '''
    API to get the payment status of a Trip
    '''

    def post(self, request, *args, **kwargs):
        transfer_id = request.DATA.get('transfer_id')
        dic = {}
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id, added_by=request.user_profile)

            dic['advance_received'] = transfer_obj.advance_received
            dic['total_amount'] = transfer_obj.total_amount
            self.flag = StatusCode.HTTP_200_OK
        except Transfer.DoesNotExist:
            dic['message'] = "No such transfer found"
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


@method_decorator((verify_access_token, get_raw_data), name='dispatch')
class ServiceAvailabilityAPI(ApiView):
    '''
    API to get the Service Availability of pickup and drop
    '''

    def post(self, request, *args, **kwargs):
        pickup_lat = request.DATA.get('pickup_lat', '')
        pickup_lng = request.DATA.get('pickup_lng', '')
        drop_lat = request.DATA.get('drop_lat', '')
        drop_lng = request.DATA.get('drop_lng', '')

        pickup_location = get_city_from_location(pickup_lat, pickup_lng)
        drop_location = get_city_from_location(drop_lat, drop_lng)
        logger_me.debug('pickup_location' + str(pickup_location))
        logger_me.debug('drop_location' + str(drop_location))
        dic = {}
        if pickup_location == drop_location:
            dic['message'] = "Success"
            self.flag = StatusCode.HTTP_200_OK
        else:
            dic['message'] = lang_obj.get_lang_word(request.language, 'lbl_service_not_available')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


# @method_decorator((verify_access_token), name='dispatch')
class GetVisaCreds(ApiView):
    """
        API for testing
    """

    def get(self, request, *args, **kwargs):
        is_debug = request.GET.get('is_debug', '')
        dic = {}
        if is_debug != '':
            if is_debug == 'true':
                visa_merch_id = get_config('VISA_MERCHANT_STG_ID')
                visa_access_id = get_config('VISA_ACCESS_KEY_STG_ID')
                visa_secret_success = get_config('VISA_SECRET_STG_ACCESS')
            elif is_debug == 'false':
                visa_merch_id = get_config('VISA_MERCHANT_ID')
                visa_access_id = get_config('VISA_ACCESS_KEY_ID')
                visa_secret_success = get_config('VISA_SECRET_ACCESS')
            else:
                visa_merch_id = get_config('VISA_MERCHANT_STG_ID')
                visa_access_id = get_config('VISA_ACCESS_KEY_STG_ID')
                visa_secret_success = get_config('VISA_SECRET_STG_ACCESS')
        else:
            visa_merch_id = get_config('VISA_MERCHANT_STG_ID')
            visa_access_id = get_config('VISA_ACCESS_KEY_STG_ID')
            visa_secret_success = get_config('VISA_SECRET_STG_ACCESS')
        dic['visa_merch_id'] = visa_merch_id
        dic['visa_access_id'] = visa_access_id
        dic['visa_secret_access'] = visa_secret_success

        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


class GetCategoryList(ApiView):
    """
        API for testing
    """

    @method_decorator((verify_access_token, get_raw_data))
    def post(self, request, **kwargs):

        dic = {}
        trucks = []
        pickup_lat = request.DATA.get('pickup_lat', '')
        pickup_lng = request.DATA.get('pickup_lng', '')
        drop_lat = request.DATA.get('drop_lat', '')
        drop_lng = request.DATA.get('drop_lng', '')
        location_name = get_city_from_location(pickup_lat, pickup_lng)
        try:
            city_obj = City.objects.get(city_name=location_name)
            # admin_profile = BaseProfile.objects.get(user=self.request.user_profile.id)

            truck_crew_list = TruckCrew.objects.filter(added_by__city=city_obj)
            truck_types = TruckTypes.objects.all().order_by('vol_min')
            trucks = []
            for truck_type in truck_types:
                truck_loader = {}
                truck_loader["category_name"] = truck_type.category_name
                truck_loader["image"] = truck_type.image
                truck_loader["trucks"] = []
                trucks_data = VehicleDetails.objects.filter(added_by__city=city_obj,
                                                            vehicle_volume__lte=truck_type.vol_max,
                                                            vehicle_volume__gte=truck_type.vol_min)
                for truck in trucks_data:
                    result_dict = {}
                    result_dict['truck_volume'] = truck.vehicle_volume
                    if not any(d['truck_volume'] == truck.vehicle_volume for d in truck_loader["trucks"]):
                        truck_loader["trucks"].append(result_dict)

                # for x in range(int(truck_type.vol_min),int(truck_type.vol_max)+1):
                #     result_dict = {}
                #     result_dict['truck_volume'] = x
                #     truck_loader["trucks"].append(result_dict)
                if (truck_loader["trucks"]):
                    trucks.append(truck_loader)
                self.flag = StatusCode.HTTP_200_OK

            return JsonWrapper(trucks, self.flag)
        except City.DoesNotExist:
            dic['message'] = lang_obj.get_lang_word(request.language, 'No City Exist')
            self.flag = StatusCode.HTTP_403_FORBIDDEN
        return JsonWrapper(dic, self.flag)


class HelperCountPrice(ApiView):
    """
    An api for Return Price for helper count
    """

    @method_decorator(get_raw_data)
    def post(self, request):
        dict = {}
        helper_count = request.DATA.get('helper_count')
        if helper_count not in self.NULL_VALUE_VALIDATE:
            dict['price'] = helper_count * 2
            dict['helper_count'] = helper_count
            return JsonWrapper(dict, self.flag)


class ToggleSpecialHandling(ApiView):

    @method_decorator(get_raw_data)
    def post(self, request, **kwargs):
        dict = {}
        transfer_id = request.DATA.get('transfer_id')
        if transfer_id not in self.NULL_VALUE_VALIDATE:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            transfer_obj.is_special_handling_required = not transfer_obj.is_special_handling_required
            transfer_obj.save()
            dict['message'] = "Toggled is_special_handling_required"
            self.flag = StatusCode.HTTP_200_OK
            return JsonWrapper(dict, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class PromotionListApi(ApiView):
    """
    Api for Notification list
    """

    def get(self, request, **kwargs):
        promotions = Promotion.objects.all()
        history = []
        for promotion in promotions:
            if promotion.expiry:
                if promotion.expiry < timezone.now():
                    continue
            # DELETE INVALID OFFERS
            dic = dict(id=promotion.id, name=promotion.name,
                       percentage=promotion.percentage,
                       short_description=promotion.short_description,
                       description=promotion.description,
                       expiry=promotion.expiry)
            history.append(dic)
        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(history, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class AdsListApi(ApiView):

    @method_decorator(get_raw_data)
    def post(self, request):
        dic = {}
        user_type = request.DATA.get('user_type')
        if user_type == 'user':
            try:
                ads_obj = Advertisement.objects.filter(user=True)
                ads_list = []
                for ads in ads_obj:
                    dict = {}
                    dict['header'] = ads.name
                    dict['start_date'] = ads.date_start
                    dict['end_date'] = ads.date_end
                    dict['image'] = ads.image
                    dict['added_on'] = ads.added_on
                    ads_list.append(dict)
                self.flag = StatusCode.HTTP_200_OK
                return JsonWrapper(ads_list, self.flag)
            except Advertisement.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'No Ads Exist')
                self.flag = StatusCode.HTTP_403_FORBIDDEN
                return JsonWrapper(dic, self.flag)
        elif user_type == 'partner':
            try:
                ads_obj = Advertisement.objects.filter(partner=True)
                ads_list = []
                for ads in ads_obj:
                    dict = {}
                    dict['header'] = ads.name
                    dict['start_date'] = ads.date_start
                    dict['end_date'] = ads.date_end
                    dict['image'] = ads.image
                    dict['added_on'] = ads.added_on
                    ads_list.append(dict)
                self.flag = StatusCode.HTTP_200_OK
                return JsonWrapper(ads_list, self.flag)
            except Advertisement.DoesNotExist:
                dic['message'] = lang_obj.get_lang_word(request.language, 'No Ads Exist')
                return JsonWrapper(dic, self.flag)
        else:
            self.flag = StatusCode.HTTP_403_FORBIDDEN
            dic['message'] = lang_obj.get_lang_word(request.language, 'No Ads Exist')
            return JsonWrapper(dic, self.flag)


class GetDriverLocation(ApiView):

    def get(self, request):
        dic = {}
        logger_me.debug(request)

        trans_id = request.GET.get('transfer_id')
        try:
            dict = {}
            driver_obj = Transfer.objects.get(id=trans_id).driver
            dict['driver_lat'] = driver_obj.current_lat
            dict['driver_long'] = driver_obj.current_lng
            self.flag = StatusCode.HTTP_200_OK
            return JsonWrapper(dict, self.flag)
        except Transfer.DoesNotExist:
            dic['message'] = "Toggled is_special_handling_required"
            self.flag = StatusCode.HTTP_403_FORBIDDEN
            return JsonWrapper(dic, self.flag)


@method_decorator(verify_access_token, name='dispatch')
class PartnerTripShare(ApiView):

    @method_decorator(get_raw_data)
    def post(self, request):
        dic = {}
        transfer_id = request.DATA.get('transfer_id', '')
        if transfer_id != '':
            try:
                Transfer.objects.filter(id=transfer_id).update(share_trip=True)
                dic['message'] = "Informed to the admin"
                self.flag = StatusCode.HTTP_200_OK
                return JsonWrapper(dic, self.flag)
            except Transfer.DoesNotExist:
                dic['message'] = "Object not exist"
                self.flag = StatusCode.HTTP_403_FORBIDDEN
            return JsonWrapper(dic, self.flag)
        else:
            dic['message'] = "Something wend wrong"
            self.flag = StatusCode.HTTP_403_FORBIDDEN
            return JsonWrapper(dic, self.flag)


class GetNearbyDrivers(ApiView):

    def get(self, request):
        transfer_id = request.GET.get('transfer_id')
        transfer_obj = Transfer.objects.get(id=transfer_id)
        tot_volume = transfer_obj.tot_volume
        if tot_volume < 1:
            tot_volume = 1
        vehicle_max_size = tot_volume * 2  # 200 % of requested size
        logger_me.debug('vehicle_max_size')
        logger_me.debug(vehicle_max_size)
        logger_me.debug("drivers")
        if transfer_obj.source == 'Commodity':
            transfer_commodity = \
            TransferCommodity.objects.filter(transfer_loc_id__transfer_id=transfer_obj).order_by('-item__height')[0]
            min_height = transfer_commodity.item.height
            drivers = BaseProfile.objects.filter(user_type='driver', status='active', drive_status=True,
                                                 current_lat__isnull=False, current_lng__isnull=False,
                                                 in_trip=False,
                                                 vehicledetails__vehicle_volume__lte=vehicle_max_size,
                                                 vehicledetails__vehicle_volume__gte=tot_volume,
                                                 vehicledetails__vehicle_height__gte=min_height)
        else:
            drivers = BaseProfile.objects.filter(user_type='driver', status='active', drive_status=True,
                                                 current_lat__isnull=False, current_lng__isnull=False,
                                                 in_trip=False,
                                                 vehicledetails__vehicle_volume__lte=vehicle_max_size,
                                                 vehicledetails__vehicle_volume__gte=tot_volume)

        transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')

        driver_with_distance = []
        for driver_obj in drivers:
            distance, duration, duration_in_sec, distance_in_km = get_distance_matrix(driver_obj.current_lat,
                                                                                      driver_obj.current_lng,
                                                                                      transfer_pickup.loc_lat,
                                                                                      transfer_pickup.loc_lng)
            dict = {}
            dict['distance'] = distance_in_km
            dict['driver_name'] = driver_obj.user.first_name
            dict['driver_id'] = driver_obj.id
            driver_with_distance.append(dict)

            # driver_obj.distance = distance_in_km
            # logger_me.debug(driver_obj)
            # driver_with_distance.append(driver_obj)

            # if driver_obj.city.city_name != transfer_obj.city.city_name:
            #     exclude_drivers.append(driver_obj.id)
            #     continue
        self.flag = StatusCode.HTTP_200_OK
        # driver_with_distance['message'] = "driver objected listed"
        return JsonWrapper(driver_with_distance, self.flag)
