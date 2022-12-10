import logging

from django.core.exceptions import MultipleObjectsReturned
from push_notifications.apns import APNSServerError
from push_notifications.models import GCMDevice, APNSDevice

from api_base.default import get_distance_matrix, LanguageConversion
from api_base.models import *
# from api_base.push import send_push_notification
# from api_base.push import send_push_notification
from dashboard.payout import calculate_driver_payout

logger_me = logging.getLogger('debug')
lang_obj = LanguageConversion()


class SearchDrivers(object):
    """TO SEARCH DRIVERS"""

    def search_drivers(self, transfer_obj, instant_search, language='es'):
        # TAKE ALL ACTIVE DRIVERS WITH STATUS TRUE
        tot_volume = transfer_obj.tot_volume
        if tot_volume < 1:
            tot_volume = 1
        vehicle_max_size = tot_volume * 2  # 200 % of requested size
        logger_me.debug('vehicle_max_size')
        logger_me.debug(vehicle_max_size)

        # if max volume is invalid as per all vehicles, reset max vol
        # COMMENDED AS PER CLIENT SUGGESTION
        # available_volumes_list = sorted(set(list(VehicleDetails.objects.filter(driver_id__status='active', driver_id__drive_status=True, driver_id__current_lat__isnull=False, driver_id__current_lng__isnull=False, driver_id__in_trip=False).values_list('vehicle_volume', flat=True))))
        # for volume in available_volumes_list:
        #     if tot_volume <= volume:
        #         if not volume <= vehicle_max_size:
        #             vehicle_max_size = volume
        #             break

        # transfer_loc = TransferLocation.objects.get(transfer_id=transfer_obj,loc_type='Pickup')

        logger_me.debug("drivers")

        if transfer_obj.source == 'Commodity':
            transfer_commodity = \
            TransferCommodity.objects.filter(transfer_loc_id__transfer_id=transfer_obj).order_by('-item__height')[0]
            min_height = transfer_commodity.item.height
            drivers = BaseProfile.objects.filter(user_type='driver', status='active', drive_status=True,
                                             current_lat__isnull=False, current_lng__isnull=False, in_trip=False,
                                             vehicledetails__vehicle_volume__lte=vehicle_max_size,
                                             vehicledetails__vehicle_volume__gte =tot_volume, vehicledetails__vehicle_height__gte=min_height)
        else:
            drivers = BaseProfile.objects.filter(user_type='driver', status='active', drive_status=True,
                                                 current_lat__isnull=False, current_lng__isnull=False, in_trip=False,
                                                 vehicledetails__vehicle_volume__lte=vehicle_max_size,
                                                 vehicledetails__vehicle_volume__gte=tot_volume)

        # To log reasons for driver rejection:
        for each in BaseProfile.objects.filter(user_type='driver').exclude(status='active'):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Driver Status is not 'active'")
        for each in BaseProfile.objects.filter(user_type='driver').exclude(drive_status=True):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Drive_Status is false")
        for each in BaseProfile.objects.filter(user_type='driver').exclude(current_lat__isnull=False):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Driver location is not available")
        for each in BaseProfile.objects.filter(user_type='driver').exclude(current_lng__isnull=False):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Driver location is not available")
        for each in BaseProfile.objects.filter(user_type='driver').exclude(in_trip=False):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Driver is in another trip")
        for each in BaseProfile.objects.filter(user_type='driver').exclude(
                vehicledetails__vehicle_volume__lte=vehicle_max_size):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Truck volume is more than 200% of total transfer volume")
        for each in BaseProfile.objects.filter(user_type='driver').exclude(
                vehicledetails__vehicle_volume__gte=tot_volume):
            SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=each,
                                           reason="Truck volume is lesser than total transfer volume")

        # GET PICKUP AND DROP LOCATIONS IT RETURNS ONLY 1 RESULT , CHANGE IT FOR MULTIPICKUP/DROP
        transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
        transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')

        exclude_drivers = []
        logger_me.debug(drivers)
        for driver_obj in drivers:
            distance, duration, duration_in_sec, distance_in_km = get_distance_matrix(driver_obj.current_lat,
                                                                                      driver_obj.current_lng,
                                                                                      transfer_pickup.loc_lat,
                                                                                      transfer_pickup.loc_lng)

            setattr(driver_obj, 'time_needed', duration)

            if driver_obj.city.city_name != transfer_obj.city.city_name:
                exclude_drivers.append(driver_obj.id)
                continue

            if instant_search:
                max_duration = 5400
            else:
                max_duration = (transfer_obj.transfer_on - timezone.now()).total_seconds()

                if max_duration < 0:
                    max_duration = 0

            if int(duration_in_sec) > max_duration or int(duration_in_sec) <= 0:  # IF DRIVER CAN'T REACH IN 90 MINUTES
                exclude_drivers.append(driver_obj.id)
                reason = "Driver can't reach in time"
                SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=driver_obj, reason=reason)
            else:
                try:
                    req_obj = TruckRequest.objects.get(transfer_id=transfer_obj, driver_id=driver_obj, status__in=['sent', 'rejected'])
                    # IF ALREADY SENT A REQUEST AND IS NOT TIMED OUT
                    if req_obj.status == 'sent':
                        reason = "Driver already received this request and it is not timed out"
                    else:
                        reason = "Driver already rejected this request"
                    exclude_drivers.append(driver_obj.id)
                    SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=driver_obj, reason=reason)
                except TruckRequest.DoesNotExist:
                    pass

                if not self.driver_can_transfer(transfer_obj, driver_obj):
                    exclude_drivers.append(driver_obj.id)
                    reason = "Driver can't transfer due to insufficient funds"
                    exclude_drivers.append(driver_obj.id)
                    SearchFailedLog.objects.create(transfer=transfer_obj, user=transfer_obj.added_by.user.username, excluded_driver=driver_obj, reason=reason)

        # IF REQUEST NOW
        # if instant_search:
        #
        #
        # else:
        #     for driver_obj in drivers:
        #         error_flag = True
        #         if driver_obj.city.city_name != transfer_obj.city.city_name:
        #             exclude_drivers.append(driver_obj.id)
        #             continue
        #
        #         if self.check_location_in_serviceable_area(driver_obj, transfer_pickup.loc_lat,
        #                                                    transfer_pickup.loc_lng):
        #             logger_me.debug('in check_location_in_serviceable_area')
        #             if self.driver_can_transfer(transfer_obj, driver_obj):
        #                 logger_me.debug('in driver_can_transfer')
        #                 try:
        #                     distance, duration, duration_in_sec, distance_in_km = get_distance_matrix(
        #                         driver_obj.current_lat, driver_obj.current_lng, transfer_pickup.loc_lat,
        #                         transfer_pickup.loc_lng)
        #                     setattr(driver_obj, 'time_needed', duration)
        #                     time_needed = timezone.now() + timezone.timedelta(seconds=duration_in_sec)
        #                     logger_me.debug(transfer_obj.transfer_on)
        #                     if time_needed < (transfer_obj.transfer_on + timezone.timedelta(hours=1)):
        #                         logger_me.debug('success')
        #                         error_flag = False
        #                 except:
        #                     pass
        #         if error_flag:
        #             logger_me.debug('error')
        #             exclude_drivers.append(driver_obj.id)

        self.request_transfer_to_drivers(drivers, exclude_drivers, transfer_obj, instant_search, language)
        return True

    @staticmethod
    def request_transfer_to_drivers(drivers, exclude_drivers, transfer_obj, instant_search, language='es'):
        if instant_search is True:
            time_out = int(timezone.timedelta(seconds=30).total_seconds() * 1000)
        else:
            time_out = int((transfer_obj.transfer_on - timezone.timedelta(hours=1)).strftime('%s')) * 1000

        logger_me.debug("Drivers - ALL")
        if len(drivers) > 0:
            for each in drivers:
                logger_me.debug(each.user.first_name)
            logger_me.debug("Drivers - Excluded")
            for each in exclude_drivers:
                logger_me.debug('- id: ')
                logger_me.debug(each)
        else:
            logger_me.debug('No drivers available')

        notify_obj = create_notification(transfer_obj, 'trip_request')

        for driver_obj in drivers:
            # EXCLUDE DRIVERS WHO ARE NOT ABLE TO GET THE REQUEST
            if driver_obj.id not in exclude_drivers:
                logger_me.debug('language')
                logger_me.debug(language)
                new_transfer_request_heading = lang_obj.get_lang_word(language, 'lbl_new_transfer_request_heading')
                new_transfer_request = lang_obj.get_lang_word(language, 'lbl_new_transfer_request').format(transfer_obj.added_by.user.first_name, driver_obj.time_needed)
                # message = "New transfer request from a user " + transfer_obj.added_by.user.first_name + ", which is " + driver_obj.time_needed + " away from your location."
                message = new_transfer_request
                if send_push_notification(transfer_obj, driver_obj, message, new_transfer_request_heading, True, time_out,
                                          notify_obj):
                    TruckRequest.objects.create(transfer_id=transfer_obj, driver_id=driver_obj, status='sent')
        return True

    def check_location_in_serviceable_area(self, driver_obj, lat, lng):

        serviceable_areas = ServiceableArea.objects.filter(driver_id=driver_obj)
        for area in serviceable_areas:
            try:
                if get_distance_matrix(area.latitude, area.longitude, lat, lng)[3] < 10:  # DISTANCE BELOW 10 KMS
                    return True
            except:
                return False

        return False

    def driver_can_transfer(self, transfer_obj, driver_obj):
        # IF THE SECURITY DEPOSIT < THE AMOUNT OF THE TRANSFER
        try:
            veh_obj = VehicleDetails.objects.get(driver_id=driver_obj)
            total_amount = float(transfer_obj.total_amount)
            amount_paid = float(transfer_obj.amount_paid)
            tot_volume = float(transfer_obj.tot_volume)
            security_deposit = float(veh_obj.security_deposit)
            vehicle_volume = float(veh_obj.vehicle_volume)
            if tot_volume < 1:
                tot_volume = 1
            """
            DRIVER CAN ATTEND THIS TRANSFER ONLY IF
            # trip_commsion_to_muberz <= (net_payable_for_driver + security_deposit)
            """

            payout_obj = calculate_driver_payout(driver_obj, shouldSave=False)
            total_amount_of_driver = 0
            if payout_obj:
                total_amount_of_driver = float(payout_obj['net_payable_for_driver'])
            total_amount_of_driver += float(veh_obj.security_deposit)

            # UPDATE COMMISSION TO MUBERZ
            trip_commsion_to_muberz = 0
            if driver_obj.fleet_id:
                commision = driver_obj.fleet_id.commission
            else:
                commision = driver_obj.commission

            if commision > 0:
                trip_commsion_to_muberz = (total_amount * commision) / 100

            # if (total_amount - amount_paid) <= security_deposit:
            if trip_commsion_to_muberz <= total_amount_of_driver:
                return True
            else:
                amount_needs = trip_commsion_to_muberz - total_amount_of_driver
                # amount_needs = total_amount - amount_paid - security_deposit
                message = "You just missed a transfer request as your security deposit is lesser by " + str(
                    amount_needs) + ". Please consider topup your security deposit to get more transfer requests."
                # time_out = int(timezone.timedelta(minutes=10).total_seconds() * 1000)
                notify_obj = create_notification(transfer_obj, 'missed_transfer')
                send_push_notification(transfer_obj, driver_obj, message, "", False, 0, notify_obj)
                return False
        except VehicleDetails.DoesNotExist:
            return False
        except MultipleObjectsReturned:
            return False


