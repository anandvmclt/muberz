# -*- coding: utf-8 -*-
# Create your tasks here
from __future__ import absolute_import, unicode_literals

import logging
from threading import Thread

import pytz
from celery import Celery
from celery.task import PeriodicTask
from django.template.loader import get_template
from django.utils import timezone
from django_api_base.utils import send_template_email

from api_base.default import auto_cancelled_email_to_admin
from api_base.models import *
# from api_base.models import Transfer, Notifications, RefundManagement, BaseProfile, TruckRequest, VehicleDetails, \
#     TransferCommodity, TransferLocation
from api_base.search_driver import create_notification, send_push_notification, delete_notification
from dashboard.payout import calculate_driver_payout

logger_me = logging.getLogger('debug')

app = Celery('tasks', broker='pyamqp://guest@localhost//')


class NotificationMessages:
    class EN:
        reminder_heading = "Transfer Reminder"
        search_failed_heading = "Search Failed"
        driver_trip_timeout_heading = "Trip Timed-Out"
        user_trip_timeout_heading = "Driver Unavailable"

        reminder_message = "Your upcoming transfer is scheduled at "
        search_failed_message = "Sorry, we couldn't find any trucks for your transfer scheduled for {0} from {1} to {2}. Would you like " \
                                "to continue the search or cancel the transfer?"
        driver_trip_timeout_message = "Since you failed to follow through the trip scheduled on {0} that you accepted, it has been cancelled"
        user_trip_timeout_message = "The driver who accepted the trip scheduled on {0}, seems to be unavailable at the moment. We regret the inconvenience"
        lbl_transfer_cancelled = "The driver who accepted the trip scheduled on {0}, seems to be unavailable at the moment. We regret the inconvenience"
        lbl_refund_processing = "The amount you have paid will be refunded soon"
        lbl_driver_name = "Driver Name"
        lbl_reg_no = "Vehicle Registration No"
        lbl_volume = "Vehicle Volume"
        lbl_payable = "Payable Amount"
        lbl_payment_mode = "Payment Mode"
        lbl_fully_paid = "Fully Paid"
        lbl_scheduled_time = "Scheduled Time"
        lbl_pickup = "Pickup"
        lbl_drop = "Drop"
        lbl_sl_no = "Sl.No."
        lbl_name = "Name"
        lbl_plug_in = "Plug In"
        lbl_quantity = "Quantity"
        lbl_yes = "Yes"
        lbl_no = "No"
        lbl_thanks = "Thanks for choosing"
        lbl_commodities = "Commodities"
        lbl_transfer_confirmed = "Transfer Confirmed"
        lbl_trip_amount = "Trip Amount"
        lbl_auto_refund_trucks = "Auto refund requested for your transfer on {0}, as we couldn't find suitable trucks."

    class ES:
        reminder_heading = "Recordatorio de transferencia"
        search_failed_heading = "Error de búsqueda"
        driver_trip_timeout_heading = "Tiempo de viaje agotado"
        user_trip_timeout_heading = "Driver no disponible"

        reminder_message = "Su próxima transferencia está programada a las "
        search_failed_message = "Lo sentimos, no pudimos encontrar ningún equipo para su traslado programado para las {0} de {1} a {2}. Desea continuar la búsqueda o cancelar el servicio ?"
        driver_trip_timeout_message = "Como no cumplió el viaje programado para las {0}. que aceptó, se canceló"
        user_trip_timeout_message = "El conductor que aceptó el viaje programado para las {0}, parece no estar disponible en este momento. Lamentamos la inconveniencia"

        lbl_transfer_cancelled = "El conductor que aceptó el viaje programado para las {0}, parece no estar disponible en este momento. Lamentamos la inconveniencia"
        lbl_refund_processing = "El monto que ha pagado será reembolsado pronto"

        lbl_driver_name = "Nombre del conductor"
        lbl_reg_no = "Matrícula del vehículo"
        lbl_volume = "Volumen del vehículo"
        lbl_payable = "Cantidad a pagar"
        lbl_payment_mode = "Modo de pago"
        lbl_fully_paid = "Totalmente pagado"
        lbl_scheduled_time = "Hora programada"
        lbl_pickup = "Recoger"
        lbl_drop = "soltar",
        lbl_sl_no = "Si. No."
        lbl_name = "Nombre"
        lbl_plug_in = "Enchufar"
        lbl_quantity = "Cantidad"
        lbl_yes = "Sí"
        lbl_no = "No"
        lbl_thanks = "Gracias por elegir"
        lbl_commodities = "Productos básicos"
        lbl_transfer_confirmed = "Transferencia confirmada"
        lbl_trip_amount = "Monto del viaje"
        lbl_auto_refund_trucks = "Solicitud de reembolso automático para su transferencia en {0} ya que no pudimos encontrar un camión adecuado."


