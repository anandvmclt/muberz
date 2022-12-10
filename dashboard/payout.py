from datetime import datetime, timedelta, date

import pytz
from django.utils import timezone

from api_base.default import logger_me
from api_base.models import DriveStatusHistory, PayoutHistory, Transfer, DriverOffer


# To calculate payout amount for each driver:
def calculate_driver_payout(driver_obj, payout_date=timezone.now(), shouldSave=True):
    logger_me.debug('calculation started')
    # payout_date = payout_date + timedelta(1)
    payout_date = payout_date_peru = payout_date.astimezone(pytz.timezone('America/Lima'))
    # PERU TIME - 1
    actual_payout_peru_date = payout_date_peru - timedelta(1)
    actual_payout_peru_date = actual_payout_peru_date.replace(hour=23, minute=59, second=59)
    actual_payout_utc = actual_payout_peru_date.astimezone(pytz.utc)

    previous_payouts = PayoutHistory.objects.filter(driver=driver_obj, payment_processed=True).order_by('-id')
    drivers_commission_percentage = driver_obj.commission
    start_date = None
    return_obj = None
    cash_incentives = 0
    earnings_from_discount = 0
    total_bookings_amount = 0
    transfer_cash_in_hand = 0
    net_debitable_cash = 0
    net_cash_earned_booking = 0
    net_muberz_commission = 0
    net_payable_for_driver = 0
    if previous_payouts:
        start_date = previous_payouts[0].date
    else:
        start_dates = Transfer.objects.filter(driver=driver_obj, status='completed').order_by('completed_on').values(
            'transfer_on')
        temp = Transfer.objects.filter(driver=driver_obj, status='completed').order_by('completed_on')
        if start_dates:
            start_date = start_dates[0]['transfer_on'].date()

    if start_date:
        raw_bookings = Transfer.objects.filter(status='completed', driver=driver_obj, completed_on__date__gte=start_date,
                                               completed_on__lte=actual_payout_utc).values('id',
                                                                                                      'completed_on',
                                                                                                      'total_amount',
                                                                                                      'payment_type')
        all_bookings = Transfer.objects.filter(status='completed', driver=driver_obj,
                                               completed_on__date__gte=start_date,
                                               completed_on__lte=actual_payout_utc)

        total_bookings = []

        for booking in raw_bookings:
            completed_on = booking['completed_on'].astimezone(pytz.timezone('America/Lima'))
            new_booking = {'booking_id': booking['id'],
                           'completed_on': datetime.strftime(completed_on, "%d/%m/%y"),
                           'total_amount': booking['total_amount'],
                           'cash_payment': True if booking['payment_type'] == 'cash' else False,
                           'muberz_commission': drivers_commission_percentage
                           }
            total_bookings.append(new_booking)
        cash_incentives = 0
        if total_bookings:
            incentives = calculate_driver_incentive(driver_obj, previous_payouts, actual_payout_peru_date + timedelta(1), actual_payout_utc) #payout_date)
            logger_me.debug('incentives')
            logger_me.debug(incentives)

            cash_incentives = incentives['cash_earned']
            earnings_from_discount = 0
            total_bookings_amount = 0
            transfer_cash_in_hand = 0
            net_debitable_cash = 0
            net_cash_earned_booking = 0
            net_muberz_commission = 0
            net_payable_for_driver = 0
            commission_percentage = 0
            logger_me.debug('total_bookings')
            logger_me.debug(total_bookings)
            for booking in total_bookings:
                commission_percentage = booking['muberz_commission']
                discounted_commissions = 0

                if incentives['time_daily_commission_discount']:
                    discounted_commission = 0
                    for time_daily in incentives['time_daily_commission_discount']:
                        logger_me.debug(time_daily['date'])

                        # daily_date = datetime.strptime(time_daily['date'], "%d/%m/%y").replace(hour=23, minute=59, second=59)
                        # daily_date = pytz.timezone('America/Lima').localize(daily_date)
                        # daily_date = daily_date.astimezone(pytz.utc)
                        logger_me.debug('daily_date')
                        logger_me.debug(time_daily['date'])
                        logger_me.debug(datetime.strptime(booking['completed_on'], "%d/%m/%y"))
                        if datetime.strptime(booking['completed_on'], "%d/%m/%y") == datetime.strptime(
                                time_daily['date'], "%d/%m/%y"):
                            logger_me.debug('time_dailycommission+')
                            logger_me.debug(time_daily['commission'])
                            discounted_commission += time_daily['commission']
                    discounted_commissions += discounted_commission
                logger_me.debug('discounted_commissions')
                logger_me.debug(discounted_commissions)
                if incentives['time_weekly_commission_discount']:
                    discounted_commission = 0
                    for time_weekly in incentives['time_weekly_commission_discount']:
                        if datetime.strptime(booking['completed_on'], "%d/%m/%y") >= datetime.strptime(
                                time_weekly['week_from'], "%d/%m/%y") and datetime.strptime(booking['completed_on'],
                                                                                            "%d/%m/%y") <= datetime.strptime(
                            time_weekly['week_to'], "%d/%m/%y"):
                            discounted_commission += time_weekly['commission']
                    discounted_commissions += discounted_commission

                if incentives['trip_daily_commission_discount']:
                    discounted_commission = 0
                    for trip_daily in incentives['trip_daily_commission_discount']:
                        if datetime.strptime(booking['completed_on'], "%d/%m/%y") == datetime.strptime(
                                trip_daily['date'], "%d/%m/%y"):
                            discounted_commission += trip_daily['commission']
                    discounted_commissions += discounted_commission

                if incentives['trip_weekly_commission_discount']:
                    discounted_commission = 0
                    for trip_weekly in incentives['trip_weekly_commission_discount']:
                        if datetime.strptime(booking['completed_on'], "%d/%m/%y") >= datetime.strptime(
                                trip_weekly['week_from'], "%d/%m/%y") and datetime.strptime(booking['completed_on'],
                                                                                            "%d/%m/%y") <= datetime.strptime(
                            trip_weekly['week_to'], "%d/%m/%y"):
                            discounted_commission += trip_weekly['commission']
                    discounted_commissions += discounted_commission

                if discounted_commissions > 100:
                    discounted_commissions = 100

                logger_me.debug('+++book id =====')
                logger_me.debug(booking['booking_id'])
                logger_me.debug('discounted_commissions')
                logger_me.debug(discounted_commissions)

                earnings_from_discount += (booking['total_amount'] * (
                        commission_percentage * discounted_commissions / 100) / 100)
                commission_percentage = (commission_percentage - (commission_percentage * discounted_commissions / 100))
                commission_amount = (booking['total_amount'] * commission_percentage / 100)

                net_muberz_commission += commission_amount

                logger_me.debug('commission_percentage')
                logger_me.debug(commission_percentage)
                logger_me.debug('earnings_from_discount')
                logger_me.debug(earnings_from_discount)
                logger_me.debug('net_muberz_commission')
                logger_me.debug(net_muberz_commission)
                logger_me.debug('commission_amount')
                logger_me.debug(commission_amount)


                cash_with_driver = 0
                if booking['cash_payment']:
                    cash_with_driver = booking['total_amount']

                transfer_cash_in_hand += cash_with_driver
                net_cash_earned_booking += (booking['total_amount'] - commission_amount)
                net_debitable_cash += (booking['total_amount'] - commission_amount - cash_with_driver)
                total_bookings_amount += booking['total_amount']

                # logger_me.debug('total_amount****' + str(booking['total_amount']))
                # logger_me.debug('total_bookings_amount****' + str(total_bookings_amount))
                # logger_me.debug('commission_amount****' + str(commission_amount))
                # logger_me.debug('net_cash_earned****' + str(net_cash_earned_booking))
                logger_me.debug('net_debitable_cash****' + str(net_debitable_cash))

            incentive_to_deposit = 0
            if cash_incentives > total_bookings_amount:
                incentive_to_deposit = cash_incentives - total_bookings_amount
                cash_incentives = cash_incentives - incentive_to_deposit

            net_payable_for_driver = net_debitable_cash + cash_incentives
            amount_to_be_collected = 0
            if net_payable_for_driver < 0:
                amount_to_be_collected = abs(net_payable_for_driver)
                net_payable_for_driver = 0

            logger_me.debug('net_payable_for_driver')
            logger_me.debug(net_payable_for_driver)
            logger_me.debug('amount_to_be_collected')
            logger_me.debug(amount_to_be_collected)

            if shouldSave:
                # creating a new payout history entry for this driver in database:

                PayoutHistory.objects.filter(driver=driver_obj, payment_processed=False).update(deleted=True)
                return_obj = PayoutHistory.objects.create(driver=driver_obj,
                                                          total_bookings_amount=total_bookings_amount,
                                                          commission_amount_to_muberz=net_muberz_commission,
                                                          drivers_earnings_from_transfers=net_cash_earned_booking,
                                                          transfer_cash_in_drivers_hand=transfer_cash_in_hand,
                                                          drivers_earnings_from_discounts=earnings_from_discount,
                                                          cash_incentives_earned_by_driver=cash_incentives,
                                                          net_payable_for_driver=net_payable_for_driver,
                                                          amount_to_be_collected_from_driver=amount_to_be_collected,
                                                          payment_processed=False, date=timezone.now())
                return_obj.transfers.add(*all_bookings)
                return_obj.save()
                logger_me.debug(net_payable_for_driver)
                return_obj.net_payable_for_driver = net_payable_for_driver
                return_obj.save()
                if driver_obj.fleet_id:
                    driver_obj.fleet_id.payment_processed = False
                    driver_obj.fleet_id.save(update_fields=['payment_processed'])
            else:
                considered_bookings = []
                for each in raw_bookings:
                    considered_bookings.append(each["id"])

                return_obj = {
                    'total_bookings_amount': round(total_bookings_amount, 2),
                    'commission_amount_to_muberz': round(net_muberz_commission, 2),
                    'income_from_transfers': round(net_cash_earned_booking, 2),
                    'transfer_cash_in_hand': round(transfer_cash_in_hand, 2),
                    'net_debitable_cash': round(net_debitable_cash, 2),
                    'cash_incentives_earned': round(cash_incentives, 2),
                    'net_payable': round(net_payable_for_driver, 2),
                    'net_payable_for_driver': round(net_payable_for_driver, 2),
                    'amount_to_be_collected': round(amount_to_be_collected, 2),
                    'considered_bookings': considered_bookings
                }
                if incentive_to_deposit > 0:
                    return_obj['security_deposit'] = round(driver_obj.vehicledetails.security_deposit, 2)
                    return_obj['incentive_to_deposit'] = round(incentive_to_deposit, 2)

            logger_me.debug("Driver Payout Calculated")
    return return_obj