def create_notification(transfer_obj, notification_type):
    previous_notifications = Notifications.objects.filter(transfer_id=transfer_obj, type=notification_type)
    if previous_notifications:
        previous_notifications.update(deleted=True)
    not_obj = Notifications.objects.create(transfer_id=transfer_obj, type=notification_type)
    return not_obj


def send_push_notification(transfer_obj, user_obj, message, message_headline='', should_save=False, time_out=0,
                           notify_obj=None):
    # thread.start_new_thread
    # driver_obj = BaseProfile.objects.get(id=17)
    user = user_obj.user
    gcm_device_list = GCMDevice.objects.filter(user=user)
    apns_device_list = APNSDevice.objects.filter(user=user)
    notification_type = ''
    logger_me.debug("notification started")
    logger_me.debug(gcm_device_list)
    logger_me.debug(apns_device_list)
    if notify_obj:
        notify_obj.message_headline = message_headline
        notify_obj.message = message
        notification_type = notify_obj.type
        notify_obj.receiver = user_obj
        notify_obj.save()
        print("Notify object updated")
    result = 0

    def send_push(priority):
        try:
            notification_message = message
            logger_me.debug("reached here")
            logger_me.debug(message)

            if type(device_obj) is GCMDevice:
                extra_arguments = {"transfer_id": transfer_obj.id, "time_out": time_out, "heading": message_headline,
                                   "display_message": message,
                                   "notification_type": notification_type, "is_instant": transfer_obj.instant_search}
            else:
                extra_arguments = {
                    "aps": {"sound": "default", "alert": notification_message, "heading": message_headline,
                            "transfer_id": transfer_obj.id,
                            "time_out": time_out, "display_message": message,
                            "notification_type": notification_type, "is_instant": transfer_obj.instant_search}}
            logger_me.debug("send push")
            status = device_obj.send_message(None, priority=priority,
                                             extra=extra_arguments)
            logger_me.debug(status)
            if status:
                rstatus = status['success']
                logger_me.debug("notification sent")
            else:
                rstatus = 1
                logger_me.debug("notification failed")

        except Exception as e:
            logger_me.debug(e)
            rstatus = 0

        return rstatus

    for device_obj in gcm_device_list:
        if device_obj.registration_id != '':
            result = send_push("high")

    for device_obj in apns_device_list:
        if device_obj.registration_id != '':
            result = send_push(10)

    # if result == 1 and should_save and notify_obj:
    if should_save and notify_obj:
        if time_out > 0:
            time_out /= 1000
            dismiss_time = timezone.now() + timezone.timedelta(seconds=time_out)
            NotificationHistory.objects.create(notification_id=notify_obj, user=user_obj, time_out=dismiss_time)
        else:
            NotificationHistory.objects.create(notification_id=notify_obj, user=user_obj)

    return result