class CeleryRun(PeriodicTask):
    run_every = timezone.timedelta(seconds=10)

    def run(self, *args, **kwargs):
        logger_me.debug("celery in")
        '''
        1. Driver Push
            - Get all accepted transfers, where pickup time = current time + 1hr and if not send
            - Push reminder reminder_notifications
        2. User Push - Search Failed
        '''
        try:

            peru_timezone = pytz.timezone('America/Lima')
            reminder_time = timezone.now() + timezone.timedelta(hours=1)
            instant_search_fail_time = timezone.now() - timezone.timedelta(seconds=30)
            trip_time_out = timezone.now() - timezone.timedelta(hours=1)

            # TRIPS WHICH IS ACCEPTED AND NOT STARTED AFTER 1 HOUR OF TRIP TIME
            time_out_transfers = Transfer.objects.filter(status='accepted', transfer_on__lte=trip_time_out)

            transfers = Transfer.objects.filter(status='accepted', transfer_on__lte=reminder_time, instant_search=False,
                                                transfer_on__gte=timezone.now())

            instant_pending_transfers = Transfer.objects.filter(status='active', transfer_on__lte=instant_search_fail_time,
                                                                instant_search=True)
            scheduled_pending_transfers = Transfer.objects.filter(status='active', transfer_on__lte=reminder_time,
                                                                  instant_search=False,
                                                                  added_on__lte=instant_search_fail_time)

            pending_transfers = instant_pending_transfers | scheduled_pending_transfers
            # logger_me.debug("Pending trans")
            # logger_me.debug(pending_transfers)
            # logger_me.debug("Pending trans end")

            # Q(status='active'), Q(transfer_on__lte=reminder_time), Q(instant_search=False) |
            # Q(status='active'), Q(transfer_on__lte=instant_search_fail_time), Q(instant_search=True))

            reminder_notifications = Notifications.objects.filter(type="trip_reminder").values_list('transfer_id',
                                                                                                    flat=True)
            search_failed_notifications = Notifications.objects.filter(type="search_failed").values_list('transfer_id',
                                                                                                         flat=True)

            driver_languages = dict(transfers.values_list('driver_id', 'driver__language'))
            user_languages = dict(pending_transfers.values_list('added_by_id', 'added_by__language'))
            time_out_driver_languages = dict(time_out_transfers.values_list('driver_id', 'driver__language'))
            time_out_user_languages = dict(time_out_transfers.values_list('added_by_id', 'added_by__language'))

            for transfer in transfers:
                if transfer.id not in reminder_notifications:
                    transfer_time = transfer.transfer_on.astimezone(peru_timezone).strftime("%I:%M %p")
                    notify_obj = create_notification(transfer, "trip_reminder")

                    transfer_pickup = TransferLocation.objects.get(transfer_id=transfer, loc_type='pickup')
                    transfer_drop = TransferLocation.objects.get(transfer_id=transfer, loc_type='drop')

                    if transfer.instant_search:
                        message = "Sorry, we couldn't find any trucks for your transfer request on " + transfer_time + " from " + transfer_pickup.location_name + " to " + transfer_drop.location_name + ". Would you like " \
                                                                                                                                                                                                         "to continue the search or cancel the transfer?"
                    else:
                        message = NotificationMessages.__dict__[driver_languages[
                            transfer.driver_id]].reminder_message + transfer_time
                    status = send_push_notification(transfer, transfer.driver, message,
                                                    NotificationMessages.__dict__[
                                                        driver_languages[transfer.driver_id]].reminder_heading,
                                                    time_out=0, notify_obj=notify_obj, should_save=True)
                    if status == 1:
                        logger_me.debug("Reminded driver about upcoming transfer")

            for pending_transfer in pending_transfers:
                if pending_transfer.id not in search_failed_notifications:
                    pending_transfer.refresh_from_db()
                    if pending_transfer.status == 'active':
                        logger_me.debug("Search Failed !")
                        transfer_time = pending_transfer.transfer_on.astimezone(peru_timezone).strftime("%d-%m-%Y %I:%M %p")
                        transfer_pickup = TransferLocation.objects.get(transfer_id=pending_transfer, loc_type='pickup')
                        transfer_drop = TransferLocation.objects.get(transfer_id=pending_transfer, loc_type='drop')
                        pending_transfer.status = 'auto_cancelled'
                        pending_transfer.save()
                        TruckRequest.objects.filter(transfer_id=pending_transfer, status='sent').update(status='time_out')

                        notify_obj = create_notification(pending_transfer, "search_failed")
                        try:
                            notif = send_push_notification(pending_transfer, pending_transfer.added_by,
                                                       NotificationMessages.__dict__[
                                                           user_languages[
                                                               pending_transfer.added_by_id]].search_failed_message.format(
                                                           str(transfer_time), transfer_pickup.location_name,
                                                           transfer_drop.location_name), NotificationMessages.__dict__[
                                                           user_languages[
                                                               pending_transfer.added_by_id]].search_failed_heading,
                                                       time_out=0, notify_obj=notify_obj, should_save=True)
                            logger_me.debug("User notified about search failure")
                            logger_me.debug("--------Search Failed------")
                            logger_me.debug(notif)
                            logger_me.debug("--------Search Failed notif------")
                        except Exception as e:
                            logger_me.debug("-------Send Push Exception-----")
                            logger_me.debug(str(e))
                    else:
                        logger_me.debug("Pending status no active")
                else:
                    logger_me.debug("Transfer id in search failed")
            '''
            Initiate Refund if auto-cancelled after 2 minutes
            '''
            refund_timeout = timezone.now() - timezone.timedelta(minutes=1)

            auto_cancelled_transfers = list(Transfer.objects.filter(status='auto_cancelled', refund_initiated=False,
                                                                    transfer_on__lte=refund_timeout, payment_type='card'))
            for transfer in auto_cancelled_transfers:
                try:
                    peru_timezone = pytz.timezone('America/Lima')
                    RefundManagement.objects.create(added_by=transfer.added_by,
                                                    refund_cause='Auto cancelled as driver search failed',
                                                    date_added=timezone.now(), amount_to_refund=transfer.total_amount,
                                                    transfer=transfer, status='requested')
                    transfer.refund_initiated = True
                    transfer.save()
                    # DELETE NOTIFICATIONS OF SEARCH FAILED
                    delete_notification(transfer, 'refund_initiated', '')

                    notify_obj = create_notification(transfer, "refund_initiated")
                    transfer_time = transfer.transfer_on.astimezone(peru_timezone).strftime("%A, %B %d at %I:%M %p")

                    if transfer.transfer_timed_out:
                        user_message = "Refund initiated for your transfer on {0}, as driver failed to follow trip at the schedule time."
                    else:
                        user_message = NotificationMessages.__dict__[
                            user_languages[
                                transfer.added_by_id
                            ]
                        ].lbl_auto_refund_trucks.format(transfer_time)

                    status = send_push_notification(transfer, transfer.added_by, user_message, "Refund Requested",
                                                    time_out=0,
                                                    notify_obj=notify_obj, should_save=True)

                    if status == 1:
                        logger_me.debug("User notified about refund request")
                    else:
                        notify_obj.delete()
                        logger_me.debug("APNS failed!")
                except:
                    logger_me.debug("Couldn't create an refund management object")

            """
            Sent Email to admin for auto cancelled transfer
            """

            all_auto_cancelled_transfers = list(Transfer.objects.filter(status='auto_cancelled', cancel_notify_admin=False, transfer_on__lte=refund_timeout))
            for transfer in all_auto_cancelled_transfers:
                try:
                    auto_cancelled_email_to_admin(transfer)
                    transfer.cancel_notify_admin = True
                    transfer.save()
                except:
                    pass

            '''
            added_by = models.ForeignKey(BaseProfile, null=True)
            refund_cause = models.TextField()
            date_added = models.DateTimeField(auto_now=True)
            amount_to_refund = models.FloatField(null=False, blank=False, default=0)
            transfer = models.ForeignKey(Transfer)
            status
            '''
            # CANCEL TIMEOUT TRANSFERS

            for transfer in time_out_transfers:
                logger_me.debug("Trip Time exceeded !")
                transfer_time = transfer.transfer_on.astimezone(peru_timezone).strftime("%I:%M %p")

                # PUSH TO USER
                delete_notification(transfer, 'trip_cancelled', 'user')
                notify_obj = create_notification(transfer, "trip_cancelled")
                status = send_push_notification(transfer, transfer.added_by,
                                                NotificationMessages.__dict__[
                                                    time_out_user_languages[
                                                        transfer.added_by_id]].user_trip_timeout_message.format(
                                                    transfer_time), NotificationMessages.__dict__[
                                                    time_out_user_languages[
                                                        transfer.added_by_id]].user_trip_timeout_heading,
                                                time_out=0, notify_obj=notify_obj, should_save=True)

                # MAIL NOTIFICATION TO USER APP
                driver_vehicle = VehicleDetails.objects.filter(driver_id=transfer.driver).latest('id')
                transfer_commodities = TransferCommodity.objects.filter(
                    transfer_loc_id__transfer_id=transfer, transfer_loc_id__loc_type="pickup").values(
                    'item__item_name', 'need_plugged').distinct().annotate(models.Count('item'))
                transfer_locations = TransferLocation.objects.filter(
                    transfer_id=transfer).values('loc_type', 'location_name')
                context = {
                    "transfer": transfer,
                    "driver": transfer.driver,
                    "lbl_transfer_cancelled": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_transfer_cancelled.format(
                        transfer_time),
                    "user_trip_timeout_heading": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].user_trip_timeout_heading,
                    "lbl_refund_processing": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_refund_processing,
                    "commodities": transfer_commodities,
                    "lbl_driver_name": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_driver_name,
                    "lbl_payment_mode": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_payment_mode,
                    "lbl_pickup": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_pickup,
                    "lbl_drop": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_drop,
                    "lbl_sl_no": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_sl_no,
                    "lbl_name": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_name,
                    "lbl_plug_in": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_plug_in,
                    "lbl_quantity": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_quantity,
                    "lbl_yes": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_yes,
                    "lbl_no": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_no,
                    "lbl_thanks": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_thanks,
                    "lbl_commodities": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_commodities,
                    "lbl_trip_amount": NotificationMessages.__dict__[
                        time_out_user_languages[
                            transfer.added_by_id]].lbl_trip_amount,
                }

                for location in transfer_locations:
                    context[location['loc_type']] = location['location_name'] or ""
                if not transfer.instant_search:
                    target_timezone = pytz.timezone('America/Lima')
                    scheduled_time = transfer.transfer_on.astimezone(target_timezone)
                    context["scheduled_time"] = scheduled_time
                message = get_template('dashboard/email-templates/transfer-cancel-mail.html').render(context)
                # Starting a new thread for sending confirmation mail
                email_thread = Thread(
                    target=send_template_email,
                    args=(NotificationMessages.__dict__[
                              time_out_user_languages[
                                  transfer.added_by_id]].user_trip_timeout_heading,
                          message, [transfer.added_by.user.email]))
                email_thread.start()  # Starts thread
                # MAIL NOTIFICATION TO USER APP

                # PUSH TO DRIVER
                notify_obj = create_notification(transfer, "trip_cancelled")
                status1 = send_push_notification(transfer, transfer.driver,
                                                 NotificationMessages.__dict__[
                                                     time_out_driver_languages[
                                                         transfer.driver_id]].driver_trip_timeout_message.format(
                                                     transfer_time), NotificationMessages.__dict__[
                                                     time_out_driver_languages[
                                                         transfer.driver_id]].driver_trip_timeout_heading,
                                                 time_out=0, notify_obj=notify_obj, should_save=True)

                transfer.status = 'auto_cancelled'
                transfer.transfer_timed_out = True
                transfer.cancel_comments = "Driver failed to follow trip at the schedule time. "
                transfer.save()
        except Exception as e:
            logger_me.debug(str(e))

        return "Task completed"


class AutoPayoutCalculation(PeriodicTask):
    run_every = None

    def run(self, *args, **kwargs):
        logger_me.debug("AutoPayoutCalculation Initiated")
        drivers = list(BaseProfile.objects.filter(user_type='driver').order_by('id'))
        logger_me.debug(len(drivers))
        for driver in drivers:
            try:
                logger_me.debug('---------driver-------')
                logger_me.debug(driver.id)
                calculate_driver_payout(driver, payout_date=timezone.now())
                logger_me.debug('---------payout completed-------')
            except:
                logger_me.debug('---------payout failed-------')
                pass