# To calculate incentives based on time driver was online & trips taken

def calculate_driver_incentive(driver_obj, previous_payouts, payout_date, actual_payout_utc):
    driver_online_array = calculate_driver_duration(driver_obj, previous_payouts, payout_date, actual_payout_utc)
    logger_me.debug('driver_online_array----')
    logger_me.debug(driver_online_array)
    trip_details_array = calculate_driver_trips(driver_obj, previous_payouts, payout_date, actual_payout_utc)
    cash_earned = 0
    time_daily_commission_discount = []
    time_weekly_commission_discount = []
    trip_daily_commission_discount = []
    trip_weekly_commission_discount = []
    cash_earned = 0
    start_date = ''
    if previous_payouts:
        start_date = previous_payouts[0].date
    else:
        if driver_online_array:
            start_date = datetime.strptime(driver_online_array[0]['date'], "%d/%m/%y").date()
    if driver_obj.fleet_id:
        offer_applied_to = 'fleet'
    else:
        offer_applied_to = 'user'
    if start_date != '':
        offers = DriverOffer.objects.filter(offer_valid_to__gte=start_date, added_by__city=driver_obj.city, offer_applied_to=offer_applied_to)

        logger_me.debug('offers')
        logger_me.debug(offers)
        for offer in offers:
            if offer.offer_based_on == 'time':
                if offer.offer_base == 'daily':
                    logger_me.debug('in offer daily time' + str(offer.id))
                    for each_day in driver_online_array:
                        if datetime.strptime(each_day['date'],
                                             "%d/%m/%y").date() >= offer.offer_valid_from and datetime.strptime(
                            each_day['date'], "%d/%m/%y").date() <= offer.offer_valid_to:
                            if each_day['seconds'] / 3600 > offer.total_duration:
                                if offer.offer_type == 'cash':
                                    if offer.offer_applied_to == 'user':
                                        cash_earned += offer.offer_commission_cash
                                    elif driver_obj.fleet_id:
                                        cash_earned += offer.offer_commission_cash
                                    logger_me.debug('cash_earned')
                                    logger_me.debug(cash_earned)
                                else:
                                    dic = {}
                                    if offer.offer_applied_to == 'user':
                                        dic = {'date': each_day['date'], 'commission': offer.offer_commission_percent}
                                    elif driver_obj.fleet_id:
                                        dic = {'date': each_day['date'],
                                               'commission': offer.offer_commission_percent}
                                    if dic:
                                        time_daily_commission_discount.append(dic)
                                        logger_me.debug('daily-time-commision')
                                        logger_me.debug(dic)
                    logger_me.debug('time_daily_commission_discount')
                    logger_me.debug(time_daily_commission_discount)
                else:
                    logger_me.debug('in offer weekly time' + str(offer.id))
                    weekly_online = []
                    for driver_online_initial_day in driver_online_array:
                        if datetime.strptime(driver_online_initial_day['date'],
                                             "%d/%m/%y").date() >= offer.offer_valid_from:
                            if datetime.strptime(driver_online_initial_day['date'], "%d/%m/%y").strftime(
                                    "%A").lower() != 'sunday':
                                weekly_online.append(
                                    {'week_from': driver_online_initial_day['date'], 'week_to': '', 'commission': 0})
                                break
                    for each_day_ordinal in range(start_date.toordinal(), (payout_date - timedelta(1)).toordinal()):
                        each_day = date.fromordinal(each_day_ordinal)
                        if each_day.strftime("%A").lower() == 'sunday':
                            if each_day != start_date:
                                if weekly_online:
                                    weekly_online[-1]['week_to'] = (each_day - timedelta(1)).strftime('%d/%m/%y')
                            weekly_online.append(
                                {'week_from': each_day.strftime('%d/%m/%y'), 'week_to': '', 'commission': 0})
                    if weekly_online:
                        weekly_online[-1]['week_to'] = (payout_date - timedelta(1)).strftime('%d/%m/%y')
                    logger_me.debug('==+++=====weekly_online=+++===========')
                    logger_me.debug(weekly_online)
                    logger_me.debug('=======weekly_online============')

                    for each_week in weekly_online:
                        total_time = 0
                        for each_day in driver_online_array:
                            if each_week['week_from'] and each_week['week_to']:
                                if datetime.strptime(each_day['date'], '%d/%m/%y') >= datetime.strptime(
                                        each_week['week_from'], '%d/%m/%y') and datetime.strptime(
                                    each_day['date'], '%d/%m/%y') <= datetime.strptime(each_week['week_to'], '%d/%m/%y'):
                                    total_time += each_day['seconds'] / 3600
                        if total_time > offer.total_duration:
                            if offer.offer_type == 'cash':
                                if offer.offer_applied_to == 'user':
                                    cash_earned += offer.offer_commission_cash
                                elif driver_obj.fleet_id:
                                    cash_earned += offer.offer_commission_cash
                            else:
                                if offer.offer_applied_to == 'user':
                                    each_week['commission'] += offer.offer_commission_percent
                                elif driver_obj.fleet_id:
                                    each_week['commission'] += offer.offer_commission_percent
                    for each in weekly_online:
                        if each['commission'] != 0:
                            time_weekly_commission_discount.append(each)
                logger_me.debug('====cash_earned')
                logger_me.debug(cash_earned)
            else:
                if previous_payouts:
                    start_date = previous_payouts[0].date
                else:
                    start_dates = Transfer.objects.filter(driver=driver_obj, status='completed').order_by('id').values(
                        'transfer_on')
                    if start_dates:
                        start_date = start_dates[0]['transfer_on'].date()
                if offer.offer_base == 'daily':
                    logger_me.debug('in offer daily trip' + str(offer.id))
                    logger_me.debug('trip_details_array')
                    logger_me.debug(trip_details_array)
                    for each_day in trip_details_array:
                        if datetime.strptime(each_day['date'],
                                             "%d/%m/%y").date() >= offer.offer_valid_from and datetime.strptime(
                            each_day['date'], "%d/%m/%y").date() <= offer.offer_valid_to:
                            if each_day['trips'] > offer.total_trip_count:
                                if offer.offer_type == 'cash':
                                    if offer.offer_applied_to == 'user':
                                        cash_earned += offer.offer_commission_cash
                                    elif driver_obj.fleet_id:
                                        cash_earned += offer.offer_commission_cash
                                else:
                                    dic = {}
                                    if offer.offer_applied_to == 'user':
                                        dic = {'date': each_day['date'], 'commission': offer.offer_commission_percent}
                                    elif driver_obj.fleet_id:
                                        dic = {'date': each_day['date'], 'commission': offer.offer_commission_percent}
                                    if dic:
                                        trip_daily_commission_discount.append(dic)
                else:
                    logger_me.debug('in offer weekly trip' + str(offer.id))
                    weekly_online = []
                    for trip_initial_day in trip_details_array:
                        if datetime.strptime(trip_initial_day['date'], "%d/%m/%y").date() >= offer.offer_valid_from:
                            if datetime.strptime(trip_initial_day['date'], "%d/%m/%y").strftime(
                                    "%A").lower() != 'sunday':
                                weekly_online.append(
                                    {'week_from': trip_initial_day['date'], 'week_to': '', 'commission': 0})
                                break
                    logger_me.debug('---weekly_online')
                    logger_me.debug(weekly_online)
                    for each_day_ordinal in range(start_date.toordinal(), (payout_date - timedelta(1)).toordinal()):
                        each_day = date.fromordinal(each_day_ordinal)
                        if each_day.strftime("%A").lower() == 'sunday':
                            if each_day != start_date and weekly_online:
                                weekly_online[-1]['week_to'] = (each_day - timedelta(1)).strftime('%d/%m/%y')
                            weekly_online.append(
                                {'week_from': each_day.strftime('%d/%m/%y'), 'week_to': '', 'commission': 0})
                    if weekly_online:
                        weekly_online[-1]['week_to'] = (payout_date - timedelta(1)).strftime('%d/%m/%y')
                        logger_me.debug('weekly_online---')
                        logger_me.debug(weekly_online)
                    logger_me.debug('=======weekly_online============')
                    logger_me.debug(weekly_online)
                    logger_me.debug('=======weekly_online============')
                    for each_week in weekly_online:
                        total_trips = 0
                        for each_day in trip_details_array:
                            if datetime.strptime(each_day['date'], '%d/%m/%y') >= datetime.strptime(
                                    each_week['week_from'], '%d/%m/%y') and datetime.strptime(each_day['date'],
                                                                                              '%d/%m/%y') <= datetime.strptime(
                                each_week['week_to'], '%d/%m/%y'):
                                total_trips += each_day['trips']
                        if total_trips > offer.total_trip_count:
                            if offer.offer_type == 'cash':
                                if offer.offer_applied_to == 'user':
                                    cash_earned += offer.offer_commission_cash
                                elif driver_obj.fleet_id:
                                    cash_earned += offer.offer_commission_cash
                            else:
                                if offer.offer_applied_to == 'user':
                                    each_week['commission'] += offer.offer_commission_percent
                                elif driver_obj.fleet_id:
                                    each_week['commission'] += offer.offer_commission_percent
                            logger_me.debug('cash_earned')
                            logger_me.debug(cash_earned)
                    for each in weekly_online:
                        if each['commission'] != 0:
                            trip_weekly_commission_discount.append(each)
    logger_me.debug('trip_weekly_commission_discount=======')
    logger_me.debug(trip_weekly_commission_discount)
    logger_me.debug('trip_weekly_commission_discount=======')
    logger_me.debug(cash_earned)
    data = {
        'cash_earned': cash_earned,
        'time_daily_commission_discount': time_daily_commission_discount,
        'time_weekly_commission_discount': time_weekly_commission_discount,
        'trip_daily_commission_discount': trip_daily_commission_discount,
        'trip_weekly_commission_discount': trip_weekly_commission_discount
    }
    return data