def delete_notification(transfer_obj, not_type, user_type=''):
    notifications = Notifications.objects.filter(transfer_id=transfer_obj)
    if user_type and user_type == 'user':
        notifications = notifications.filter(receiver=transfer_obj.added_by)

    if not_type == 'trip_accepted':
        for not_obj in notifications:
            if not_obj.type == 'trip_request' or not_obj.type == 'trip_reminder':
                for not_history in NotificationHistory.objects.filter(notification_id=not_obj):
                    not_history.is_valid = False
                    not_history.read_status = True
                    not_history.save()
    elif not_type == 'trip_cancelled':
        for not_obj in notifications:
            if not_obj.type == 'trip_accepted' or not_obj.type == 'trip_request' or not_obj.type == 'trip_reminder':
                for not_history in NotificationHistory.objects.filter(notification_id=not_obj):
                    not_history.is_valid = False
                    not_history.save()
    elif not_type == 'start_loading':
        for not_obj in notifications:
            if not_obj.type == 'trip_accepted':
                for not_history in NotificationHistory.objects.filter(notification_id=not_obj):
                    not_history.is_valid = False
                    not_history.save()
    elif not_type == 'trip_started':
        for not_obj in notifications:
            if not_obj.type == 'start_loading':
                for not_history in NotificationHistory.objects.filter(notification_id=not_obj):
                    not_history.is_valid = False
                    not_history.save()
    elif not_type == 'trip_completed':
        for not_obj in notifications:
            if not_obj.type == 'trip_started':
                for not_history in NotificationHistory.objects.filter(notification_id=not_obj):
                    not_history.is_valid = False
                    not_history.save()
    elif not_type == 'refund_initiated':
        for not_obj in notifications:
            if not_obj.type == 'search_failed':
                for not_history in NotificationHistory.objects.filter(notification_id=not_obj):
                    not_history.is_valid = False
                    not_history.save()
    return True