def calculate_driver_trips(driver_obj, previous_payouts, payout_date, actual_payout_utc):
    peru_timezone = pytz.timezone('America/Lima')
    start_date = ''

    if previous_payouts:
        start_date = previous_payouts[0].date
    else:
        start_dates = Transfer.objects.filter(driver=driver_obj, status='completed').order_by('id').values(
            'transfer_on')
        if start_dates:
            start_date = start_dates[0]['transfer_on']
    if start_date != '':
        # start_date = start_date.astimezone(peru_timezone)
        trip_details = Transfer.objects.filter(driver=driver_obj, completed_on__date__gte=start_date.date(), status='completed',
                                               completed_on__lte=actual_payout_utc).values('completed_on')
        temp_trips = []
        loop_date = start_date.astimezone(peru_timezone)
        while loop_date.date() < payout_date.date():
            temp_trips.append({'date': loop_date.strftime("%d/%m/%y"), 'trips': 0})
            loop_date = loop_date + timedelta(days=1)
        for each_trip in trip_details:
            for each_temp in temp_trips:
                if each_trip['completed_on'].astimezone(peru_timezone).strftime("%d/%m/%y") == each_temp['date']:
                    each_temp['trips'] += 1
        trips = []
        for each_trip in temp_trips:
            if each_trip['trips'] != 0:
                trips.append(each_trip)
        return trips