def get_notification_count(user_id):
    count = NotificationHistory.objects.filter(user=user_id, read_status=False).count()
    return count


def create_promotion(notification_type, item_obj):
    not_obj = Notifications.objects.create(type=notification_type, offer_id=item_obj)
    return not_obj


def send_promotion_push_notification(item_obj, user_obj, message, message_headline='', should_save=False, time_out=0,
                           notify_obj=None):
    user = user_obj.user
    gcm_device_list = GCMDevice.objects.filter(user=user)
    apns_device_list = APNSDevice.objects.filter(user=user)
    notification_type = ''

    if notify_obj:
        notify_obj.message_headline = message_headline
        notify_obj.message = message
        notification_type = notify_obj.type
        notify_obj.receiver = user_obj
        notify_obj.save()
        print("Notify object updated")
    result = 0

    def send_push(priority):
        try:
            notification_message = message

            if type(device_obj) is GCMDevice:

                extra_arguments = {"item_id": item_obj.id, "time_out": time_out, "heading": message_headline,
                                   "display_message": message,
                                   "notification_type": notification_type}
            else:
                extra_arguments = {
                    "aps": {"sound": "default", "alert": notification_message, "heading": message_headline,
                            "item_id": item_obj.id,
                            "time_out": time_out, "display_message": message,
                            "notification_type": notification_type}}

            status = device_obj.send_message(None, priority=priority,
                                             extra=extra_arguments)
            if status:
                rstatus = status['success']
            else:
                rstatus = 1

        except APNSServerError as e:
            rstatus = 0

        return rstatus

    for device_obj in gcm_device_list:
        if device_obj.registration_id != '':
            result = send_push("high")

    for device_obj in apns_device_list:
        if device_obj.registration_id != '':
            try:
                result = send_push(10)
            except:
                pass

    # if result == 1 and should_save and notify_obj:
    if should_save and notify_obj:
        if time_out > 0:
            time_out /= 1000
            dismiss_time = timezone.now() + timezone.timedelta(seconds=time_out)
            NotificationHistory.objects.create(notification_id=notify_obj, user=user_obj, time_out=dismiss_time)
        else:
            NotificationHistory.objects.create(notification_id=notify_obj, user=user_obj)

    return result