# # Function for calculating time duration of drivers, during payout
def calculate_driver_duration(driver_obj, previous_payouts, payout_date, actual_payout_utc):
    peru_timezone = pytz.timezone('America/Lima')
    start_date = ''
    if previous_payouts:
        start_date = previous_payouts[0].date
    else:
        start_dates = DriveStatusHistory.objects.filter(driver=driver_obj).order_by('status_from')
        if start_dates:
            start_date = start_dates[0].status_from
    if start_date != '':
        # start_date = start_date.astimezone(peru_timezone)
        # Get all start times in the payout time period
        logger_me.debug('calculate_driver_duration----')
        logger_me.debug(start_date)
        raw_start_times = DriveStatusHistory.objects.filter(status_from__date__gte=start_date.date()).order_by('status_from').values(
            'status_from')
        start_times = []
        for date in raw_start_times:
            date_dictionary = {
                'date': date['status_from'].astimezone(peru_timezone).strftime("%d/%m/%y"),
                'time': date['status_from'].astimezone(peru_timezone).strftime("%X")
            }
            start_times.append(date_dictionary)

        # Get all stop/end times in the payout time period
        raw_stop_times = DriveStatusHistory.objects.filter(status_from__date__gte=start_date.date()).order_by('status_to').values(
            'status_to')
        stop_times = []
        for date in raw_stop_times:
            if not date['status_to']:
                date_dictionary = {
                    'date': timezone.now().astimezone(peru_timezone).strftime("%d/%m/%y"),
                    'time': timezone.now().astimezone(peru_timezone).strftime("%X")
                }
            else:
                date_dictionary = {
                    'date': date['status_to'].astimezone(peru_timezone).strftime("%d/%m/%y"),
                    'time': date['status_to'].astimezone(peru_timezone).strftime("%X")
                }
            stop_times.append(date_dictionary)

        durations = []
        loop_date = start_date.astimezone(peru_timezone)
        while loop_date.date() < payout_date.date():
            durations.append({'date': loop_date.strftime("%d/%m/%y"), 'seconds': 0})
            loop_date = loop_date + timedelta(days=1)

        while len(start_times) > 0 or len(stop_times) > 0:
            if len(start_times) > 0:
                if start_times[-1]['date'] == stop_times[-1]['date']:
                    if start_times[-1]['time'] <= stop_times[-1]['time']:
                        time_duration = (datetime.strptime(stop_times[-1]['time'], '%H:%M:%S') - datetime.strptime(
                            start_times[-1]['time'], '%H:%M:%S')).total_seconds()
                        for duration in durations:
                            if duration['date'] == start_times[-1]['date']:
                                duration['seconds'] += time_duration
                                break
                        start_times.pop()
                        stop_times.pop()
                    else:
                        time_duration = (datetime.strptime('23:59:59', '%H:%M:%S') - datetime.strptime(
                            start_times[-1]['time'], '%H:%M:%S')).total_seconds()
                        for duration in durations:
                            if duration['date'] == start_times[-1]['date']:
                                duration['seconds'] += time_duration
                                break
                        start_times.pop()
                else:
                    if start_times[-1]['date'] == (payout_date - timedelta(1)).date().strftime("%d/%m/%y"):
                        time_duration = (datetime.strptime('23:59:59', '%H:%M:%S') - datetime.strptime(
                            start_times[-1]['time'], '%H:%M:%S')).total_seconds()
                        for duration in durations:
                            if duration['date'] == start_times[-1]['date']:
                                duration['seconds'] += time_duration
                                break
                        start_times.pop()
                    else:
                        time_duration = (datetime.strptime('23:59:59', '%H:%M:%S') - datetime.strptime(
                            start_times[-1]['time'], '%H:%M:%S')).total_seconds()
                        for duration in durations:
                            if duration['date'] == start_times[-1]['date']:
                                duration['seconds'] += time_duration
                                break
                        start_times[-1]['date'] = (
                                datetime.strptime(start_times[-1]['date'], '%d/%m/%y') + timedelta(1)).date().strftime(
                            "%d/%m/%y")
                        start_times[-1]['time'] = '00:00:00'
            else:
                break

        final_durations = []
        for duration in durations:
            if duration['seconds'] != 0:
                final_durations.append(duration)
        return final_durations
