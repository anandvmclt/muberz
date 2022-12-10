# -*- coding: utf-8 -*-
# Create your views here.
from __future__ import unicode_literals
from datetime import timedelta
from sqlite3 import IntegrityError
from threading import Thread

import pytz
from django.contrib import messages
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.db.models import Prefetch
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django_api_base.api_base import ApiView, StatusCode, JsonWrapper
from django_api_base.utils import random_number_generator

import csv
from api_base.default import *
from api_base.models import *
from api_base.search_driver import create_promotion
from api_base.search_driver import send_promotion_push_notification
from api_base.views import get_security_deposit, get_no_assistant, get_rating
from dashboard.payout import calculate_driver_payout
from django.db import connection
from api_base.search_driver import send_push_notification

logger_me = logging.getLogger('debug')
dashboard_login = '/dashboard/login'



def set_session(request):
    language = request.GET.get('language', '')
    dic = {}
    if language == '1':
        lang = 'en'
    else:
        lang = 'span'

    request.session['language'] = lang
    dic["language"] = request.session['language']
    result_data = request.session['language']
    return JsonResponse(result_data, safe=False)


class LoginView(TemplateView):
    """
    Login view for admin's to login to dashboard
    """
    template_name = 'dashboard/page-login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            if request.user.is_staff:
                return redirect(reverse('dashboard:dashboard-home-page'))
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def post(request):
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if username and password != '':
            try:
                # user = authenticate(username=username, password=password)  # Authenticating user
                user = User.objects.get(username=username)
                logger_me.debug(user)
                logger_me.debug(user.id)
                if user.check_password(password):
                    logger_me.debug("checking password")
                    if user is not None:

                        if user.is_active:
                            if user.is_staff and user.is_superuser:
                                login(request, user)  # Logging in user and setting session
                                messages.success(request, request.lbl_welcome + " %s" % user.email)
                                if request.user.is_superuser:
                                    admin_profile, status = BaseProfile.objects.get_or_create(user=user,
                                                                                              user_type='super_user')
                                    request.session['user_type'] = admin_profile.get_user_type_display()
                            elif user.is_staff:
                                try:
                                    admin_profile = BaseProfile.objects.get(user=user)
                                    if admin_profile.user_type == 'admin_user' or admin_profile.user_type == 'fleet_admin' or admin_profile.user_type == 'operator':
                                        request.session['user_name'] = admin_profile.user.get_full_name()
                                        request.session['user_type'] = admin_profile.get_user_type_display()
                                        login(request, user)  # Logging in user and setting session
                                        # logger_me = logging.getLogger('debug')
                                        # logger_me.debug(request.session['company'])
                                        request.session[
                                            'company'] = admin_profile.user.first_name + ' ' + admin_profile.user.last_name
                                        try:
                                            request.session['city'] = admin_profile.city.city_name
                                        except:
                                            pass
                                        request.session['image'] = admin_profile.profile_pic
                                        request.session.modified = True
                                        messages.success(request, request.lbl_welcome + " %s" % user.email)
                                    else:
                                        messages.error(request, request.lbl_login_no_permission)
                                except:
                                    pass

                            else:  # User don't have permission. User is not superuser
                                messages.error(request, request.lbl_login_no_permission)
                        else:  # User account is not active
                            messages.error(request, request.lbl_accnt_not_active)
                    else:  # User with provided username/password does not exist
                        messages.error(request, request.lbl_invalid_username_password)
                else:  # User with provided username/password does not exist
                    messages.error(request, request.lbl_invalid_username_password)
            except User.DoesNotExist:
                messages.error(request, request.lbl_invalid_username_password)
        else:  # Provided username is not valid
            messages.error(request, request.lbl_provide_valid_username_password)

        return redirect(reverse('dashboard:dashboard-login'))


class SignupView(TemplateView):
    """
    View for rendering and handling Signup Fleet
    """
    template_name = 'dashboard/signup-fleet.html'

    def get_context_data(self, **kwargs):
        context = super(SignupView, self).get_context_data(**kwargs)
        cities = City.objects.all()
        context['city'] = cities
        return context

    @staticmethod
    def post(request):
        company_name = request.POST.get('company_name', '')
        address = request.POST.get('address', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        city = request.POST.get('city', '')
        ceo_id_proof = request.POST.get('image1', '')
        if email is not None:
            if not User.objects.filter(username=email):
                try:
                    user = User.objects.create_user(
                        username=email, email=email, password=password, is_staff=True)
                    user.first_name = company_name
                    user.save()

                    user_profile, status = BaseProfile.objects.get_or_create(user=user)
                    try:
                        city_obj = City.objects.get(id=city)
                        user_profile.city = city_obj
                    except:
                        pass
                    user_profile.user_type = 'fleet_admin'
                    user_profile.address = address
                    if ceo_id_proof:
                        ceo_id_proof = "{0}{1}".format(str(settings.BUCKET_URL), str(ceo_id_proof))
                        user_profile.ceo_id_proof = ceo_id_proof
                    user_profile.status = 'not_verified'
                    user_profile.save()

                    messages.success(request,
                                     request.lbl_fleet_signup_success1 + " %s" % user.email + request.lbl_fleet_signup_success2)
                except IntegrityError:
                    messages.error(request, request.lbl_another_username_exists)
            else:
                messages.error(request, request.lbl_another_username_exists)

        return redirect(reverse('dashboard:fleet-signup'))


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class HomeView(TemplateView):
    """
    View for rendering the home page of the dashboard
    """
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        if not self.request.user.is_superuser and not self.request.user.is_staff:
            return redirect("dashboard:index")
        context = {}
        context = super(HomeView, self).get_context_data(**kwargs)
        # Fetching necessary data from database to reduce database load/delay
        context['users'] = BaseProfile.objects.filter(status='active', user_type='app_user').count()
        transfers = []
        active_statuses = ['in_transit', 'loading']

        if self.request.user.is_superuser:
            context['partner'] = BaseProfile.objects.filter(user_type='driver', status='active').count()
            context['damage'] = Damage.objects.filter(deleted=False).count()
            context['completed_trips'] = Transfer.objects.filter(deleted=False, status='completed').count()
            context['active_trips'] = Transfer.objects.filter(deleted=False, status__in='in_transit').count()
            context['city'] = City.objects.all()
            transfers = Transfer.objects.filter(status__in=active_statuses)

        elif self.request.user.is_staff:
            try:
                user_profile = BaseProfile.objects.get(user=self.request.user)
                if user_profile.user_type == 'fleet_admin':
                    context['city'] = City.objects.filter(id=user_profile.city.id)
                    context['damage'] = Damage.objects.filter(deleted=False,
                                                              transfer_id__driver__fleet_id=user_profile).values(
                        'transfer_id').distinct().count()
                    context['completed_trips'] = Transfer.objects.filter(deleted=False, status='completed',
                                                                         driver__fleet_id=user_profile).count()
                    context['active_trips'] = Transfer.objects.filter(deleted=False, status__in=active_statuses,
                                                                      driver__fleet_id=user_profile).count()

                    transfers = Transfer.objects.filter(driver__fleet_id=user_profile, status__in=active_statuses)
                elif user_profile.user_type == 'admin_user' or user_profile.user_type == 'operator':
                    context['partner'] = BaseProfile.objects.filter(city=user_profile.city, status='active',
                                                                    user_type='driver').count()
                    context['city'] = City.objects.filter(id=user_profile.city.id)
                    context['damage'] = Damage.objects.filter(deleted=False,
                                                              transfer_id__driver__city=user_profile.city).values(
                        'transfer_id').distinct().count()
                    context['completed_trips'] = Transfer.objects.filter(deleted=False, status='completed',
                                                                         city=user_profile.city).count()
                    context['active_trips'] = Transfer.objects.filter(deleted=False, status__in=active_statuses,
                                                                      city=user_profile.city).count()
                    transfers = Transfer.objects.filter(city=user_profile.city, status__in=active_statuses)


            except:
                pass

        dic = []
        peru_timezone = pytz.timezone('America/Lima')
        for transfer in transfers:
            transfer_pickup = TransferLocation.objects.get(transfer_id=transfer, loc_type='pickup')
            transfer_drop = TransferLocation.objects.get(transfer_id=transfer, loc_type='drop')

            logger_me.debug(transfer)
            count = Damage.objects.filter(transfer_id=transfer).aggregate(count=Sum('count'))["count"]
            setattr(transfer, 'no_damaged_items', count)
            setattr(transfer, 'transfer_pickup', transfer_pickup.location_name)
            setattr(transfer, 'transfer_drop', transfer_drop.location_name)
            transfer_on = transfer.transfer_on.astimezone(peru_timezone)
            added_time = str(transfer_on.strftime('%d-%m-%Y %I:%M %p')) + "\n"
            setattr(transfer, 'added_time', added_time)

        context['transfers'] = transfers
        context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
        return context


class LogoutView(View):
    """
    View for logging out user and redirect to login page
    """

    @staticmethod
    def get(request):
        if request.user.is_authenticated:
            logout(request)
        return redirect(reverse('dashboard:dashboard-home-page'))


class ForgotPasswordView(TemplateView):
    """
    View for rendering and handling password recovery procedures
    """
    template_name = 'dashboard/page-recoverpw.html'

    @staticmethod
    def post(request):
        email = request.POST.get('email', '')
        if email != '':
            try:
                validate_email(email)  # Validating email with build in django function
                user_profile_obj = BaseProfile.objects.get(user__email=email)
                user_profile_obj.set_reset_key()  # Setting new password reset key
                user_profile_obj.save()

                # Sending email to user for resetting the password
                context = {
                    "link": "http://{0}/dashboard/reset-password/{1}/".format(
                        request.META['HTTP_HOST'], user_profile_obj.reset_key),
                    "lbl_forgot_pwd_link_reset": request.lbl_forgot_pwd_link_reset,
                    "lbl_reset_pwd": request.lbl_reset_pwd
                }
                message = get_template('dashboard/email-templates/action.html').render(context)
                subject = request.lbl_reset_pwd
                to = [user_profile_obj.user.email]

                # Calling function for sending email via separate thread
                threading.Thread(target=send_template_email, args=(subject, message, to)).start()
                # return render(request, 'dashboard/page-confirm-mail.html', {"email": user_profile_obj.user.email})
                # return render_to_string('dashboard/page-confirm-mail.html', {"email": user_profile_obj.user.email})
                # return render_to_response('dashboard/page-confirm-mail.html', {"email": user_profile_obj.user.email})

                params = {
                    "email": user_profile_obj.user.email,
                    "lbl_email_sent_to": request.lbl_email_sent_to,
                    "lbl_with_reset_link": request.lbl_with_reset_link,
                    "lbl_page_redirect_5_sec": request.lbl_page_redirect_5_sec,
                    "lbl_conf_mail": request.lbl_conf_mail
                }
                content = get_template('dashboard/page-confirm-mail.html').render(params)
                return HttpResponse(content)

            except BaseProfile.DoesNotExist:
                # User does not exist with provided email address
                messages.error(request, "User with provided email address is not registered")

            except ValidationError:
                # Invalid email format, Response from 'validate_email' function
                messages.error(request, "Please provide a valid email address")

        else:  # Invalid email
            messages.error(request, "Please provide a valid email address")

        return redirect(reverse('dashboard:forgot-password'))


class ResetPasswordView(TemplateView):
    """
    View for resetting the user password
    This view will be called when the user clicks the reset password link in email
    """
    template_name = 'dashboard/page-reset-password.html'

    def get_context_data(self, **kwargs):
        context = super(ResetPasswordView, self).get_context_data(**kwargs)
        reset_key = kwargs['reset_key']
        try:
            # Verifying if reset key is valid
            user_profile = BaseProfile.objects.get(reset_key=reset_key)
            # Checking if reset key expired
            context['valid_reset_key'] = user_profile.verify_reset_key_expiry()
        except BaseProfile.DoesNotExist:
            # Reset key is not valid or it expired
            context['valid_reset_key'] = False
        return context

    @staticmethod
    def post(request, **kwargs):
        reset_key = kwargs['reset_key']
        password = request.POST.get('new_password', '')
        context = {}
        try:
            # Verifying if reset key is valid
            user_profile = BaseProfile.objects.get(reset_key=reset_key)
            # Verifying if reset key has expired
            if user_profile.verify_reset_key_expiry():
                # Setting new password
                user_profile.user.set_password(password)
                user_profile.user.save()
                user_profile.reset_key = None  # Removing reset key after one use
                user_profile.reset_key_expiration = None  # Removing the expiry time of reset key
                user_profile.save()
                messages.success(request, request.lbl_reset_password_success)
                return redirect(reverse('dashboard:dashboard-home-page'))

            else:  # Reset key has expired
                # Setting flash to take necessary precautions
                context['valid_reset_key'] = False

        except BaseProfile.DoesNotExist:  # Reset key is invalid
            context['valid_reset_key'] = False

        return render(request, 'dashboard/page-reset-password.html')


################################################################################################################
# -------------------------------------------- ADMIN MANAGEMENT END------------------------------------------- #
################################################################################################################
@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class ChangePassword(TemplateView):
    """
    View for changing password for admin's
    """
    template_name = 'dashboard/admin-profile.html'

    @staticmethod
    def post(request):

        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        if old_password == new_password:
            messages.error(request, "Old Password and New password cannot be same!")
            return redirect(reverse('dashboard:update-profile'))
        admin_user = request.user
        if old_password and new_password != '':
            if admin_user.check_password(old_password):  # Checking if old password is correct
                admin_user.set_password(new_password)  # Setting new password
                admin_user.save()
                messages.success(request, request.lbl_password_changed_success)

            else:
                messages.error(request, request.lbl_incorrect_old_password)

        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:update-profile'))


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class UpdateProfile(TemplateView):
    """
    View for Update Profile
    """
    template_name = 'dashboard/admin-profile.html'

    def get_context_data(self, **kwargs):
        context = super(UpdateProfile, self).get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            context['admin_profile'] = admin_profile
            onoffswitch = OnOffSwitch.objects.filter(id=1)
            context['onoffswitch'] = onoffswitch
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)
        return context

    @staticmethod
    def post(request):

        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        address = request.POST.get('address', '')
        profile_pic = request.POST.get('image1', '')
        if first_name != '':
            admin_profile = BaseProfile.objects.get(user=request.user)
            admin_profile.user.first_name = first_name
            admin_profile.user.last_name = last_name
            admin_profile.address = address
            if profile_pic:
                upload1 = "{0}{1}".format(str(settings.BUCKET_URL), str(profile_pic))
                admin_profile.profile_pic = upload1
            request.session['image'] = admin_profile.profile_pic
            admin_profile.save()
            admin_profile.user.save()
            request.session['company'] = admin_profile.user.first_name + ' ' + admin_profile.user.last_name
            messages.success(request, request.lbl_profile_details_updated)

        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:update-profile'))


def delete_profile_image(request):
    if request.method == "GET":
        user_id = request.GET.get('user_id', '')
        try:
            obj = BaseProfile.objects.get(id=user_id)
            obj.profile_pic = ''
            obj.save()
            result_data = request.lbl_profile_image_deleted

        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)
        return JsonResponse(result_data, safe=False)


class Error404View(View):
    """
    If no url is found redirected to this view to show error page
    """

    @staticmethod
    def get(request):
        return redirect(reverse('dashboard:dashboard-login'))


class DashboardLoginView(TemplateView):
    template_name = 'dashboard/page-login.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardLoginView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                if self.request.user.is_superuser or self.request.user.is_staff:
                    response_flag = True
                else:
                    try:
                        userprofile_obj = BaseProfile.objects.get(user=self.request.user)
                        if userprofile_obj.user_type == 'fleet_admin' and userprofile_obj.status == 'active':
                            response_flag = True
                        else:
                            response_flag = False
                    except:
                        response_flag = False
            except:
                response_flag = False
            if response_flag:
                message = "Cannot Login to the Dashboard"
                logout(self.request)
                return redirect('/dashboard/login')
            else:
                message = "Already logged in to the Dashboard"
                return redirect('/dashboard')
        else:
            return context

    def post(self, request):
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if username == '' or password == '':
            messages.error(request, 'Username and password cannot be blank')
            return redirect(dashboard_login)
        else:
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    return redirect('/dashboard/')
                else:
                    try:
                        userprofile_obj = BaseProfile.objects.get(user=user)
                        if userprofile_obj.user_type == 'fleet_admin' and userprofile_obj.status == 'active':
                            login(request, user)
                            return redirect("/dashboard/")
                        else:
                            return redirect(dashboard_login)
                    except:
                        return redirect(dashboard_login)

            else:
                messages.error(request, 'Sorry Username or password Wrong Try again!')
                return redirect(dashboard_login)


class DashboardHomeView(TemplateView):
    template_name = 'dashboard/index.html'

    def dispatch(self, request, *args, **kwargs):
        context = super(DashboardHomeView, self).dispatch(request, *args, **kwargs)
        if request.user.is_authenticated:
            return context
        else:
            messages.error(request, "Sorry Kindly login to continue")
            return redirect('/dashboard/login')

    def get_context_data(self, **kwargs):
        context = super(DashboardHomeView, self).get_context_data(**kwargs)
        context['page'] = 'Home'
        return context


class DashboardLogoutView(View):
    def get(self, *args):
        logout(self.request)
        return redirect(dashboard_login)


class DashboardProfileView(TemplateView):
    template_name = 'dashboard/profile.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        context = super(DashboardProfileView, self).dispatch(request, *args, **kwargs)
        context['page'] = 'Profile'
        try:
            user_pro_obj = BaseProfile.objects.get(user=user)
        except BaseProfile.DoesNotExist:
            profile_obj = BaseProfile(user=user)
            profile_obj.save()
        except:
            messages.error(request, 'Something Went wrong!')
            return redirect('/dashboard')
        return context

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super(DashboardProfileView, self).get_context_data(**kwargs)
        try:
            user_pro_obj = BaseProfile.objects.get(user=user)
            context['user_profile'] = user_pro_obj
        except:
            messages.error(self.request, 'Something Went wrong!')
            context['user_profile'] = ''
        return context

    def post(self, request):
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        req_type = request.POST.get('request_type', '')
        if req_type == 'profile':
            if name != '' or email != '':
                user_profile = BaseProfile.objects.get(user=request.user)
                user_profile.user.first_name = name
                user_profile.user.email = email
                user_profile.user.save()
                messages.success(request, "Profile Updated Successfully")
            else:
                messages.error(request, 'Name or Email cannot be empty')
        else:
            if password != '':
                user_obj = BaseProfile.objects.get(user=request.user)
                user_obj.user.set_password(password)
                user_obj.user.save()
                messages.success(request, "Password Reset successfull")
            else:
                messages.error(request, 'Password Cannot be blank')
        return redirect('/dashboard/profile')


# -------------------------------------------- COMMODITY MANAGEMENT START----------------------------------- #

@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ListCommodity(TemplateView):
    """
    View for listing Commodity
    """
    template_name = 'dashboard/commodity-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListCommodity, self).get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False

            commodity_list = Commodity.objects.filter(city=admin_profile.city).order_by('-id')
            context['commodity_list'] = commodity_list
            context['heading'] = 'Commodities'
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)
        return context


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class AddCommodity(View):
    """
    View for adding new Commodity
    """

    @staticmethod
    def post(request):
        item_name = request.POST.get('item_name', '')
        length = request.POST.get('length', '')
        breadth = request.POST.get('breadth', '')
        height = request.POST.get('height', '')
        volume = request.POST.get('volume', '')
        material_type = request.POST.get('material_type', '')
        image1 = request.POST.get('image1', '')
        is_plugable = request.POST.get('is_plugable', '')
        installation_charge = request.POST.get('installation_charge', '')
        no_of_loaders = request.POST.get('loader', 1)

        if is_plugable == '1':
            is_plugable = True
        else:
            is_plugable = False

        if item_name != '':
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                if not Commodity.objects.filter(item_name=item_name, city=admin_profile.city).exists():
                    item_obj = Commodity(item_name=item_name, material_type=material_type, added_by=admin_profile)
                    upload1 = "{0}{1}".format(str(settings.BUCKET_URL), str(image1))
                    item_obj.image = upload1
                    item_obj.length = length
                    item_obj.breadth = breadth
                    item_obj.height = height
                    item_obj.volume = volume
                    item_obj.city = admin_profile.city
                    item_obj.is_plugable = is_plugable
                    item_obj.loaders = no_of_loaders
                    if installation_charge and is_plugable:
                        item_obj.installation_charge = installation_charge
                    item_obj.save()

                    messages.success(request, request.lbl_added_new_commodity)
                else:
                    messages.error(request, request.lbl_commodity_already_exist)
                    return redirect("dashboard:list-commodity")
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-commodity'))


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class UploadCommodityCsv(View):
    """
    View for adding new Commodity
    """

    @staticmethod
    def post(request):

        csv_file = request.FILES.get('commodity_upload')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return redirect("dashboard:list-commodity")
        admin_profile = BaseProfile.objects.get(user=request.user)
        with open('media/'+csv_file.name, 'wb+') as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)

        with open(settings.BASE_DIR + '/media/'+csv_file.name) as f:

            commodity_items = csv.reader(f)
            commodity_items = list(commodity_items)
            commodity_items.pop(0)
            logger_me.debug(commodity_items)

        for item in commodity_items:

            item_name = item[0]
            length = item[1]
            breadth = item[2]
            height = item[3]
            volume = int(length)*int(breadth)*int(height)
            material_type = item[4]
            no_of_loaders = item[5]
            image1 = item[6]
            is_plugable = item[7]
            if is_plugable == 'TRUE':
                installation_charge = item[8]
            else:
                installation_charge = ''

            if is_plugable == '1':
                is_plugable = True
            else:
                is_plugable = False

            if item_name != '':
                try:
                    if not Commodity.objects.filter(item_name=item_name, city=admin_profile.city).exists():
                        item_obj = Commodity(item_name=item_name, material_type=material_type, added_by=admin_profile)
                        upload1 = str(image1)
                        item_obj.image = upload1
                        item_obj.length = length
                        item_obj.breadth = breadth
                        item_obj.height = height
                        item_obj.volume = volume
                        item_obj.city = admin_profile.city
                        item_obj.is_plugable = is_plugable
                        item_obj.loaders = no_of_loaders
                        if installation_charge and is_plugable:
                            item_obj.installation_charge = installation_charge
                        item_obj.save()

                    # else:
                    #     messages.error(request, request.lbl_commodity_already_exist)
                    #     return redirect("dashboard:list-commodity")
                except BaseProfile.DoesNotExist:
                    messages.error(request, request.lbl_invalid_user)
            else:
                messages.error(request, request.lbl_provide_valid_data)

        messages.success(request, 'Commodities updated successfully')
        return redirect(reverse('dashboard:list-commodity'))


def delete_commodity(request):
    if request.method == "GET":
        commodity_id = request.GET.get('commodity_id', '')
        try:
            obj = Commodity.objects.get(id=commodity_id)
            obj.delete()
            result_data = request.lbl_commodity_deleted

        except Commodity.DoesNotExist:
            messages.error(request, request.lbl_invalid_commodity)
        return JsonResponse(result_data, safe=False)


def delete_commodity_image(request):
    if request.method == "GET":
        commodity_id = request.GET.get('item_id', '')
        try:
            obj = Commodity.objects.get(id=commodity_id)
            obj.image = ''
            obj.save()
            result_data = request.lbl_commodity_image_deleted

        except Commodity.DoesNotExist:
            messages.error(request, request.lbl_invalid_commodity)
        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class EditCommodity(TemplateView):
    """View for Update to  Commodity"""

    template_name = "dashboard/edit-commodity.html"

    def get_context_data(self, **kwargs):
        context = super(EditCommodity, self).get_context_data(**kwargs)
        commodity_id = kwargs['commodity_id']
        try:
            # Fetching editable user data
            item_data = Commodity.objects.get(id=commodity_id)
            context['item_data'] = item_data

        except Commodity.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)

        return context

    def post(self, request, **kwargs):
        item_name = self.request.POST.get('item_name', '')
        length = self.request.POST.get('length', '')
        breadth = self.request.POST.get('breadth', '')
        height = self.request.POST.get('height', '')
        volume = self.request.POST.get('volume', '')
        material_type = self.request.POST.get('material_type', '')
        commodity_id = kwargs['commodity_id']
        image1 = self.request.POST.get('image1', '')
        installation_charge = self.request.POST.get('installation_charge', '')
        is_plugable = request.POST.get('is_plugable', '')
        if is_plugable == '1':
            is_plugable = True
        else:
            is_plugable = False
        try:
            admin_profile = BaseProfile.objects.get(user=request.user)
            if not Commodity.objects.filter(~Q(id=commodity_id), item_name=item_name, city=admin_profile.city).exists():
                try:
                    item_obj = Commodity.objects.get(id=commodity_id)
                    item_obj.item_name = item_name
                    item_obj.length = float(length)
                    item_obj.breadth = float(breadth)
                    item_obj.height = float(height)
                    item_obj.volume = float(volume)
                    if installation_charge and is_plugable:
                        item_obj.installation_charge = installation_charge
                    else:
                        item_obj.installation_charge = 0
                    item_obj.is_plugable = is_plugable
                    item_obj.material_type = material_type
                    if image1:
                        upload1 = "{0}{1}".format(str(settings.BUCKET_URL), str(image1))
                        item_obj.image = upload1
                    item_obj.save()

                    messages.success(request, request.lbl_commodity_update)
                    return redirect("dashboard:list-commodity")

                except Commodity.DoesNotExist:
                    messages.error(request, request.lbl_invalid_commodity)
                    return redirect(reverse('dashboard:list-commodity'))
            else:
                messages.error(request, request.lbl_commodity_already_exist)
                return redirect("dashboard:edit-commodity", commodity_id)
        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)
            return redirect(reverse('dashboard:list-commodity'))
        return redirect(reverse('dashboard:list-commodity'))


# -------------------------------------------- COMMODITY MANAGEMENT END----------------------------------- #

# -------------------------------------------- TRANSFER TYPE MANAGEMENT START----------------------------------- #

@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ListTransferType(TemplateView):
    """
    View for listing Transfer Type
    """
    template_name = 'dashboard/transfer-type-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListTransferType, self).get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False

            type_list = TransferType.objects.filter(city=admin_profile.city)
            context['type_list'] = type_list
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_admin)
        return context


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class AddTransferType(View):
    """
    View for adding new Transfer Type
    """

    @staticmethod
    def post(request):
        transfer_from = request.POST.get('transfer_from', '')
        transfer_to = request.POST.get('transfer_to', '')
        charge = request.POST.get('charge', '')
        if transfer_from != '' and transfer_to != '':
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                if not TransferType.objects.filter(transfer_from=transfer_from, transfer_to=transfer_to,
                                                   city=admin_profile.city).exists():
                    item_obj = TransferType(transfer_from=transfer_from, transfer_to=transfer_to,
                                            added_by=admin_profile, city=admin_profile.city)
                    item_obj.charge = charge
                    item_obj.city = admin_profile.city
                    item_obj.save()

                    messages.success(request, request.lbl_added_new_transfer_type)
                else:
                    messages.error(request, request.lbl_transfer_type_already_exist)
                    return redirect("dashboard:list-transfer-type")
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-transfer-type'))


def delete_transfer_type(request):
    if request.method == "GET":
        transfer_type_id = request.GET.get('transfer_type_id', '')
        try:
            obj = TransferType.objects.get(id=transfer_type_id)
            obj.delete()
            result_data = request.lbl_transfer_type_deleted

        except TransferType.DoesNotExist:
            messages.error(request, request.lbl_invalid_transfer_type)
        return JsonResponse(result_data, safe=False)


@method_decorator(verify_permission(level=None), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class EditTransferType(TemplateView):
    """View for Update to  Commodity"""

    template_name = "dashboard/edit-transfer-type.html"

    def get_context_data(self, **kwargs):
        context = super(EditTransferType, self).get_context_data(**kwargs)
        transfer_type_id = kwargs['transfer_type_id']
        try:
            # Fetching editable user data
            item_data = TransferType.objects.get(id=transfer_type_id)
            context['item_data'] = item_data

        except TransferType.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)

        return context

    def post(self, request, **kwargs):
        transfer_from = self.request.POST.get('transfer_from', '')
        transfer_to = self.request.POST.get('transfer_to', '')
        charge = self.request.POST.get('charge', '')
        transfer_type_id = kwargs['transfer_type_id']
        try:
            admin_profile = BaseProfile.objects.get(user=request.user)
            if not TransferType.objects.filter(~Q(id=transfer_type_id), transfer_from=transfer_from,
                                               transfer_to=transfer_to, city=admin_profile.city).exists():
                try:
                    item_obj = TransferType.objects.get(id=transfer_type_id)
                    item_obj.transfer_from = transfer_from
                    item_obj.transfer_to = transfer_to
                    item_obj.charge = charge
                    item_obj.save()

                    messages.success(request, request.lbl_transfer_type_update)
                    return redirect("dashboard:list-transfer-type")

                except TransferType.DoesNotExist:
                    messages.error(request, request.lbl_invalid_transfer_type)
                    return redirect(reverse('dashboard:list-transfer-type'))
            else:
                messages.error(request, request.lbl_transfer_type_already_exist)
                return redirect("dashboard:edit-transfer-type", transfer_type_id)
        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)
        return redirect(reverse('dashboard:list-transfer-type'))


# -------------------------------------------- TRANSFER TYPE MANAGEMENT END----------------------------------- #


# -------------------------------------------- SERVICES MANAGEMENT START----------------------------------- #

@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ListService(TemplateView):
    """
    View for listing Transfer Type
    """
    template_name = 'dashboard/service-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListService, self).get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False
            service_list = Service.objects.filter(city=admin_profile.city).order_by('-id')
            context['service_list'] = service_list
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_admin)
        return context


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class AddService(View):
    """
    View for adding new Service
    """

    @staticmethod
    def post(request):
        service_from = request.POST.get('service_from', '')
        service_to = request.POST.get('service_to', '')
        charge = request.POST.get('charge', '')
        # charge_20_30 = request.POST.get('charge_20_30', '')
        # charge_30_40 = request.POST.get('charge_30_40', '')
        # charge_40_50 = request.POST.get('charge_40_50', '')
        # charge_50_60 = request.POST.get('charge_50_60', '')
        # charge_60_70 = request.POST.get('charge_60_70', '')
        if service_from and service_from != '':
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                if not Service.objects.filter(service_from=service_from, service_to=service_to,
                                              city=admin_profile.city).exists():
                    item_obj = Service(service_from=service_from, service_to=service_to, added_by=admin_profile)
                    item_obj.charge = charge
                    # item_obj.charge_20_30 = charge_20_30
                    # item_obj.charge_30_40 = charge_30_40
                    # item_obj.charge_40_50 = charge_40_50
                    # item_obj.charge_50_60 = charge_50_60
                    # item_obj.charge_60_70 = charge_60_70
                    item_obj.city = admin_profile.city
                    item_obj.set_as_plugable()
                    item_obj.save()

                    messages.success(request, request.lbl_added_new_service)
                else:
                    messages.error(request, request.lbl_service_already_exist)
                    return redirect("dashboard:list-service")
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-service'))


def delete_service(request):
    if request.method == "GET":
        service_id = request.GET.get('service_id', '')
        try:
            obj = Service.objects.get(id=service_id)
            obj.delete()
            result_data = request.lbl_service_deleted

        except Service.DoesNotExist:
            messages.error(request, request.lbl_invalid_service)
        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class EditService(TemplateView):
    """View for Update to  Service"""

    template_name = "dashboard/edit-service.html"

    def get_context_data(self, **kwargs):
        context = super(EditService, self).get_context_data(**kwargs)
        service_id = kwargs['service_id']
        try:
            # Fetching editable user data
            item_data = Service.objects.get(id=service_id)
            context['item_data'] = item_data
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            service_list = Service.objects.filter(city=admin_profile.city)
            context['service_list'] = service_list

        except Service.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)

        return context

    def post(self, request, **kwargs):
        service_name_en = request.POST.get('service_name_en', '')
        service_name_es = request.POST.get('service_name_es', '')
        service_description_en = request.POST.get('service_description_en', '')
        service_description_es = request.POST.get('service_description_es', '')
        charge = request.POST.get('charge', '')
        # charge_10_20 = request.POST.get('charge_10_20', '')
        # charge_20_30 = request.POST.get('charge_20_30', '')
        # charge_30_40 = request.POST.get('charge_30_40', '')
        # charge_40_50 = request.POST.get('charge_40_50', '')
        # charge_50_60 = request.POST.get('charge_50_60', '')
        # charge_60_70 = request.POST.get('charge_60_70', '')
        service_id = kwargs['service_id']
        try:
            admin_profile = BaseProfile.objects.get(user=request.user)
            try:
                if not Service.objects.filter(~Q(id=service_id), display_service_name_en=service_name_en,
                                              display_service_name_es=service_name_es,
                                              city=admin_profile.city).exists():
                    item_obj = Service.objects.get(id=service_id)
                    item_obj.display_service_name_en = service_name_en
                    item_obj.display_service_name_es = service_name_es
                    item_obj.service_description_en = service_description_en
                    item_obj.service_description_es = service_description_es
                    item_obj.charge = charge
                    # item_obj.charge_10_20 = charge_10_20
                    # item_obj.charge_20_30 = charge_20_30
                    # item_obj.charge_30_40 = charge_30_40
                    # item_obj.charge_40_50 = charge_40_50
                    # item_obj.charge_50_60 = charge_50_60
                    # item_obj.charge_60_70 = charge_60_70
                    item_obj.save()
                    messages.success(request, request.lbl_service_update)
                    return redirect("dashboard:list-service")
                else:
                    messages.error(request, request.lbl_service_already_exist)
                    return redirect("dashboard:edit-service", service_id)
            except Service.DoesNotExist:
                messages.error(request, request.lbl_invalid_service)
                return redirect(reverse('dashboard:list-service'))
        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)
        return redirect(reverse('dashboard:list-service'))


# -------------------------------------------- SERVICES MANAGEMENT END----------------------------------- #


# -------------------------------------------- CITY MANAGEMENT START----------------------------------- #

@method_decorator((login_required, verify_permission(level='superuser')), name='dispatch')
class ListCity(TemplateView):
    """
    View for listing Cities
    """
    template_name = 'dashboard/city-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListCity, self).get_context_data(**kwargs)
        city_list = City.objects.all()
        context['city_list'] = city_list
        context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
        return context


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class AddCity(View):
    """
    View for adding new City
    """

    @staticmethod
    def post(request):
        # city_name = request.POST.get('city_name', '')
        city_lat = request.POST.get('city_lat', 0)
        city_lng = request.POST.get('city_lng', 0)
        city_name = request.POST.get('city', "")
        poly_data = request.POST.get('polygon', "")
        city_name_arr = city_name.split(',')
        city_name = city_name_arr[0]
        payment_mode = request.POST.get('payment_type', '')
        logger_me.debug('----' + city_name)
        if city_name != '':
            try:
                if not City.objects.filter(city_name=city_name).exists():
                    item_obj = City(city_name=city_name, polygon_data=poly_data)
                    if payment_mode != '':
                        if payment_mode == 'cash':
                            item_obj.cash_only = True
                    item_obj.save()

                    messages.success(request, request.lbl_added_new_city)
                else:
                    messages.error(request, city_name + ' ' + request.lbl_city_already_exist)
                    return redirect("dashboard:list-city")
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-city'))


def delete_city(request):
    if request.method == "GET":
        city_id = request.GET.get('city_id', '')
        try:
            obj = City.objects.get(id=city_id)
            obj.delete()
            result_data = request.lbl_city_deleted

        except City.DoesNotExist:
            messages.error(request, request.lbl_invalid_city)
        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class EditCity(TemplateView):
    """View for Update to  City"""

    template_name = "dashboard/edit-city.html"

    def get_context_data(self, **kwargs):
        context = super(EditCity, self).get_context_data(**kwargs)
        city_id = kwargs['city_id']
        try:
            # Fetching editable user data
            item_data = City.objects.get(id=city_id)
            context['item_data'] = item_data
            context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY

        except City.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)
            return redirect(self.request.META['HTTP_REFERER'])

        return context

    def post(self, request, **kwargs):
        # city_name = self.request.POST.get('city_name', '')
        city_lat = self.request.POST.get('city_lat', 0)
        city_lng = self.request.POST.get('city_lng', 0)
        city_name = request.POST.get('city_name', "")
        city_name_arr = city_name.split(',')
        city_name = city_name_arr[0]
        city_id = kwargs['city_id']
        poly_data = request.POST.get('polygon', "")
        if not City.objects.filter(~Q(id=city_id), city_name=city_name).exists():
            try:
                item_obj = City.objects.get(id=city_id)
                item_obj.city_name = city_name
                item_obj.polygon_data = poly_data
                item_obj.save()

                messages.success(request, request.lbl_city_update)
                return redirect("dashboard:list-city")

            except City.DoesNotExist:
                messages.error(request, request.lbl_invalid_city)
                return redirect(reverse('dashboard:list-city'))
        else:
            messages.error(request, city_name + ' ' + request.lbl_city_already_exist)
            return redirect("dashboard:edit-city", city_id)
        return redirect(reverse('dashboard:list-city'))


# -------------------------------------------- CITY MANAGEMENT END----------------------------------- #


# -------------------------------------------- DISCOUNT MANAGEMENT START----------------------------------- #


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ListDiscount(TemplateView):
    """
    View for listing Transfer Type
    """
    template_name = 'dashboard/discount-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListDiscount, self).get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False
            discount_list = Discount.objects.filter(service_type__city=admin_profile.city, status='active')
            context['discount_list'] = discount_list
            service_list = Service.objects.filter(city=admin_profile.city)
            context['service_list'] = service_list
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_admin)
        return context


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class AddDiscount(View):
    """
    View for adding new Discount
    """

    @staticmethod
    def post(request):
        price_range = request.POST.get('price_range', '')
        rate_from, rate_to = price_range.split('-')
        discount = request.POST.get('discount', '')
        service_type = request.POST.get('service_type', '')
        if rate_from != '' and rate_to != '' and discount != '' and service_type != '':
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                service_obj = Service.objects.get(id=service_type, city=admin_profile.city)
                if not Discount.objects.filter(rate_from=rate_from, rate_to=rate_to, service_type=service_obj,
                                               service_type__city=admin_profile.city, status='active').exists():
                    item_obj = Discount(rate_from=rate_from, rate_to=rate_to, service_type=service_obj,
                                        added_by=admin_profile)
                    item_obj.discount = discount
                    item_obj.status = 'active'
                    item_obj.save()

                    messages.success(request, request.lbl_added_new_discount)
                else:
                    messages.error(request, request.lbl_discount_already_exist)
                    return redirect("dashboard:list-discount")
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
            except Service.DoesNotExist:
                messages.error(request, request.lbl_invalid_service)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-discount'))


def delete_discount(request):
    if request.method == "GET":
        discount_id = request.GET.get('discount_id', '')
        admin_profile = BaseProfile.objects.get(user=request.user)
        try:
            obj = Discount.objects.get(id=discount_id, service_type__city=admin_profile.city)
            obj.status = 'deleted'
            obj.save()
            result_data = request.lbl_discount_deleted

        except Discount.DoesNotExist:
            messages.error(request, request.lbl_invalid_discount)
        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class EditDiscount(TemplateView):
    """View for Update to  Discount"""

    template_name = "dashboard/edit-discount.html"

    def get_context_data(self, **kwargs):
        context = super(EditDiscount, self).get_context_data(**kwargs)
        discount_id = kwargs['discount_id']
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # Fetching editable user data
            item_data = Discount.objects.get(id=discount_id)
            context['item_data'] = item_data

            service_list = Service.objects.filter(city=admin_profile.city)
            context['service_list'] = service_list

        except Discount.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)

        return context

    def post(self, request, **kwargs):
        price_range = request.POST.get('price_range', '')
        rate_from, rate_to = price_range.split('-')
        discount = request.POST.get('discount', '')
        service_type = request.POST.get('service_type', '')
        discount_id = kwargs['discount_id']
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            service_obj = Service.objects.get(id=service_type, city=admin_profile.city)
            if not Discount.objects.filter(~Q(id=discount_id), rate_from=rate_from, rate_to=rate_to,
                                           service_type=service_obj, service_type__city=admin_profile.city,
                                           status='active').exists():
                try:
                    item_obj = Discount.objects.get(id=discount_id)
                    item_obj.discount = discount
                    item_obj.rate_from = rate_from
                    item_obj.rate_to = rate_to
                    item_obj.service_type = service_obj
                    item_obj.save()

                    messages.success(request, request.lbl_discount_update)
                    return redirect("dashboard:list-discount")

                except Discount.DoesNotExist:
                    messages.error(request, request.lbl_invalid_discount)
                    return redirect(reverse('dashboard:list-discount'))
            else:
                messages.error(request, request.lbl_discount_already_exist)
                return redirect("dashboard:edit-discount", discount_id)
        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)
        except Service.DoesNotExist:
            messages.error(request, request.lbl_invalid_service)
        return redirect(reverse('dashboard:list-discount'))


# -------------------------------------------- DISCOUNT MANAGEMENT END----------------------------------- #

# -------------------------------------------- TRUCK CREW MANAGEMENT START----------------------------------- #

@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
class ListTruckCrew(TemplateView):
    """
    View for listing Transfer Type
    """
    template_name = 'dashboard/crew-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListTruckCrew, self).get_context_data(**kwargs)
        truck_crew_list = []
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False
            truck_crew_list = TruckCrew.objects.filter(added_by__city=admin_profile.city).order_by('capacity_from')
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)

        context['truck_crew_list'] = truck_crew_list
        return context


@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class AddTruckCrew(View):
    """
    View for adding new Discount
    """

    @staticmethod
    def post(request):
        capacity_from = request.POST.get('capacity_from', '')
        capacity_to = request.POST.get('capacity_to', '')
        no_drivers = request.POST.get('no_drivers', '')
        no_loaders = request.POST.get('no_loaders', '')
        if no_drivers != '' and no_loaders != '' and capacity_from != '' and capacity_to != '':
            try:
                if request.user.is_superuser:
                    admin_profile, created = BaseProfile.objects.get_or_create(user=request.user,
                                                                               user_type='super_user')
                else:
                    admin_profile = BaseProfile.objects.get(user=request.user)
                if not TruckCrew.objects.filter(capacity_from__range=(capacity_from, capacity_to),
                                                added_by__city=admin_profile.city).exists():
                    if not TruckCrew.objects.filter(capacity_to__range=(capacity_from, capacity_to),
                                                    added_by__city=admin_profile.city).exists():
                        if float(capacity_from) < float(capacity_to):
                            item_obj = TruckCrew(capacity_from=capacity_from, capacity_to=capacity_to,
                                                 added_by=admin_profile)
                            item_obj.loading_peoples = no_loaders
                            item_obj.no_drivers = no_drivers
                            item_obj.save()
                            messages.success(request, request.lbl_added_new_truck_crew)
                        else:
                            messages.error(request, request.lbl_provide_valid_data)
                    else:
                        messages.error(request, request.lbl_truck_crew_already_exist)
                else:
                    messages.error(request, request.lbl_truck_crew_already_exist)
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-truck-crew'))


def delete_truck_crew(request):
    if request.method == "GET":
        crew_id = request.GET.get('crew_id', '')
        try:
            obj = TruckCrew.objects.get(id=crew_id)
            obj.delete()
            result_data = request.lbl_truck_crew_deleted

        except Discount.DoesNotExist:
            messages.error(request, request.lbl_invalid_truck_crew)
        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class EditTruckCrew(TemplateView):
    """View for Update to  Crew Details"""

    template_name = "dashboard/edit-crew.html"

    def get_context_data(self, **kwargs):
        context = super(EditTruckCrew, self).get_context_data(**kwargs)
        crew_id = kwargs['crew_id']
        try:
            # Fetching editable user data
            item_data = TruckCrew.objects.get(id=crew_id)
            context['item_data'] = item_data

        except TruckCrew.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_truck_crew)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)

        return context

    def post(self, request, **kwargs):
        capacity_from = request.POST.get('capacity_from', '')
        capacity_to = request.POST.get('capacity_to', '')
        no_drivers = request.POST.get('no_drivers', '')
        no_loaders = request.POST.get('no_loaders', '')
        a = request.POST.get('a', '')
        b = request.POST.get('b', '')
        c = request.POST.get('c', '')
        amount_per_helper = request.POST.get('amount_per_helper', 2)
        crew_id = kwargs['crew_id']
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            if not TruckCrew.objects.filter(~Q(id=crew_id), capacity_from__range=(capacity_from, capacity_to),
                                            added_by__city=admin_profile.city).exists():
                if not TruckCrew.objects.filter(~Q(id=crew_id), capacity_to__range=(capacity_from, capacity_to),
                                                added_by__city=admin_profile.city).exists():
                    if float(capacity_from) < float(capacity_to):
                        try:
                            item_obj = TruckCrew.objects.get(id=crew_id)
                            item_obj.capacity_from = capacity_from
                            item_obj.capacity_to = capacity_to
                            item_obj.loading_peoples = no_loaders
                            item_obj.no_drivers = no_drivers
                            item_obj.a = a
                            item_obj.b = b
                            item_obj.c = c
                            item_obj.amount_per_helper = amount_per_helper
                            item_obj.save()

                            messages.success(request, request.lbl_truck_crew_update)
                            return redirect("dashboard:list-truck-crew")

                        except TruckCrew.DoesNotExist:
                            messages.error(request, request.lbl_invalid_truck_crew)
                    else:
                        messages.error(request, request.lbl_provide_valid_data)
                        return redirect("dashboard:edit-truck-crew", crew_id)
                else:
                    messages.error(request, request.lbl_truck_crew_already_exist)
                    return redirect("dashboard:edit-truck-crew", crew_id)
            else:
                messages.error(request, request.lbl_truck_crew_already_exist)
                return redirect("dashboard:edit-truck-crew", crew_id)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)
        return redirect(reverse('dashboard:list-truck-crew'))


# -------------------------------------------- TRUCK CREW MANAGEMENT END----------------------------------- #

################################################################################################################
# --------------------------------------------ADMIN MANAGEMENT START------------------------------------------ #
################################################################################################################


@method_decorator((login_required, verify_permission(level='superuser')), name='dispatch')
class ListAdmin(TemplateView):
    """
    View for listing admin's
    """
    template_name = 'dashboard/admin_list.html'

    def get_context_data(self, **kwargs):
        context = super(ListAdmin, self).get_context_data(**kwargs)
        # Getting all the admin's except the current logged in admin
        admin_list = BaseProfile.objects.filter(
            user__is_staff=True, user__is_superuser=False, user__is_active=True
        ).exclude(user__email=self.request.user.email)

        companies = BaseProfile.objects.filter(user_type='admin_user', status='active', user__is_active=True)
        context['admin_list'] = companies
        city_list = City.objects.all()
        context['city_list'] = city_list
        return context


@method_decorator((login_required, verify_permission(level='superuser')), name='dispatch')
class AddAdmin(View):
    """
    View for adding new admin's
    """

    @staticmethod
    def post(request):
        username = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        city_name = request.POST.get('city_name', '')

        if username is not None:
            if not User.objects.filter(username=username):
                try:
                    random_password = random_number_generator(8)
                    logger_me.debug('random_password')
                    logger_me.debug(random_password)
                    user = User.objects.create_user(
                        username=username, email=username, password=random_password, is_staff=True)
                    user.first_name = first_name
                    user.last_name = last_name
                    user.is_active = True
                    user.save()

                    user_profile, status = BaseProfile.objects.get_or_create(user=user)
                    user_profile.user_type = 'admin_user'
                    city_obj = City.objects.get(id=city_name)
                    user_profile.city = city_obj
                    user_profile.status = 'active'
                    user_profile.save()

                    """
                        CREATE DEFAULT SERVICES FOR
                        1. Transfer (Packed - Packed)
                        2. Relocation Package Plus (Unpacked - Packed)
                        3. Relocation Package Plus Plus Uncrating (Unpacked - Unpacked)
                    """
                    services = []

                    if not Service.objects.filter(service_name='packed-packed', city=user_profile.city).exists():
                        services.append(
                            Service(service_name='packed-packed', display_service_name_en='Transfer',
                                    display_service_name_es='Traslado', service_description_en='Just move your items',
                                    service_description_es='Solo traslado de artículos previamente embalados por cliente',
                                    added_by=user_profile, city=user_profile.city))
                    if not Service.objects.filter(service_name='unpacked-packed', city=user_profile.city).exists():
                        services.append(
                            Service(service_name='unpacked-packed', display_service_name_en='Relocation Package',
                                    display_service_name_es='Embalaje + Traslado',
                                    service_description_en='Pack and move your items',
                                    service_description_es='incluye instalación de artículos seleccionados por el cliente',
                                    added_by=user_profile, city=user_profile.city))
                    if not Service.objects.filter(service_name='unpacked-unpacked', city=user_profile.city).exists():
                        services.append(
                            Service(service_name='unpacked-unpacked',
                                    display_service_name_en='Relocation Package + Uncrating',
                                    display_service_name_es='Embalaje + Traslado + Desembalaje',
                                    service_description_en='Pack, move and unpack your items',
                                    service_description_es='incluye instalación de artículos seleccionados por el cliente',
                                    added_by=user_profile, city=user_profile.city))
                    logger_me.debug(services)
                    Service.objects.bulk_create(services)

                    """
                    CREATE DEFAULT CREW FOR EACH CITY
                    """
                    truck_crews = []
                    if not TruckCrew.objects.filter(added_by__city=user_profile.city):
                        truck_crews.append(TruckCrew(capacity_from=1, capacity_to=3, no_drivers=1, loading_peoples=1,
                                                     added_by=user_profile))
                        truck_crews.append(TruckCrew(capacity_from=3.1, capacity_to=5, no_drivers=1, loading_peoples=1,
                                                     added_by=user_profile))
                        truck_crews.append(TruckCrew(capacity_from=5.1, capacity_to=7, no_drivers=1, loading_peoples=2,
                                                     added_by=user_profile))
                        truck_crews.append(TruckCrew(capacity_from=7.1, capacity_to=9, no_drivers=1, loading_peoples=2,
                                                     added_by=user_profile))

                        truck_crews.append(TruckCrew(capacity_from=9.1, capacity_to=11, no_drivers=1, loading_peoples=2,
                                                     added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=11.1, capacity_to=13, no_drivers=1, loading_peoples=3,
                                      added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=13.1, capacity_to=15, no_drivers=1, loading_peoples=3,
                                      added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=15.1, capacity_to=17, no_drivers=1, loading_peoples=4,
                                      added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=17.1, capacity_to=20, no_drivers=1, loading_peoples=4,
                                      added_by=user_profile))

                        truck_crews.append(
                            TruckCrew(capacity_from=20.1, capacity_to=25, no_drivers=1, loading_peoples=5,
                                      added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=25.1, capacity_to=30, no_drivers=1, loading_peoples=5,
                                      added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=30.1, capacity_to=35, no_drivers=1, loading_peoples=6,
                                      added_by=user_profile))
                        truck_crews.append(
                            TruckCrew(capacity_from=35.1, capacity_to=40, no_drivers=1, loading_peoples=6,
                                      added_by=user_profile))
                        TruckCrew.objects.bulk_create(truck_crews)

                    messages.success(request, request.lbl_added_admin_success + " %s" % user.email)

                    # Sending password as email to new admin
                    subject = "Muberz new account info"
                    ctx = {
                        "lbl_password_txt": request.lbl_password_txt,
                        "new_acc_info_added": request.new_acc_info_added,
                        "lbl_login_txt": request.lbl_login_txt,
                        "username": user.email,
                        "password": random_password,
                        "link": "http://{0}/dashboard/login/?email={1}&pass={2}".format(
                            request.META['HTTP_HOST'], user.email, random_password)
                    }
                    content = get_template("dashboard/email-templates/new_account_info.html").render(ctx)
                    threading.Thread(target=send_template_email, args=(subject, content, [user.email])).start()
                    # logger.error()
                except City.DoesNotExist:
                    messages.error(request, request.lbl_invalid_city)
                except IntegrityError:
                    messages.error(request, request.lbl_another_username_exists)
            else:
                messages.error(request, request.lbl_another_username_exists)

        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-admin'))


@method_decorator((login_required, verify_permission(level=super)), name='dispatch')
class EditAdmin(TemplateView):
    """View for Update to  Admin"""

    template_name = "dashboard/edit-admin.html"

    def get_context_data(self, **kwargs):
        context = super(EditAdmin, self).get_context_data(**kwargs)
        admin_id = kwargs['admin_id']
        try:
            # Fetching editable user data
            item_data = BaseProfile.objects.get(id=admin_id)
            context['item_data'] = item_data
            city_list = City.objects.all()
            context['city_list'] = city_list
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)

        return context

    def post(self, request, **kwargs):
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        city_name = request.POST.get('city_name', '')
        admin_id = kwargs['admin_id']
        try:
            item_obj = BaseProfile.objects.get(id=admin_id)
            item_obj.user.first_name = first_name
            item_obj.user.last_name = last_name
            city_obj = City.objects.get(id=city_name)
            item_obj.city = city_obj

            item_obj.save()
            item_obj.user.save()

            messages.success(request, request.lbl_admin_up_success)
            return redirect("dashboard:list-admin")

        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_admin)
        except City.DoesNotExist:
            messages.error(request, request.lbl_invalid_city)

            return redirect(reverse('dashboard:list-admin'))
        return redirect(reverse('dashboard:list-admin'))


def delete_admin(request):
    if request.method == "GET":
        admin_id = request.GET.get('admin_id', '')
        try:
            user = User.objects.get(id=admin_id)
            user.is_active = False
            user.save()
            # Admin shouldn't be deleted since every core data is mapped to the created admin
            # So if the admin is deleted then, the linked core data will be deleted.
            # Core datas are commodities, transfer records and all other data related to them.
            # It's very important not to delete admin from database.
            messages.success(request, request.lbl_admin_deleted)
            result_data = request.lbl_admin_deleted

        except User.DoesNotExist:
            messages.error(request, request.lbl_invalid_admin)
            result_data = request.lbl_invalid_admin

        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
class DeleteAdmin(View):
    """
    View for deleting admin's
    """

    @staticmethod
    def post(request):
        admin_user_id = request.POST.get('admin_user_id')
        if admin_user_id is not None:
            try:
                user = User.objects.get(id=admin_user_id)
                user.delete()
                messages.success(request, request.lbl_admin_deleted)

            except User.DoesNotExist:
                messages.error(request, request.lbl_invalid_admin)

        else:
            messages.error(request, request.lbl_invalid_admin)

        return redirect(reverse('dashboard:list-admin'))


################################################################################################################
# -------------------------------------------- ADMIN MANAGEMENT END------------------------------------------- #
################################################################################################################


################################################################################################################
# -------------------------------------------- USER MANAGEMENT START------------------------------------------- #
################################################################################################################

@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class UserManagement(TemplateView):
    """View for managing the users in the system"""

    template_name = "dashboard/user-management.html"

    def get_context_data(self, **kwargs):
        context = super(UserManagement, self).get_context_data(**kwargs)
        context['display_template_label'] = "App Users"
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        users = BaseProfile.objects.filter(user_type='app_user').order_by('-id')
        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False

        for user in users:
            rating = get_rating(user)
            setattr(user, 'rating', round(rating, 1))
            peru_timezone = pytz.timezone('America/Lima')
            date_joined = user.user.date_joined.astimezone(peru_timezone)
            added_time = str(date_joined.strftime('%d-%m-%Y %I:%M %p')) + "\n"
            setattr(user, 'date_joined', added_time)

        context['users'] = users
        return context


#
# @method_decorator((login_required, verify_permission(level='None')), name='dispatch')
# class BlockUnblockUser(View):
#     """
#     View for blocking and unblocking users
#     """
#
#     def get(self, request):
#         user_id = request.GET.get('user_id', '')
#         try:
#             user_obj = BaseProfile.objects.get(id=user_id)
#
#             if user_obj.status == 'blocked':
#                 user_obj.status = "active"
#                 user_obj.user.is_active = True
#                 user_obj.save()
#                 user_obj.user.save()
#                 messages.success(request,
#                                  request.lbl_user_unblocked + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)
#
#             elif user_obj.status == 'active':
#                 user_obj.status = "blocked"
#                 user_obj.save()
#                 user_obj.user.is_active = False
#                 user_obj.user.save()
#                 messages.success(request,
#                                  request.lbl_user_blocked + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)
#
#         except BaseProfile.DoesNotExist:
#             messages.error(request, "Invalid user details")
#         return redirect(reverse('dashboard:manage-users'))


################################################################################################################
# -------------------------------------------- USER MANAGEMENT END------------------------------------------- #
################################################################################################################


################################################################################################################
# -------------------------------------------- FLEET MANAGEMENT START------------------------------------------- #
################################################################################################################

@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class FleetManagement(TemplateView):
    """View for managing the fleets in the system"""

    template_name = "dashboard/fleet-management.html"

    def get_context_data(self, **kwargs):
        context = super(FleetManagement, self).get_context_data(**kwargs)
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        status = kwargs['status']
        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False
        if status == 'not_verified':
            context['display_template_label'] = self.request.lbl_new_registrations
        elif status == 'active':
            context['display_template_label'] = self.request.lbl_fleet_approved
        elif status == 'blocked':
            context['display_template_label'] = self.request.lbl_fleet_blocked
        if self.request.user.is_superuser:
            if status == 'all':
                context['users'] = BaseProfile.objects.filter(user_type='fleet_admin').order_by('-id')
        else:
            context['users'] = BaseProfile.objects.filter(user_type='fleet_admin', status=status,
                                                          city=admin_profile.city).order_by('-id')
        return context


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class ApproveUser(View):
    """
    View for Approving Fleets
    """

    def get(self, request):
        user_id = request.GET.get('user_id', '')
        user_type = 'driver'
        try:
            user_obj = BaseProfile.objects.get(id=user_id)
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            if admin_profile.user_type == 'fleet_admin':
                user_obj.status = "fleet_verified"
                user_obj.save()
                messages.success(request,
                                 request.lbl_partner_approved + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)
            else:
                if user_obj.status == 'not_verified' or user_obj.status == 'fleet_verified':
                    user_obj.status = "active"
                    try:
                        vehicle_obj = VehicleDetails.objects.get(driver_id=user_obj)
                        vehicle_obj.status = "approved"
                    except:
                        pass
                    user_obj.approved_by = admin_profile
                    user_obj.approved_on = timezone.now()
                    user_obj.user.is_active = True
                    user_type = user_obj.user_type
                    user_obj.save()
                    user_obj.user.save()

                    # Sending notification email to user
                    subject = ''
                    ctx = {}
                    if user_type == 'fleet_admin':
                        subject = request.lbl_fleet_reg_approved
                        ctx = {
                            "lbl_dear_user": request.lbl_dear_user + " " + user_obj.user.first_name + " " + user_obj.user.last_name,
                            "lbl_account_approved": request.lbl_fleet_account_with_email + " " + user_obj.user.username + " " + request.lbl_account_approved,
                            "lbl_muberz_team": request.lbl_muberz_team,
                        }
                    elif user_type == 'driver':
                        subject = request.lbl_partner_reg_approved
                        ctx = {
                            "lbl_dear_user": request.lbl_dear_user + " " + user_obj.user.first_name + " " + user_obj.user.last_name,
                            "lbl_account_approved": request.lbl_partner_account + " " + request.lbl_account_approved,
                            "lbl_muberz_team": request.lbl_muberz_team,
                        }

                    content = get_template("dashboard/email-templates/account_verified.html").render(ctx)
                    threading.Thread(target=send_template_email, args=(subject, content, [user_obj.user.email])).start()
                    threading.Thread(target=send_sms_twilio,
                                     args=(
                                         str(user_obj.user.username),
                                         'Hi Greetings, Your Muberz partner account has been approved. Welcome aboard!')).start()
                    if user_obj.fleet_id:
                        # MAIL TO SENT FLEET FOR DRIVER APPROVAL
                        subject = request.lbl_fleet_truck_approved_heading
                        dic = {
                            "lbl_dear_user": request.lbl_dear_user + " " + user_obj.fleet_id.user.get_full_name(),
                            "lbl_account_approved": request.lbl_fleet_truck_approved.format(user_obj.user.username),
                            "lbl_muberz_team": request.lbl_muberz_team,
                        }
                        content = get_template("dashboard/email-templates/account_verified.html").render(dic)
                        threading.Thread(target=send_template_email,
                                         args=(subject, content, [user_obj.fleet_id.user.email])).start()

                    if user_type == 'fleet_admin':
                        messages.success(request,
                                         request.lbl_fleet_approved + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)
                    elif user_type == 'driver':
                        messages.success(request,
                                         request.lbl_partner_approved + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)

        except BaseProfile.DoesNotExist:
            messages.error(request, "Invalid user details")
        if user_type == 'fleet_admin':
            return redirect('dashboard:manage-fleets', 'active')
        elif user_type == 'driver':
            return redirect('dashboard:manage-partners', 'active')
        return redirect('dashboard:manage-fleets', 'active')


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class DeleteUser(View):
    """
    View for Deleteing Fleets
    """

    def get(self, request):
        user_id = request.GET.get('user_id', '')
        user_type = 'driver'
        message = ''
        try:
            user_obj = User.objects.get(id=user_id)
            user_obj.delete()
            messages.success(request, "Deleted Successfully")
        except:
            messages.error(request, "Invalid user details")
            return redirect(request.META['HTTP_REFERER'])
        if user_type == 'fleet_admin':
            return redirect('dashboard:manage-fleets', 'active')
        elif user_type == 'driver':
            return redirect('dashboard:manage-partners', 'active')
        else:
            return redirect(request.META['HTTP_REFERER'])


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class BlockUnblockUser(View):
    """
    View for blocking and unblocking users
    """

    def get(self, request):
        user_id = request.GET.get('user_id', '')
        user_type = 'driver'
        try:
            user_obj = BaseProfile.objects.get(id=user_id)
            user_type = user_obj.user_type
            if user_obj.status == 'blocked':
                user_obj.status = "active"
                user_obj.user.is_active = True
                user_obj.save()
                user_obj.user.save()

                if user_type == 'fleet_admin':
                    user = request.lbl_fleet_unblocked

                    # UNBLOCK ALL DRIVERS THAT WE SUSPENDED WHILE BLOCKING
                    drivers = BaseProfile.objects.filter(fleet_id=user_obj, status='suspended')
                    for driver in drivers:
                        if not driver.user.is_active:
                            driver.status = 'active'
                            driver.user.is_active = True
                            driver.user.save()
                            driver.save()

                elif user_type == 'driver':
                    user = request.lbl_partner_unblocked
                else:
                    user = request.lbl_fleet_unblocked
                messages.success(request, user + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)

            elif user_obj.status == 'active':
                user_obj.status = "blocked"
                user_obj.save()
                user_obj.user.is_active = False
                user_obj.user.save()
                if user_type == 'fleet_admin':
                    user = request.lbl_fleet_blocked
                    # BLOCK ALL DRIVERS UNDER THE FLEET
                    drivers = BaseProfile.objects.filter(fleet_id=user_obj)
                    for driver in drivers:
                        if driver.user.is_active:
                            driver.status = 'suspended'
                            driver.user.is_active = False
                            driver.user.save()
                            driver.save()
                            # DELETED ACCESS TOKENS FOR DRIVERS
                            SingleAccessTokenManagement.delete_access_token_permission(driver.user)
                elif user_type == 'driver':
                    user = request.lbl_partner_blocked
                    # DELETED ACCESS TOKENS FOR DRIVERS
                    SingleAccessTokenManagement.delete_access_token_permission(user_obj.user)

                else:
                    user = request.lbl_fleet_blocked
                messages.success(request, user + " %s" % user_obj.user.first_name + " " + user_obj.user.last_name)

        except BaseProfile.DoesNotExist:
            messages.error(request, "Invalid user details")
        if user_type == 'fleet_admin':
            return redirect(request.META['HTTP_REFERER'])
        elif user_type == 'driver':
            return redirect(request.META['HTTP_REFERER'])
        else:
            return redirect(request.META['HTTP_REFERER'])


################################################################################################################
# -------------------------------------------- FLEET MANAGEMENT END------------------------------------------- #
################################################################################################################

################################################################################################################
# -------------------------------------------- PARTNER MANAGEMENT START------------------------------------------- #
################################################################################################################

#
# def verify_mobile(request):
#     if request.method == "GET":
#         mobile_number = request.GET.get('mobile_number', '')
#         status = 400
#         result_data = ''
#         if mobile_number is not None:
#             if User.objects.filter(username=mobile_number).exists():
#                 result_data = "user already exist"
#                 status = 400
#             else:
#                 user_obj = User.objects.create_user(username=mobile_number)
#                 user_profile = BaseProfile.objects.create(user=user_obj, user_type='driver', status='not_verified')
#                 user_obj.status = 'active'
#                 user_obj.save()
#                 user_profile.save()
#                 user_profile.set_otp()
#                 otp_text = user_profile.raw_otp + " is your verification code for Muberz User App."
#                 if send_sms(mobile_number, otp_text) == 200:
#                     result_data = "otp sent"
#                     status = 200
#                 else:
#                     result_data = 'lbl_otp_resent'
#                     status = 400
#         else:
#             result_data = "otp resend"
#             status = 400
#
#         return JsonResponse({"message": result_data, "status": status}, safe=False)
#
#
# def verify_otp(request):
#     if request.method == "GET":
#         mobile_number = request.GET.get('mobile_number', '')
#         otp = request.GET.get('otp', '')
#         status = 400
#         result_data = ''
#         if mobile_number is not None:
#             if User.objects.filter(username=mobile_number).exists():
#                 result_data = "user already exist"
#                 status = 400
#             else:
#                 user_obj = User.objects.create_user(username=mobile_number)
#                 user_profile = BaseProfile.objects.create(user=user_obj, user_type='driver', status='not_verified')
#                 user_obj.status = 'active'
#                 user_obj.save()
#                 user_profile.save()
#                 user_profile.set_otp()
#                 otp_text = user_profile.raw_otp + " is your verification code for Muberz User App."
#                 if send_sms(mobile_number, otp_text) == 200:
#                     result_data = "otp sent"
#                     status = 200
#                 else:
#                     result_data = 'lbl_otp_resent'
#                     status = 400
#         else:
#             result_data = "otp resend"
#             status = 400
#
#         return JsonResponse({"message": result_data, "status": status}, safe=False)


@method_decorator((login_required, verify_permission(level='none')), name='dispatch')
class AddPartner(TemplateView):
    """
    View for adding new partner's information
    """

    template_name = "dashboard/add-partner.html"

    def get_context_data(self, **kwargs):
        context = super(AddPartner, self).get_context_data(**kwargs)
        return context

    @staticmethod
    def post(request):
        name = request.POST.get('name')
        email = request.POST.get('email', '')
        mobile_number = request.POST.get('mobile_number', '')
        vehicle_volume = request.POST.get('vehicle_volume', '')
        registration_number = request.POST.get('registration_number', '')
        profile_pic = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image1', '')))
        driver_license = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image2', '')))
        commercial_insurance = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image3', '')))
        registration_certificate = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image4', '')))
        fitness_certificate = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image5', '')))
        tax_certificate = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image6', '')))

        if name and mobile_number and vehicle_volume and registration_number is not None:
            try:
                if not User.objects.filter(username=mobile_number).exists():
                    admin_profile = BaseProfile.objects.get(user=request.user)
                    signup_flag = True
                    user_obj = User.objects.create_user(username=mobile_number, first_name=name, email=email)
                    user_profile = BaseProfile.objects.create(user=user_obj, user_type='driver', status='not_verified',
                                                              fleet_id=admin_profile)

                    user_profile.deposit_needed = get_security_deposit(vehicle_volume, admin_profile.city)
                    user_profile.city = admin_profile.city
                    user_profile.is_new_user = True
                    user_profile.save()

                    if profile_pic != '':
                        user_profile.profile_pic = str(profile_pic)
                        user_profile.save()

                    vehicle_profile, created = VehicleDetails.objects.get_or_create(driver_id=user_profile,
                                                                                    added_by=admin_profile)

                    vehicle_profile.vehicle_volume = vehicle_volume
                    vehicle_profile.reg_no = registration_number
                    vehicle_profile.save()
                    if fitness_certificate != '':
                        try:
                            attach_obj = Attachments.objects.get(doc_type='fitness_certificate', driver_id=user_profile)
                            attach_obj.attachment = fitness_certificate
                            attach_obj.save()
                        except Attachments.DoesNotExist:
                            attach_obj = Attachments.objects.create(attachment=fitness_certificate,
                                                                    doc_type='fitness_certificate',
                                                                    driver_id=user_profile)
                            attach_obj.save()
                    if tax_certificate != '':
                        try:
                            attach_obj = Attachments.objects.get(doc_type='tax_certificate', driver_id=user_profile)
                            attach_obj.attachment = tax_certificate
                            attach_obj.save()
                        except Attachments.DoesNotExist:
                            attach_obj = Attachments.objects.create(attachment=tax_certificate,
                                                                    doc_type='tax_certificate',
                                                                    driver_id=user_profile)
                            attach_obj.save()

                    if driver_license != '':
                        try:
                            attach_obj = Attachments.objects.get(doc_type='driver_license', driver_id=user_profile)
                            attach_obj.attachment = driver_license
                            attach_obj.save()
                        except Attachments.DoesNotExist:
                            attach_obj = Attachments.objects.create(attachment=driver_license,
                                                                    doc_type='driver_license',
                                                                    driver_id=user_profile)
                            attach_obj.save()

                    if commercial_insurance != '':
                        try:
                            attach_obj = Attachments.objects.get(doc_type='commercial_insurance',
                                                                 driver_id=user_profile)
                            attach_obj.attachment = commercial_insurance
                            attach_obj.save()
                        except Attachments.DoesNotExist:
                            attach_obj = Attachments.objects.create(attachment=commercial_insurance,
                                                                    doc_type='commercial_insurance',
                                                                    driver_id=user_profile)
                            attach_obj.save()

                    if registration_certificate != '':
                        try:
                            attach_obj = Attachments.objects.get(doc_type='registration_certificate',
                                                                 driver_id=user_profile)
                            attach_obj.attachment = registration_certificate
                            attach_obj.save()
                        except:
                            attach_obj = Attachments.objects.create(attachment=registration_certificate,
                                                                    doc_type='registration_certificate',
                                                                    driver_id=user_profile)
                            attach_obj.save()

                    # GET NO OF ASSISTANTS
                    no_assistants = get_no_assistant(vehicle_volume, user_profile.city)

                    vehicle_profile.no_assistants = no_assistants
                    vehicle_profile.save()
                    user_profile.save()
                    user_profile.user.save()
                    messages.success(request, request.lbl_partner_details_added)
                    return redirect(reverse('dashboard:edit-partner', kwargs={"partner_id": user_profile.id}))
                else:
                    messages.error(request, request.lbl_another_mobile_exists)
                    return redirect(reverse('dashboard:add-partner'))
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
                return redirect(reverse('dashboard:add-partner'))

        return redirect(reverse('dashboard:add-partner'))


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ListPartners(TemplateView):
    """
    View for listing Partners
    """
    template_name = 'dashboard/list_partners.html'

    def get_context_data(self, **kwargs):
        context = super(ListPartners, self).get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            if self.request.user.is_superuser:
                vehicles = VehicleDetails.objects.all()
            else:
                vehicles = VehicleDetails.objects.filter(driver_id__fleet_id=admin_profile)
            for veh in vehicles:
                peru_timezone = pytz.timezone('America/Lima')
                if veh.driver_id.approved_on:
                    approved_on = veh.driver_id.approved_on.astimezone(peru_timezone)
                    approved_on = str(approved_on.strftime('%d-%m-%Y %I:%M %p')) + "\n"
                    setattr(veh, 'approved_on', approved_on)

            context['vehicles'] = vehicles
            context['display_template_label'] = self.request.lbl_partner_registrations
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)
        return context


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ApproveFleetDriver(View):
    """View for approving fleet driver"""

    def get(self, request, *args, **kwargs):
        driver_id = kwargs['driver_id']

        if driver_id != "":
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                driver = BaseProfile.objects.get(id=driver_id, user_type="driver", fleet_id__user=request.user)
                truck_assistants_count = Assistants.objects.filter(driver_id=driver, deleted=False).count()

                if driver.user.first_name == "":
                    raise ValidationError("Partner doesn't have a proper name")
                if driver.user.email != "":
                    try:
                        validate_email(driver.user.email)
                    except ValidationError:
                        raise ValidationError("Partner doesn't have a valid email address")

                if (len(driver.user.username) < 9) or (not driver.user.username.lstrip("+").isdigit()):
                    raise ValidationError("Partner doesn't have a valid phone number")

                if driver.profile_pic == "":
                    raise ValidationError("Partner doesn't have a profile pic")

                if driver.vehicledetails.reg_no == "":
                    raise ValidationError("Partner truck doesn't have registration number added")

                if driver.vehicledetails.vehicle_volume == 0:
                    raise ValidationError("Partner truck doesn't have sufficient volume")

                try:
                    crew_obj = TruckCrew.objects.get(capacity_from__lte=driver.vehicledetails.vehicle_volume,
                                                     capacity_to__gte=driver.vehicledetails.vehicle_volume,
                                                     added_by__city=driver.city)

                    if truck_assistants_count < crew_obj.loading_peoples:
                        raise ValidationError("Partner should have %s assistants" % crew_obj.loading_peoples)

                except TruckCrew.DoesNotExist:
                    raise ValidationError("Truck crew details are missing. Please contact admin")

                attachments_query = Attachments.objects.filter(driver_id=driver).exclude(attachment="")
                if not attachments_query.filter(doc_type="fitness_certificate").exists():
                    raise ValidationError("Partner doesn't have a fitness certificate")
                if not attachments_query.filter(doc_type="tax_certificate").exists():
                    raise ValidationError("Partner doesn't have a tax certificate")
                if not attachments_query.filter(doc_type="driver_license").exists():
                    raise ValidationError("Partner doesn't have a driver license")
                if not attachments_query.filter(doc_type="commercial_insurance").exists():
                    raise ValidationError("Partner doesn't have a commercial insurance")
                if not attachments_query.filter(doc_type="registration_certificate").exists():
                    raise ValidationError("Partner doesn't have a registration certificate")

                driver.status = "fleet_verified"
                if not driver.city:
                    driver.city = admin_profile.city
                driver.approved_by = admin_profile
                driver.approved_on = timezone.now()
                driver.is_new_user = False
                driver.save()
                messages.success(request, "Partner has been activated. Need City Admin's Approval also")

            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)

            except ValidationError as e:
                messages.error(request, e.args[0])

        try:
            return redirect(reverse('dashboard:edit-partner', kwargs={"partner_id": driver.id}))
        except:
            return redirect("dashboard:list-partners")


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class EditPartner(TemplateView):
    """View for Update to  Partner"""

    template_name = "dashboard/edit-partner.html"

    def get_context_data(self, **kwargs):
        context = super(EditPartner, self).get_context_data(**kwargs)
        partner_id = kwargs['partner_id']
        try:
            driver_data = BaseProfile.objects.get(id=partner_id)
            # Fetching editable user data
            veh_data = VehicleDetails.objects.get(driver_id=driver_data)
            context['driver_data'] = driver_data
            context['attachments'] = Attachments.objects.filter(driver_id=veh_data.driver_id)
            context['veh_data'] = veh_data
            context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
            serviceable_areas = ServiceableArea.objects.filter(driver_id=veh_data.driver_id)
            assistants = Assistants.objects.filter(driver_id=driver_data, deleted=False)
            for area in serviceable_areas:
                location_name = get_location_name(area.latitude, area.longitude)
                setattr(area, 'location_name', location_name)
            context['assistants'] = assistants
            context['serviceable_areas'] = serviceable_areas
            context["assistants_needed_count"] = "N/A"

            try:
                crew_obj = TruckCrew.objects.get(capacity_from__lte=veh_data.vehicle_volume,
                                                 capacity_to__gte=veh_data.vehicle_volume,
                                                 added_by__city=driver_data.city)

                context["assistants_needed_count"] = crew_obj.loading_peoples

            except TruckCrew.DoesNotExist:
                messages.error(self.request, "Truck crew details are missing. Please contact admin")

        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)
        except VehicleDetails.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)

        return context

    def post(self, request, **kwargs):
        # name = request.POST.get('name')
        # email = request.POST.get('email', '')
        # mobile_number = request.POST.get('mobile_number', '')
        # vehicle_volume = request.POST.get('vehicle_volume', '')
        profile_pic = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image1', '')))
        driver_license = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image2', '')))
        commercial_insurance = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image3', '')))
        registration_certificate = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image4', '')))
        fitness_certificate = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image5', '')))
        tax_certificate = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image6', '')))
        partner_id = kwargs['partner_id']

        try:
            user_profile = BaseProfile.objects.get(id=partner_id)

            if request.POST.get('image1', '') != '':
                user_profile.profile_pic = str(profile_pic)
                user_profile.save()

            if request.POST.get('image5', '') != '':
                try:
                    attach_obj = Attachments.objects.get(doc_type='fitness_certificate', driver_id=user_profile)
                    attach_obj.attachment = fitness_certificate
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=fitness_certificate,
                                                            doc_type='fitness_certificate',
                                                            driver_id=user_profile)
                    attach_obj.save()
            if request.POST.get('image6', '') != '':
                try:
                    attach_obj = Attachments.objects.get(doc_type='tax_certificate', driver_id=user_profile)
                    attach_obj.attachment = tax_certificate
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=tax_certificate,
                                                            doc_type='tax_certificate',
                                                            driver_id=user_profile)
                    attach_obj.save()

            if request.POST.get('image2', '') != '':
                try:
                    attach_obj = Attachments.objects.get(doc_type='driver_license', driver_id=user_profile)
                    attach_obj.attachment = driver_license
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=driver_license,
                                                            doc_type='driver_license',
                                                            driver_id=user_profile)
                    attach_obj.save()

            if request.POST.get('image3', '') != '':
                try:
                    attach_obj = Attachments.objects.get(doc_type='commercial_insurance',
                                                         driver_id=user_profile)
                    attach_obj.attachment = commercial_insurance
                    attach_obj.save()
                except Attachments.DoesNotExist:
                    attach_obj = Attachments.objects.create(attachment=commercial_insurance,
                                                            doc_type='commercial_insurance',
                                                            driver_id=user_profile)
                    attach_obj.save()

            if request.POST.get('image4', '') != '':
                try:
                    attach_obj = Attachments.objects.get(doc_type='registration_certificate',
                                                         driver_id=user_profile)
                    attach_obj.attachment = registration_certificate
                    attach_obj.save()
                except:
                    attach_obj = Attachments.objects.create(attachment=registration_certificate,
                                                            doc_type='registration_certificate',
                                                            driver_id=user_profile)
                    attach_obj.save()

            messages.success(request, request.lbl_basic_details_updated)

        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)

        except VehicleDetails.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)

        return redirect("dashboard:edit-partner", partner_id)


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class DeletePartner(View):
    """View for deleting a driver/truck"""

    def get(self, request, *args, **kwargs):

        partner_id = kwargs["partner_id"]
        if partner_id != "":
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                if admin_profile.user_type == "fleet_admin":
                    params = {"fleet_id": admin_profile}
                elif admin_profile.user_type == "admin_user":
                    params = {"city": admin_profile}
                else:
                    messages.error(request, "You have no permission to do this action")
                    return redirect("dashboard:dashboard-home-page")
                partner = BaseProfile.objects.get(id=partner_id, user_type="driver", **params)
                partner.user.delete()
                messages.success(request, "We have successfully deleted your truck")

            except BaseProfile.DoesNotExist:
                messages.error(request, "Invalid truck Id")

        else:
            messages.error(request, "Please provide valid data")

        return redirect("dashboard:list-partners")


def update_serviceable_area(request):
    if request.method == "GET":
        user_id = request.GET.get('user_id', '')
        latitude = request.GET.get('latitude', '')
        longitude = request.GET.get('longitude', '')
        result = {}
        try:
            user_profile = BaseProfile.objects.get(id=user_id)
            servobj_obj = ServiceableArea(
                latitude=latitude, longitude=longitude, driver_id=user_profile)
            servobj_obj.save()
            location_name = get_location_name(latitude, longitude)
            result_data = 200
            print(location_name)
            result = {
                "result_data": result_data,
                "location_name": location_name
            }

        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)
        return JsonResponse(result, safe=False)


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class PartnerManagement(TemplateView):
    """View for managing the Partner in the system"""

    template_name = "dashboard/partner-management.html"

    def get_context_data(self, **kwargs):
        context = super(PartnerManagement, self).get_context_data(**kwargs)
        status = kwargs['status']
        context['display_approved_on'] = True
        if status == 'not_verified':
            context['display_template_label'] = self.request.lbl_new_partner_registrations
            context['display_approved_on'] = False
        elif status == 'active':
            context['display_template_label'] = self.request.lbl_partner_approved_regns
            context['display_approved_on'] = True
        elif status == 'blocked':
            context['display_template_label'] = self.request.lbl_partner_blocked_regns
            context['display_approved_on'] = False

        admin_profile = BaseProfile.objects.get(user=self.request.user)

        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False

        if status == 'not_verified':  # IF NOT VERIFIED
            vehicles = VehicleDetails.objects.filter(driver_id__user_type='driver').order_by('-id')
            if admin_profile.user_type == 'fleet_admin':
                vehicles = vehicles.filter(driver_id__fleet_id=admin_profile, driver_id__status=status)
            else:
                vehicles = vehicles.filter(driver_id__city=admin_profile.city)
                vehicles1 = vehicles.filter(driver_id__fleet_id__isnull=False, driver_id__status='fleet_verified')
                vehicles2 = vehicles.filter(driver_id__fleet_id__id__isnull=True, driver_id__status='not_verified')
                vehicles = vehicles1 | vehicles2
        else:  # IF BLOCKED OR ACTIVE
            vehicles = VehicleDetails.objects.filter(driver_id__user_type='driver', driver_id__status=status,
                                                     driver_id__city=admin_profile.city).order_by(
                '-id')
            if admin_profile.user_type == 'fleet_admin':
                vehicles = vehicles.filter(driver_id__fleet_id=admin_profile)

        for veh in vehicles:
            rating = get_rating(veh.driver_id)
            setattr(veh, 'rating', round(rating, 1))
            peru_timezone = pytz.timezone('America/Lima')
            if veh.driver_id.approved_on:
                approved_on = veh.driver_id.approved_on.astimezone(peru_timezone)
                approved_on = str(approved_on.strftime('%d-%m-%Y %I:%M %p')) + "\n"
                setattr(veh, 'approved_on', approved_on)

        context['vehicles'] = vehicles
        return context


class PartnerDetailsApi(TemplateView):
    """
    View for Partner Details
    """
    template_name = 'dashboard/partner-details.html'

    def get_context_data(self, **kwargs):
        context = super(PartnerDetailsApi, self).get_context_data(**kwargs)
        vehicle_id = kwargs['vehicle_id']

        try:
            veh_data = VehicleDetails.objects.get(id=vehicle_id)
            rating = get_rating(veh_data.driver_id)
            setattr(veh_data, 'rating', round(rating, 1))
            context['veh_data'] = veh_data
            context['attachments'] = Attachments.objects.filter(driver_id=veh_data.driver_id)
            serviceable_areas = ServiceableArea.objects.filter(driver_id=veh_data.driver_id)
            for area in serviceable_areas:
                location_name = get_location_name(area.latitude, area.longitude)
                setattr(area, 'location_name', location_name)

            context['serviceable_areas'] = serviceable_areas
            context['assistants'] = Assistants.objects.filter(driver_id=veh_data.driver_id, deleted=False)
            context['security_dep'] = get_security_deposit(veh_data.vehicle_volume, veh_data.driver_id.city)
            # context['actions'] = actions
            admin_profile = BaseProfile.objects.get(user=self.request.user)

            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False

        except BaseProfile.DoesNotExist:
            # Reset key is not valid or it expired
            context['valid_reset_key'] = False
        except VehicleDetails.DoesNotExist:
            # Reset key is not valid or it expired
            context['valid_reset_key'] = False
        return context

    def post(self,request,vehicle_id):
        vehicle_height = request.POST.get('vehicle_height',0)
        vehicle = VehicleDetails.objects.get(id=vehicle_id)
        vehicle.vehicle_height = vehicle_height
        vehicle.save()
        return redirect("dashboard:partner-view",vehicle_id=vehicle_id)
################################################################################################################
# -------------------------------------------- PARTNER MANAGEMENT ENDtran------------------------------------------- #
################################################################################################################


################################################################################################################
# -------------------------------------------- DAMAGE REPORT MANAGEMENT START --------------------------------- #
################################################################################################################


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class DamageReportManagement(TemplateView):
    """View for managing the Partner in the system"""

    template_name = "dashboard/damage-report-management.html"

    def get_context_data(self, **kwargs):
        context = super(DamageReportManagement, self).get_context_data(**kwargs)
        context['display_template_label'] = self.request.lbl_damages_reported

        admin_profile = BaseProfile.objects.get(user=self.request.user)
        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False

        transfer_ids = Damage.objects.all().values_list('transfer_id').distinct()
        transfers = []
        if self.request.user.is_superuser:
            transfers = Transfer.objects.filter(id__in=transfer_ids, status='completed').order_by('-id')
        elif admin_profile.user_type == 'fleet_admin':
            transfers = Transfer.objects.filter(id__in=transfer_ids, status='completed',
                                                driver__fleet_id=admin_profile).order_by('-id')
        elif admin_profile.user_type == 'admin_user':
            transfers = Transfer.objects.filter(id__in=transfer_ids, status='completed',
                                                city=admin_profile.city).order_by('-id')
        logger_me.debug(transfers)
        peru_timezone = pytz.timezone('America/Lima')
        for transfer in transfers:
            try:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer, loc_type='pickup')
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer, loc_type='drop')

                logger_me.debug(transfer)
                damage_obj = Damage.objects.filter(transfer_id=transfer).aggregate(damage_count=Sum("count"))
                setattr(transfer, 'no_damaged_items', damage_obj['damage_count'])
                setattr(transfer, 'transfer_pickup', transfer_pickup)
                setattr(transfer, 'transfer_drop', transfer_drop)

                transfer_on = transfer.transfer_on.astimezone(peru_timezone)
                added_time = str(transfer_on.strftime('%d-%m-%Y %I:%M %p'))
                setattr(transfer, 'added_time', added_time)
            except TransferLocation.DoesNotExist:
                pass
        context['transfers'] = transfers
        return context


class DamageDetailsApi(TemplateView):
    """
    View for Damage Details
    """
    template_name = 'dashboard/damage-details.html'

    def get_context_data(self, **kwargs):
        context = super(DamageDetailsApi, self).get_context_data(**kwargs)
        transfer_id = kwargs['transfer_id']
        commodity_list = []
        try:
            transfer_obj = Transfer.objects.get(id=transfer_id)
            peru_timezone = pytz.timezone('America/Lima')
            transfer_on = transfer_obj.transfer_on.astimezone(peru_timezone)
            added_time = str(transfer_on.strftime('%d-%m-%Y %I:%M %p'))
            setattr(transfer_obj, 'added_time', added_time)

            context['transfer_data'] = transfer_obj
            try:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='pickup')
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer_obj, loc_type='drop')

                commodities = TransferCommodity.objects.filter(transfer_loc_id=transfer_pickup).values(
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
                            partial = damages_reported.filter(damage_type='partial').aggregate(
                                partial_count=Sum("count"))
                            full = damages_reported.filter(damage_type='full').aggregate(full_count=Sum("count"))
                            stolen = damages_reported.filter(damage_type='stolen').aggregate(stolen_count=Sum("count"))
                            commodity_dict['partial'] = partial['partial_count']
                            commodity_dict['full'] = full['full_count']
                            commodity_dict['stolen'] = stolen['stolen_count']
                            commodity_dict['photos'] = DamagePhotos.objects.filter(transfer_id=transfer_obj,
                                                                                   item_id=comm_obj)
                            commodity_list.append(commodity_dict)
                    except Commodity.DoesNotExist:
                        pass
                context['damage_description'] = DamageDescriptions.objects.filter(transfer_id=transfer_obj)
                context['damages'] = commodity_list
                context['transfer_pickup'] = transfer_pickup.location_name
                context['transfer_drop'] = transfer_drop.location_name
                # TO DISABLE ACTION PERMISSION FOR OPERATORS
                admin_profile = BaseProfile.objects.get(user=self.request.user)
                if admin_profile.user_type == 'operator':
                    context['disable_action'] = True
                else:
                    context['disable_action'] = False

            except TransferLocation.DoesNotExist:
                pass
            except BaseProfile.DoesNotExist:
                pass
        except Transfer.DoesNotExist:
            # Reset key is not valid or it expired
            context['valid_reset_key'] = False
        return context


def update_penalty(request):
    if request.method == "GET":
        transfer_id = request.GET.get('transfer_id', '')
        topup_amount = request.GET.get('topup_amount', '').strip()
        logger_me.debug(topup_amount)
        result_data = ''
        try:
            trans_obj = Transfer.objects.get(id=transfer_id)
            # UPDATE PENALTY ONLY AFTER 48 HOURS
            damage_timeout = timezone.now() - timedelta(hours=48)
            if trans_obj.completed_on < damage_timeout:
                trans_obj.penalty = float(topup_amount)
                trans_obj.damage_resolved = True
                trans_obj.save()
                veh_obj = VehicleDetails.objects.get(driver_id=trans_obj.driver)
                veh_obj.security_deposit -= float(topup_amount)
                veh_obj.save()

                result_data = request.lbl_penalty_added
                # MAIL NOTIFICATION TO USER
                transfer_commodities = TransferCommodity.objects.filter(
                    transfer_loc_id__transfer_id=trans_obj, transfer_loc_id__loc_type="pickup").values(
                    'item__item_name', 'need_plugged').distinct().annotate(models.Count('item'))

                transfer_locations = TransferLocation.objects.filter(
                    transfer_id=trans_obj).values('loc_type', 'location_name')

                context = {
                    "transfer": trans_obj,
                    "added_by": trans_obj.added_by,
                    "driver": trans_obj.driver.user.get_full_name(),
                    "commodities": transfer_commodities,
                    "lbl_user_name": 'User',
                    "lbl_transfer_completed_on": 'Completed On',
                    "lbl_fully_paid": 'Fully Paid',
                    "lbl_transfer_time": 'Scheduled Time',
                    "lbl_pickup": 'Pickup',
                    "lbl_drop": 'Drop',
                    "lbl_sl_no": 'Sl.No.',
                    "lbl_name": 'Name',
                    "lbl_plug_in": 'Plug In',
                    "lbl_quantity": 'Quantity',
                    "lbl_yes": 'Yes',
                    "lbl_no": 'No',
                    "lbl_thanks": 'Thanks for choosing',
                    "lbl_commodities": 'Commodities',
                    "lbl_damage_reported": 'Damage Reported',
                    "lbl_trip_amount": 'Trip Amount',
                    "lbl_damage_type": 'Damage Type',
                    "lbl_image": 'Image',
                    "lbl_deduction": " We have added a penalty of S/." + str(
                        float(topup_amount)) + " will be deducted from your security deposit."
                }
                for location in transfer_locations:
                    context[location['loc_type']] = location['location_name'] or ""
                target_timezone = pytz.timezone('America/Lima')
                completed_on = trans_obj.completed_on.astimezone(target_timezone)
                context["completed_on"] = completed_on

                commodities = TransferCommodity.objects.filter(transfer_loc_id__transfer_id=trans_obj).values(
                    'item').distinct()
                commodity_list = []
                for commodity_obj in commodities:
                    try:
                        comm_obj = Commodity.objects.get(id=commodity_obj['item'])
                        damages_reported = Damage.objects.filter(transfer_id=trans_obj, item_id=comm_obj)

                        if damages_reported.count() > 0:
                            commodity_dict = {}
                            comm_obj = Commodity.objects.get(id=commodity_obj['item'])
                            commodity_dict['id'] = comm_obj.id
                            commodity_dict['item_name'] = comm_obj.item_name
                            commodity_dict['image'] = comm_obj.image
                            partial = damages_reported.filter(damage_type='partial').aggregate(
                                partial_count=Sum("count"))
                            full = damages_reported.filter(damage_type='full').aggregate(full_count=Sum("count"))
                            stolen = damages_reported.filter(damage_type='stolen').aggregate(stolen_count=Sum("count"))
                            commodity_dict['partial'] = partial['partial_count']
                            commodity_dict['full'] = full['full_count']
                            commodity_dict['stolen'] = stolen['stolen_count']
                            commodity_dict['photos'] = DamagePhotos.objects.filter(transfer_id=trans_obj,
                                                                                   item_id=comm_obj)
                            commodity_list.append(commodity_dict)
                    except Commodity.DoesNotExist:
                        pass
                context['damage_description'] = DamageDescriptions.objects.filter(transfer_id=trans_obj)
                context['damages'] = commodity_list

                message = get_template('dashboard/email-templates/penalty-notification-mail.html').render(context)
                # Starting a new thread for sending confirmation mail
                email_thread = Thread(
                    target=send_template_email,
                    args=('Damage Reported by the User', message, [trans_obj.driver.user.email]))
                email_thread.start()  # Starts thread
                peru_timezone = pytz.timezone('America/Lima')
                transfer_on = trans_obj.transfer_on.astimezone(peru_timezone)
                added_time = str(transfer_on.strftime('%d-%m-%Y %H:%M:%S'))
                transfer_pickup = TransferLocation.objects.get(transfer_id=trans_obj, loc_type='pickup')
                transfer_drop = TransferLocation.objects.get(transfer_id=trans_obj, loc_type='drop')
                threading.Thread(target=send_sms_twilio,
                                 args=(
                                     str(trans_obj.driver.user.username),
                                     'Hi Greetings, A damage has been reported by the user against the trip on ' + str(
                                         added_time) + ' from ' + transfer_pickup.location_name + ' to ' + transfer_drop.location_name + '. We have added a penalty of S/.' + str(
                                         float(
                                             topup_amount)) + ', will be deducted from your security deposit.')).start()

            else:
                result_data = request.lbl_add_penalty_after_48_hours
        except Transfer.DoesNotExist:
            result_data = request.lbl_invalid_transfer
        except VehicleDetails.DoesNotExist:
            result_data = request.lbl_invalid_user
        return JsonResponse(result_data, safe=False)


################################################################################################################
# -------------------------------------------- DAMAGE REPORT MANAGEMENT END --------------------------------- #
################################################################################################################


################################################################################################################
# --------------------------------------------SYSTEM DOCUMENTS START------------------------------------------ #
################################################################################################################


@method_decorator((login_required, verify_permission(level='superuser')), name='dispatch')
class ListDocuments(TemplateView):
    """
    View for listing admin's
    """
    template_name = 'dashboard/document_list.html'

    def get_context_data(self, **kwargs):
        context = super(ListDocuments, self).get_context_data(**kwargs)
        # Getting all the admin's except the current logged in admin
        document_list = Documents.objects.all()
        context['document_list'] = document_list
        dict = list(Documents.TYPES)
        context['doc_type_list'] = dict
        context['languages'] = list(Documents.LANGUAGE)
        context['app_type'] = list(Documents.APP_TYPE)
        return context


@method_decorator((login_required, verify_permission(level='superuser')), name='dispatch')
class AddDocument(View):
    """
    View for adding new document
    """

    @staticmethod
    def post(request):
        image1 = request.POST.get('image1')
        if image1:
            document = "{0}{1}".format(str(settings.BUCKET_URL), str(image1))
        document_type = request.POST.get('document_type', '')
        language = request.POST.get('language', '')
        app_type = request.POST.get('app_type', '')
        if document is not None:
            try:
                doc_obj = Documents.objects.get(document_type=document_type, language=language, app_type=app_type)
                doc_obj.document = document
                doc_obj.app_type = app_type
                doc_obj.save()
                messages.success(request, request.lbl_document_added)
            except Documents.DoesNotExist:
                doc_obj = Documents.objects.create(document_type=document_type, document=document, language=language,
                                                   app_type=app_type)
                doc_obj.save()
                messages.success(request, request.lbl_document_added)

        return redirect(reverse('dashboard:list-documents'))


################################################################################################################
# --------------------------------- SYSTEM DOCUMENTS MANAGEMENT END------------------------------------------- #
################################################################################################################


################################################################################################################
# ------------------------------------ COMMISSION MANAGEMENT START ------------------------------------------- #
################################################################################################################


@method_decorator((login_required, verify_permission(level=None)), name='dispatch')
class ListFleetAndDriverCommission(TemplateView):
    """
    View for listing commissions
    """
    template_name = 'dashboard/commission-list.html'

    def get_context_data(self, **kwargs):
        context = super(ListFleetAndDriverCommission, self).get_context_data(**kwargs)
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False

        commission_data = {}
        drivers_and_fleets = BaseProfile.objects.filter(
            user_type='driver', fleet_id=None, status='active') | BaseProfile.objects.filter(user_type='fleet_admin',
                                                                                             status='active')
        drivers_and_fleets = drivers_and_fleets.filter(city=admin_profile.city).select_related('user').order_by('-id')

        for driver in drivers_and_fleets:
            commission_data[driver.id] = driver.commission

        context['drivers_fleets'] = drivers_and_fleets
        context['commission_data'] = commission_data
        return context

    @method_decorator(disable_operator_permission(), name='dispatch')
    def post(self, request, *args, **kwargs):

        driver_id = request.POST.get('drivers', '')
        commission = request.POST.get('commission', '')
        admin_profile = BaseProfile.objects.get(user=self.request.user)

        if driver_id and commission != "":
            try:
                driver_profile = BaseProfile.objects.get(id=driver_id, city=admin_profile.city)
                driver_profile.commission = commission
                driver_profile.save(update_fields=['commission'])
                messages.success(request, "Updated commission")

            except BaseProfile.DoesNotExist:
                messages.error(request, "Invalid id")

        else:
            messages.error(request, "Please provide valid params")

        return redirect(reverse('dashboard:commission-management'))


################################################################################################################
# ------------------------------------ COMMISSION MANAGEMENT END --------------------------------------------- #
################################################################################################################


################################################################################################################
# ------------------------------------ OFFER MANAGEMENT START --------------------------------------------- #
################################################################################################################


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class OfferManagement(TemplateView):
    """View for managing the Offers in the system"""

    template_name = "dashboard/offer-mgmt.html"

    def get_context_data(self, **kwargs):
        context = super(OfferManagement, self).get_context_data(**kwargs)
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        if admin_profile.user_type == "super_user":
            context['offer_list'] = DriverOffer.objects.all().order_by('-id')
        else:
            context['offer_list'] = DriverOffer.objects.filter(added_by__city=admin_profile.city).order_by('-id')
        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False
        return context

    @method_decorator(disable_operator_permission(), name='dispatch')
    def post(self, request):
        offer_type = request.POST.get('type', '')
        trip_duration = request.POST.get('duration', 0)
        trip_count = request.POST.get('trip_count', 0)
        commission_type = request.POST.get('cashcomm', '')
        cash = request.POST.get('offer_cash', 0)
        percent = request.POST.get('offer_perc', 0)
        based_on = request.POST.get('based_on', 'daily')
        date_range = request.POST.get('daterange', '')
        applied_to = request.POST.get('applied_to', '')
        date_from, date_to = date_range.split('-')

        # YYYY-MM-DD
        if offer_type != '' and trip_duration != '' and cash != '':
            if applied_to != '':
                try:
                    from_month, from_day, from_year = date_from.split('/')
                    to_month, to_day, to_year = date_to.split('/')
                    formated_from_date = from_year.strip() + '-' + from_month.strip() + '-' + from_day.strip()
                    formated_to_date = to_year.strip() + '-' + to_month.strip() + '-' + to_day.strip()
                    driver_offer_obj = DriverOffer()
                    driver_offer_obj.offer_based_on = offer_type
                    driver_offer_obj.offer_applied_to = applied_to
                    driver_offer_obj.offer_type = commission_type
                    driver_offer_obj.total_duration = trip_duration
                    driver_offer_obj.total_trip_count = trip_count
                    driver_offer_obj.offer_commission_cash = cash
                    driver_offer_obj.offer_commission_percent = percent
                    driver_offer_obj.offer_base = based_on
                    driver_offer_obj.offer_valid_from = datetime.strptime(formated_from_date, "%Y-%m-%d").date()
                    driver_offer_obj.offer_valid_to = datetime.strptime(formated_to_date, "%Y-%m-%d").date()
                    user_object = BaseProfile.objects.get(user=request.user)
                    driver_offer_obj.added_by = user_object
                    driver_offer_obj.save()
                    message = ''
                    peru_timezone = pytz.timezone('America/Lima')
                    offer_from = driver_offer_obj.offer_valid_from.strftime('%Y-%m-%d')
                    logger_me.debug('offer_from')
                    logger_me.debug(offer_from)
                    offer_to = driver_offer_obj.offer_valid_to.strftime('%Y-%m-%d')

                    if driver_offer_obj.offer_applied_to == 'fleet':
                        users = "your drivers"
                    else:
                        users = 'you'

                    if driver_offer_obj.offer_based_on == 'time':
                        message = "If " + users + " remain more than " + str(
                            driver_offer_obj.total_duration) + " hours online "
                    else:
                        message = "if " + users + " have achieved more than " + str(
                            driver_offer_obj.total_trip_count) + " trips "
                    if offer_from == offer_to:
                        message += "on "
                        message += str(offer_from) + ", "

                    else:
                        if driver_offer_obj.offer_base == 'daily':
                            message += "daily between " + str(offer_from) + " to " + str(offer_to) + ", "
                        else:
                            message += "weekly between " + str(offer_from) + " to " + str(offer_to) + ", "

                    if driver_offer_obj.offer_type == 'cash':
                        message += " you shall receive an incentive of S./" + str(
                            driver_offer_obj.offer_commission_cash)
                    else:
                        message += " your commission amount shall be incremented by " + str(
                            driver_offer_obj.offer_commission_percent) + " %"

                    if driver_offer_obj.offer_applied_to == 'fleet':
                        fleets = BaseProfile.objects.filter(user_type='fleet_admin', status='active',
                                                            city=user_object.city)
                        context = {
                            "offer_obj": driver_offer_obj,
                            "offer_description": message,
                            "offer_heading": "Latest Offer"
                        }
                        logger_me.debug(fleets)

                        for fleet in fleets:
                            logger_me.debug('fleet id - mail sending')
                            logger_me.debug(fleet)
                            # EMAIL NOTIFICATION TO FLEET
                            context["fleet_name"] = fleet.user.first_name + " " + fleet.user.last_name
                            message = get_template('dashboard/email-templates/offer-notification-mail.html').render(
                                context)
                            # Starting a new thread for sending confirmation mail
                            email_thread = Thread(
                                target=send_template_email,
                                args=('New offer added for you', message, [fleet.user.email, 'aswathy@goodbits.in']))
                            email_thread.start()  # Starts thread
                            logger_me.debug('fleet id - mail sending end')
                    else:
                        notify_obj = create_promotion('offer', driver_offer_obj)
                        drivers = BaseProfile.objects.filter(user_type='driver', status='active', city=user_object.city,
                                                             fleet_id=None)
                        # if driver_offer_obj.offer_based_on == 'time':
                        #     message = "If you remain more than " + str(driver_offer_obj.total_duration) + "hours "
                        # else:
                        #     message = "if you have archived more than " + str(driver_offer_obj.total_trip_count) + " trips "
                        #
                        # if offer_from == offer_to:
                        #     message += " on "
                        #     message += str(offer_from) + ", "
                        #
                        # else:
                        #     if driver_offer_obj.offer_base == 'daily':
                        #         message += " daily between" + str(offer_from) + "to " + str(offer_to) + ", "
                        #     else:
                        #         message += " weekly " + str(offer_from) + "to " + str(offer_to) + ", "
                        #
                        # if driver_offer_obj.offer_type == 'cash':
                        #     message += " you shall receive an incentive of S./" + str(driver_offer_obj.offer_commission_cash)
                        # else:
                        #     message += " your commission amount shall be incremented by 20%" + str(driver_offer_obj.offer_commission_percent) + "%"
                        heading = 'You have a new offer'

                        for driver in drivers:
                            send_promotion_push_notification(driver_offer_obj, driver, message, heading, True, 0,
                                                             notify_obj)

                    messages.success(request, request.lbl_offermgmt_success)
                except:
                    messages.success(request, request.lbl_offermgmt_failed)
            else:
                messages.success(request, request.lbl_offermgmt_validation)
        else:
            messages.success(request, request.lbl_offermgmt_validation)
        return redirect(reverse('dashboard:offer-management'))


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class OfferManagementEdit(TemplateView):
    """View for managing the Offers in the system"""

    template_name = "dashboard/offer-mgmt-edit.html"

    def dispatch(self, request, *args, **kwargs):
        offer_id = kwargs['offer_id']
        context = super(OfferManagementEdit, self).dispatch(request, *args, **kwargs)
        try:
            DriverOffer.objects.get(id=offer_id)
            return context

        except:
            messages.error(request, request.lbl_invalid_offer)
            return redirect(reverse('dashboard:offer-management'))

    def get_context_data(self, **kwargs):
        offer_id = kwargs['offer_id']
        offer_obj = DriverOffer.objects.get(id=offer_id)
        context = super(OfferManagementEdit, self).get_context_data(**kwargs)
        context['offer_obj'] = offer_obj

        return context

    def post(self, request, *args, **kwargs):
        offer_id = kwargs['offer_id']
        offer_type = request.POST.get('type', '')
        trip_duration = request.POST.get('duration', 0)
        trip_count = request.POST.get('trip_count', 0)
        commission_type = request.POST.get('cashcomm', '')
        cash = request.POST.get('offer_cash', 0)
        percent = request.POST.get('offer_perc', 0)
        based_on = request.POST.get('based_on', 'daily')
        date_range = request.POST.get('daterange', '')
        applied_to = request.POST.get('applied_to', '')
        date_from, date_to = date_range.split('-')

        # YYYY-MM-DD
        if offer_type != '' and trip_duration != '' and cash != '':
            if applied_to != '':
                try:
                    from_month, from_day, from_year = date_from.split('/')
                    to_month, to_day, to_year = date_to.split('/')
                    formated_from_date = from_year.strip() + '-' + from_month.strip() + '-' + from_day.strip()
                    formated_to_date = to_year.strip() + '-' + to_month.strip() + '-' + to_day.strip()
                    driver_offer_obj = DriverOffer.objects.get(id=offer_id)
                    driver_offer_obj.offer_based_on = offer_type
                    driver_offer_obj.offer_applied_to = applied_to
                    driver_offer_obj.offer_type = commission_type
                    driver_offer_obj.total_duration = trip_duration
                    driver_offer_obj.total_trip_count = trip_count
                    driver_offer_obj.offer_commission_cash = cash
                    driver_offer_obj.offer_commission_percent = percent
                    driver_offer_obj.offer_base = based_on
                    driver_offer_obj.offer_valid_from = datetime.strptime(formated_from_date, "%Y-%m-%d").date()
                    driver_offer_obj.offer_valid_to = datetime.strptime(formated_to_date, "%Y-%m-%d").date()
                    user_object = BaseProfile.objects.get(user=request.user)
                    driver_offer_obj.added_by = user_object
                    driver_offer_obj.save()
                    messages.success(request, request.lbl_offermgmt_success)
                except:
                    messages.success(request, request.lbl_offermgmt_failed)
            else:
                messages.success(request, request.lbl_offermgmt_validation)
        else:
            messages.success(request, request.lbl_offermgmt_validation)
        return redirect(reverse('dashboard:offer-management'))


def delete_offer(request):
    if request.method == "GET":
        offer_id = request.GET.get('offer_id', '')
        try:
            obj = DriverOffer.objects.get(id=offer_id)
            obj.delete()
            result_data = request.lbl_offer_deleted

        except Discount.DoesNotExist:
            messages.error(request, request.lbl_invalid_offer)
        return JsonResponse(result_data, safe=False)


################################################################################################################
# ------------------------------------ OFFER MANAGEMENT END --------------------------------------------- #
################################################################################################################


def SaveAssistant(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id", "")
        name = request.POST.get("name", '')
        profile_pic = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image12', '')))
        id_proof = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image22', '')))
        driver_profile = BaseProfile.objects.get(id=user_id)
        assistants = Assistants(assistant_name=name, photo=profile_pic, id_proof=id_proof, driver_id=driver_profile)
        assistants.save()
        return redirect(request.META['HTTP_REFERER'])


def delete_assistant(request):
    if request.method == "GET":
        asst_id = request.GET.get('asst_id', '')
        try:
            obj = Assistants.objects.get(id=asst_id)
            obj.deleted = True
            obj.save()
            result_data = request.lbl_helper_deleted

        except Discount.DoesNotExist:
            messages.error(request, request.lbl_invalid_truck_crew)
        return JsonResponse(result_data, safe=False)


def edit_assistant(request):
    if request.method == 'POST':
        if request.method == "POST":
            user_id = request.POST.get("asst_id", "")
            name = request.POST.get("name", '')
            profile_pic = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image12', '')))
            id_proof = "{0}{1}".format(str(settings.BUCKET_URL), str(request.POST.get('image22', '')))
            assistants = Assistants.objects.get(id=user_id)
            assistants.assistant_name = name
            if str(request.POST.get('image22', '')) != '':
                assistants.id_proof = id_proof
            if str(request.POST.get('image12', '')):
                assistants.photo = profile_pic

            assistants.save()
            return redirect(request.META['HTTP_REFERER'])


################################################################################################################
# ------------------------------------ RENTAL MANAGEMENT START --------------------------------------------- #
################################################################################################################


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class RentalManagement(ListView):
    """View for managing the rentals in the system"""
    model = Transfer
    template_name = "dashboard/rental-management.html"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(RentalManagement, self).get_context_data(**kwargs)
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        # GET ALL TRANSFERS
        transfers = []
        statuses = ['not_paid']
        if admin_profile.user_type == 'fleet_admin':
            transfers = Transfer.objects.select_related('driver').filter(driver__fleet_id=admin_profile).exclude(status__in=statuses).values('pk', 'id', 'driver', 'added_by', 'total_amount', 'payment_type', 'status', 'refund_initiated', 'is_special_handling_required', 'special_handling_fee','transfer_on')
        elif admin_profile.user_type == 'admin_user' or admin_profile.user_type == 'operator':
            transfers = Transfer.objects.select_related('driver').filter(city=admin_profile.city).exclude(status__in=statuses).values('pk', 'id', 'driver', 'added_by', 'total_amount', 'payment_type', 'status', 'refund_initiated', 'is_special_handling_required', 'special_handling_fee','transfer_on')
        elif self.request.user.is_superuser:
            transfers = Transfer.objects.select_related('driver').values('pk', 'id', 'driver', 'added_by', 'total_amount', 'payment_type', 'status', 'refund_initiated', 'is_special_handling_required', 'special_handling_fee','transfer_on')


        # transfers = Transfer.objects.select_related('driver').values('pk', 'id', 'driver', 'added_by',
        #                                                                   'total_amount', 'payment_type', 'status',
        #                                                                   'refund_initiated',
        #                                                                   'is_special_handling_required',
        #                                                                   'special_handling_fee','transfer_on')
        # transfers = transfers.select_related('driver')
        if transfers:
            transfers = transfers.order_by('-id')

        for transfer in transfers:
            try:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer['id'], loc_type='pickup')
            except TransferLocation.DoesNotExist:
                transfer_pickup = None

            try:
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer['id'], loc_type='drop')
            except TransferLocation.DoesNotExist:
                transfer_drop = None

            count = Damage.objects.filter(transfer_id=transfer['id']).aggregate(count=Sum('count'))["count"]
            # setattr(transfer, 'no_damaged_items', count)
            transfer['no_damaged_items'] = count
            # setattr(transfer, 'transfer_pickup', transfer_pickup.location_name if transfer_pickup else "")
            transfer['transfer_pickup'] = transfer_pickup.location_name if transfer_pickup else ""
            # setattr(transfer, 'transfer_drop', transfer_drop.location_name if transfer_drop else "")
            transfer['transfer_drop'] = transfer_drop.location_name if transfer_drop else ""
            # user_name = BaseProfile.objects.filter(id=transfer['driver']).order_by('-id')
            transfer['added_by_user'] = BaseProfile.objects.get(id=transfer['added_by'])
            if transfer['driver']:
                transfer['driver_name'] = BaseProfile.objects.get(id=transfer['driver'])
            status = transfer['status']
            if status == 'not_paid' :
                transfer['status_value'] = 'Not Paid'
            elif status == 'active' :
                transfer['status_value'] = 'Active'
            elif status == 'accepted' :
                transfer['status_value'] = 'Accepted'
            elif status == 'cancelled' :
                transfer['status_value'] = 'Cancelled'
            elif status == 'auto_cancelled' :
                transfer['status_value'] = 'Auto Cancelled'
            elif status == 'loading' :
                transfer['status_value'] = 'Loading'
            elif status == 'in_transit' :
                transfer['status_value'] = 'In Transit'
            elif status == 'completed' :
                transfer['status_value'] = 'Completed'
            else:
                transfer['status_value'] = status

            payment_type = transfer['payment_type']
            if payment_type == 'cash' :
                transfer['payment_type_value'] = 'Cash Payment'
            elif payment_type == 'card' :
                transfer['payment_type_value'] = 'Card Payment'
            else :
                transfer['payment_type_value'] = payment_type

            peru_timezone = pytz.timezone('America/Lima')
            transfer_on = transfer['transfer_on'].astimezone(peru_timezone)
            added_time = str(transfer_on.strftime('%d-%m-%Y %I:%M %p')) + "\n"
            # setattr(transfer, 'added_time', added_time)
            transfer['added_time'] = added_time
            payout_status = False
            payout = PayoutHistory.objects.filter(driver=transfer['added_by'])
            if payout:
                if transfer in payout[0].transfers.all():
                    if payout[0].payment_processed:
                        payout_status = True
                    else:
                        payout_status = False
            # setattr(transfer, 'payout_status', payout_status)
            transfer['payout_status'] = payout_status
        context['display_template_label'] = self.request.lbl_rentals
        context['transfers'] = transfers

        paginator = Paginator(context['transfers'], self.paginate_by)
        page = self.request.GET.get('page')
        try:
            transfer_qs = paginator.page(page)
        except PageNotAnInteger:
            transfer_qs = paginator.page(1)
        except EmptyPage:
            transfer_qs = paginator.page(paginator.num_pages)
        context['transfers'] = transfer_qs

        return context


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class ViewRental(TemplateView):
    """View for displaying rental details"""
    template_name = 'dashboard/rental-details.html'

    def get_context_data(self, **kwargs):
        context = super(ViewRental, self).get_context_data(**kwargs)
        transfer_id = kwargs['transfer_id']
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False

        try:
            transfer_data = Transfer.objects.get(id=transfer_id)
            peru_timezone = pytz.timezone('America/Lima')
            transfer_on = transfer_data.transfer_on.astimezone(peru_timezone)
            added_time = str(transfer_on.strftime('%d-%m-%Y %H:%M:%S')) + "\n"
            setattr(transfer_data, 'added_time', added_time)

            context['transfer_data'] = transfer_data

            transfer_pickup = TransferLocation.objects.get(transfer_id=transfer_data, loc_type='pickup')
            transfer_drop = TransferLocation.objects.get(transfer_id=transfer_data, loc_type='drop')

            context['transfer_pickup'] = transfer_pickup
            context['transfer_drop'] = transfer_drop
            try:
                refund_obj = RefundManagement.objects.get(transfer__id=transfer_id)
                context['refund'] = refund_obj
            except:
                pass
            ratings = Rating.objects.filter(transfer_id=transfer_data)
            for each in ratings:
                if each.rating_from == transfer_data.added_by:
                    context['rating_by_user'] = each
                elif each.rating_from == transfer_data.driver:
                    context['rating_by_driver'] = each
            # Commodity List
            context['commodities'] = TransferCommodity.objects.filter(transfer_loc_id__transfer_id=transfer_data,
                                                                      transfer_loc_id__loc_type="pickup").values(
                'item__item_name', 'need_plugged', 'item__volume').distinct().annotate(models.Count('item'))
        except Transfer.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_offer)

        except TransferLocation.DoesNotExist:
            # Reset key is not valid or it expired
            context['valid_reset_key'] = False
        return context


class get_truck(ApiView):
    def get(self, request):
        dic = {}
        # GETTING ALL SERVICEABLE AREA OF THE DRIVER
        if (request.user.is_superuser):
            truck_obj_static = VehicleDetails.objects.filter(driver_id__status='active')
        else:
            userprofile = BaseProfile.objects.get(user=request.user)
            if userprofile.user_type == 'admin_user' or userprofile.user_type == 'operator':
                truck_obj_static = VehicleDetails.objects.filter(driver_id__city=userprofile.city,
                                                                 driver_id__status='active')
            elif userprofile.user_type == 'fleet_admin':
                truck_obj_static = VehicleDetails.objects.filter(driver_id__fleet_id=userprofile)
        trucks_list = []
        for trucks in truck_obj_static:
            truck_dict = {}
            truck_dict['latitude'] = trucks.driver_id.current_lat
            truck_dict['longitude'] = trucks.driver_id.current_lng
            truck_dict['driver_name'] = trucks.driver_id.user.first_name
            truck_dict['reg_no'] = trucks.reg_no
            truck_dict['mobile_number'] = trucks.driver_id.user.username
            if AccessToken.objects.filter(user=trucks.driver_id.user) and trucks.driver_id.drive_status:
                drive_status = True
            else:
                drive_status = False
            truck_dict['online_status'] = drive_status
            truck_dict['truck_status'] = trucks.driver_id.in_trip
            trucks_list.append(truck_dict)
        dic['trucks'] = trucks_list

        self.flag = StatusCode.HTTP_200_OK
        return JsonWrapper(dic, self.flag)


# -------------------------------------------- SECURITY DEPOSIT MANAGEMENT START----------------------------------- #

@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
class SecurityDepositList(TemplateView):
    """
    View for listing Security Deposit List
    """
    template_name = 'dashboard/deposit-management-list.html'

    def get_context_data(self, **kwargs):
        context = super(SecurityDepositList, self).get_context_data(**kwargs)
        deposit_list = []
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False
            deposit_list = SecurityDeposit.objects.filter(added_by__city=admin_profile.city)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)

        context['deposit_list'] = deposit_list
        return context


@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class AddSecurityDeposit(View):
    """
    View for adding new Security Deposit
    """

    @staticmethod
    def post(request):
        capacity_from = request.POST.get('capacity_from', '')
        capacity_to = request.POST.get('capacity_to', '')
        deposit_needed = request.POST.get('deposit_needed', '')
        if float(deposit_needed) > 0 and float(capacity_from) > 0 and float(capacity_to) > 0:
            try:
                if request.user.is_superuser:
                    admin_profile, created = BaseProfile.objects.get_or_create(user=request.user,
                                                                               user_type='super_user')
                else:
                    admin_profile = BaseProfile.objects.get(user=request.user)
                if not SecurityDeposit.objects.filter(capacity_from__range=(capacity_from, capacity_to),
                                                      added_by__city=admin_profile.city).exists():
                    if not SecurityDeposit.objects.filter(capacity_to__range=(capacity_from, capacity_to),
                                                          added_by__city=admin_profile.city).exists():
                        if float(capacity_from) > 0 and float(capacity_to) <= 40:
                            if float(capacity_from) < float(capacity_to):
                                item_obj = SecurityDeposit(capacity_from=capacity_from, capacity_to=capacity_to,
                                                           added_by=admin_profile)
                                item_obj.deposit_needed = deposit_needed
                                item_obj.save()
                                messages.success(request, request.lbl_added_security_deposit)
                            else:
                                messages.error(request, request.lbl_provide_valid_data)
                        else:
                            messages.error(request, request.lbl_provide_volume_between_0_40)
                    else:
                        messages.error(request, request.lbl_security_deposit_already_exist)
                else:
                    messages.error(request, request.lbl_security_deposit_already_exist)
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:list-security-deposit'))


def delete_security_deposit(request):
    if request.method == "GET":
        deposit_id = request.GET.get('deposit_id', '')
        try:
            obj = SecurityDeposit.objects.get(id=deposit_id)
            obj.delete()
            result_data = request.lbl_security_deposit_deleted

        except SecurityDeposit.DoesNotExist:
            messages.error(request, request.lbl_invalid_security_deposit)
        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class EditSecurityDeposit(TemplateView):
    """View for Update to  Security Deposit"""

    template_name = "dashboard/edit-security-deposit.html"

    def get_context_data(self, **kwargs):
        context = super(EditSecurityDeposit, self).get_context_data(**kwargs)
        deposit_id = kwargs['deposit_id']
        try:
            # Fetching editable user data
            item_data = SecurityDeposit.objects.get(id=deposit_id)
            context['item_data'] = item_data

        except SecurityDeposit.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_security_deposit)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)

        return context

    def post(self, request, **kwargs):
        capacity_from = request.POST.get('capacity_from', '')
        capacity_to = request.POST.get('capacity_to', '')
        deposit_needed = request.POST.get('deposit_needed', '')
        deposit_id = kwargs['deposit_id']
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            if float(deposit_needed) > 0 and float(capacity_from) > 0 and float(capacity_to) > 0:
                if not SecurityDeposit.objects.filter(~Q(id=deposit_id),
                                                      capacity_from__range=(capacity_from, capacity_to),
                                                      added_by__city=admin_profile.city).exists():
                    if not SecurityDeposit.objects.filter(~Q(id=deposit_id),
                                                          capacity_to__range=(capacity_from, capacity_to),
                                                          added_by__city=admin_profile.city).exists():
                        if float(capacity_from) > 0 and float(capacity_to) <= 40:
                            if float(capacity_from) < float(capacity_to):
                                try:
                                    item_obj = SecurityDeposit.objects.get(id=deposit_id)
                                    item_obj.capacity_from = capacity_from
                                    item_obj.capacity_to = capacity_to
                                    item_obj.deposit_needed = deposit_needed
                                    item_obj.save()

                                    messages.success(request, request.lbl_security_deposit_update)
                                    return redirect("dashboard:list-security-deposit")

                                except SecurityDeposit.DoesNotExist:
                                    messages.error(request, request.lbl_invalid_security_deposit)
                            else:
                                messages.error(request, request.lbl_provide_valid_data)
                        else:
                            messages.error(request, request.lbl_provide_volume_between_0_40)
                    else:
                        messages.error(request, request.lbl_security_deposit_already_exist)
                else:
                    messages.error(request, request.lbl_security_deposit_already_exist)
            else:
                messages.error(request, request.lbl_provide_valid_data)
        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_user)

        return redirect("dashboard:edit-security-deposit", deposit_id)


# -------------------------------------------- SECURITY DEPOSIT MANAGEMENT END----------------------------------- #


def update_security_deposit(request):
    if request.method == "GET":
        user_id = request.GET.get('user_id', '')
        topup_amount = request.GET.get('topup_amount', '').strip()
        result_data = ''
        try:
            base_profile = BaseProfile.objects.get(id=user_id)
            veh_obj = VehicleDetails.objects.get(driver_id=base_profile)
            veh_obj.security_deposit = float(topup_amount)
            veh_obj.save()
            result_data = request.lbl_security_amount_updated
        except BaseProfile.DoesNotExist:
            result_data = request.lbl_invalid_user
        except VehicleDetails.DoesNotExist:
            result_data = request.lbl_invalid_user
        return JsonResponse(result_data, safe=False)


@method_decorator(login_required, name='dispatch')
class PayoutManagement(TemplateView):
    """View for displaying payout history and details"""

    template_name = "dashboard/payout-management.html"
    possible_payout_days = ["Thursday", "Friday"]

    def get_context_data(self, **kwargs):
        context = super(PayoutManagement, self).get_context_data(**kwargs)
        admin_profile = BaseProfile.objects.get(user=self.request.user)

        # TO DISABLE ACTION PERMISSION FOR OPERATORS
        if admin_profile.user_type == 'operator':
            context['disable_action'] = True
        else:
            context['disable_action'] = False
        today = timezone.now()
        # Query to fetch if driver has already been paid off this weeks payout

        payout_queryset_check = Prefetch('payouthistory_set',
                                         queryset=PayoutHistory.objects.filter(payment_processed=True,
                                                                               date__date=today).order_by('-id'),
                                         to_attr='payout')

        context["payout_possible"] = today.strftime("%A") in self.possible_payout_days
        context["drivers"] = BaseProfile.objects.filter(status="active", user_type="driver",
                                                        fleet_id=None, city=admin_profile.city).prefetch_related(
            payout_queryset_check)

        payout_list = PayoutHistory.objects.filter(date__date=today, driver__status="active",
                                                   driver__user_type="driver",
                                                   driver__fleet_id=None,
                                                   driver__city=admin_profile.city, deleted=False).order_by(
            '-id')

        for payout in payout_list:
            drivers_earnings_from_discounts = payout.drivers_earnings_from_discounts
            cash_incentives_earned_by_driver = payout.cash_incentives_earned_by_driver
            total_discount = round(drivers_earnings_from_discounts + cash_incentives_earned_by_driver, 2)
            setattr(payout, 'total_discount', total_discount)

        context["payout_list"] = payout_list
        # context["fleet_payout_list"] = PayoutHistory.objects.filter(date__date=today, driver__status="active",
        #                                                             driver__user_type="fleet_admin",
        #                                                             driver__fleet_id=None,
        #                                                             driver__city=admin_profile.city,
        #                                                             deleted=False).order_by('-id')

        # fleet_payout_list = PayoutHistory.objects.filter(date__date=today, driver__status="active",
        #                                                  driver__user_type="driver",
        #                                                  driver__city=admin_profile.city,
        #                                                  deleted=False).exclude(driver__fleet_id__isnull=True).annotate(
        #     net_payable=Sum('net_payable_for_driver'),
        #     amount_to_be_collected=Sum('amount_to_be_collected_from_driver')).values_list('driver__fleet_id','net_payable', 'amount_to_be_collected').distinct('driver__fleet_id')
        # .values_list('driver__fleet_id', flat=True)

        # logger_me.debug('fleet_payout_list')
        # logger_me.debug(fleet_payout_list)
        # context["fleet_payout_list"] = PayoutHistory.objects.raw(
        #     "SELECT SUM(pt.amount_to_be_collected_from_driver) as driver_collection, SUM(pt.net_payable_for_driver) as payable, profile.fleet_id_id FROM api_base_payouthistory pt INNER JOIN api_base_baseprofile profile ON pt.driver_id = profile.userprofile_ptr_id WHERE(profile.status='active' and user_type='driver' and city_id=1 and fleet_id_id>0 and pt.deleted=false and profile.userprofile_ptr_id=245 and pt.date::date=now()::date) GROUP BY profile.fleet_id_id")

        cursor = connection.cursor()
        city_id = admin_profile.city.id
        cursor.execute(
            "SELECT SUM(pt.amount_to_be_collected_from_driver) as amount_to_be_collected_from_driver, SUM(pt.net_payable_for_driver) as net_payable_for_driver, profile.fleet_id_id as fleet_id, SUM(pt.cash_incentives_earned_by_driver) as cash_incentives, SUM(pt.drivers_earnings_from_discounts) as discounts, SUM(pt.drivers_earnings_from_transfers) as total_earnings FROM api_base_payouthistory pt INNER JOIN api_base_baseprofile profile ON pt.driver_id = profile.userprofile_ptr_id WHERE(profile.status='active' and profile.user_type='driver' and profile.city_id= {} and profile.fleet_id_id>0 and pt.deleted=false and pt.date::date=now()::date and pt.payment_processed=false ) GROUP BY profile.fleet_id_id".format(
                city_id))
        fleet_payout_list = cursor.fetchall()
        fleets = []

        dict_arr = []
        for each in fleet_payout_list:
            amount_to_be_collected_from_driver = each[0]
            net_payable_for_driver = each[1]
            if amount_to_be_collected_from_driver > net_payable_for_driver:
                driver_collection = amount_to_be_collected_from_driver - net_payable_for_driver
                payable = 0
            else:
                payable = net_payable_for_driver - amount_to_be_collected_from_driver
                driver_collection = 0
            cash_incentives = each[3]
            discounts = each[4]
            total_earnings = each[5]
            total_discount = cash_incentives + discounts
            fleet_id = each[2]
            dict = {
                'driver_collection': driver_collection,
                'payable': payable,
                'fleet_id': fleet_id,
                'total_discount': total_discount,
                'total_earnings': total_earnings
            }
            logger_me.debug('driver_collection')
            logger_me.debug(driver_collection)

            logger_me.debug('payable')
            logger_me.debug(payable)

            logger_me.debug('fleet_id')
            logger_me.debug(fleet_id)

            dict_arr.append(dict)
            if each[2] not in fleets:
                fleets.append(each[2])

        logger_me.debug(fleets)
        fleet_admins = BaseProfile.objects.filter(id__in=fleets)
        logger_me.debug(fleet_admins)
        for each in fleet_admins:
            for dic in dict_arr:
                logger_me.debug(dic['fleet_id'])
                if each.id == dic['fleet_id']:
                    setattr(each, 'amount_to_be_collected_from_driver', dic['driver_collection'])
                    setattr(each, 'net_payable_for_driver', dic['payable'])
                    setattr(each, 'total_discount', dic['total_discount'])
                    setattr(each, 'total_earnings', dic['total_earnings'])

        logger_me.debug('fleet_admins')
        logger_me.debug(fleet_admins)
        context["fleet_admins"] = fleet_admins
        # fleet_admins = BaseProfile.objects.filter(status="active", user_type="fleet_admin",
        #                                           id__in=fleet_payout_list, city=admin_profile.city)
        admins = BaseProfile.objects.filter(status="active", user_type="fleet_admin",
                                            fleet_id=None, city=admin_profile.city)

        logger_me.debug('fleet_admins')
        # logger_me.debug(fleet_admins)
        # context["fleet_admins"] = fleet_admins

        # Payout not possible this day
        if not context["payout_possible"]:
            messages.error(self.request,
                           self.request.lbl_payout_error_message + " " + ", ".join(self.possible_payout_days))

        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(disable_operator_permission(), name='dispatch')
class GeneratePartnerPayout(ApiView):
    """Api for generating the partner payout"""

    user_type = ["driver", "fleet_admin"]

    # def post(self, request, *args, **kwargs):
    #     dic = {}
    #
    #     driver_id = request.POST.get('driver_id', '')
    #
    #     if driver_id != "":
    #         try:
    #             driver_obj = BaseProfile.objects.get(id=driver_id, status="active", user_type__in=self.user_type,
    #                                                  fleet_id=None)
    #             driver_payout_obj = calculate_driver_payout(driver_obj)
    #             if driver_payout_obj:
    #                 dic["payout_amount"] = driver_payout_obj.net_payable_for_driver
    #                 self.flag = StatusCode.HTTP_200_OK
    #             else:
    #                 payout_history = PayoutHistory(driver=driver_obj, date=timezone.now(), payment_processed=True)
    #                 payout_history.save()
    #                 # ajax response for none returned from function
    #                 dic['error_flag'] = 1
    #                 self.flag = StatusCode.HTTP_200_OK
    #
    #         except BaseProfile.DoesNotExist:
    #             dic["message"] = request.lbl_invalid_user
    #
    #     else:
    #         dic["message"] = request.lbl_provide_valid_data
    #         self.flag = StatusCode.HTTP_400_BAD_REQUEST
    #
    #     return JsonWrapper(dic, self.flag)

    def get(self, request, *args, **kwargs):

        dic = {}

        driver_id = request.GET.get('driver_id', '')

        if driver_id != "":
            try:
                driver_obj = BaseProfile.objects.get(id=driver_id, status="active", user_type__in=self.user_type,
                                                     fleet_id=None)
                if driver_obj.user_type == 'fleet_admin':
                    last_payout = PayoutHistory.objects.filter(driver__fleet_id=driver_obj,
                                                               payment_processed=False).latest('id')
                    last_payout.payment_processed = True
                    last_payout.save(update_fields=['payment_processed'])
                    last_payout.driver.fleet_id.payment_processed = True
                    last_payout.driver.fleet_id.save(update_fields=['payment_processed'])
                    self.flag = StatusCode.HTTP_200_OK
                else:

                    last_payout = PayoutHistory.objects.filter(driver=driver_obj, payment_processed=False).latest('id')
                    last_payout.payment_processed = True
                    last_payout.save(update_fields=['payment_processed'])
                    self.flag = StatusCode.HTTP_200_OK

            except BaseProfile.DoesNotExist:
                dic["message"] = request.lbl_invalid_user

            except PayoutHistory.DoesNotExist:
                dic["message"] = "No payout record found"

        else:
            dic["message"] = request.lbl_provide_valid_data
            self.flag = StatusCode.HTTP_400_BAD_REQUEST

        return JsonWrapper(dic, self.flag)


class PayoutHistoryView(TemplateView):
    template_name = 'dashboard/payout-history.html'

    def dispatch(self, request, *args, **kwargs):
        context = super(PayoutHistoryView, self).dispatch(request, *args, **kwargs)
        user_id = kwargs['user_id']
        try:
            user_profile = BaseProfile.objects.get(id=user_id)
            payout_hist = PayoutHistory.objects.filter(driver=user_profile)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, "Invalid User")
        except PayoutHistory.DoesNotExist:
            messages.error(self.request, "No Payout for the selected user")
        return context

    def get_context_data(self, **kwargs):
        user_id = kwargs['user_id']
        context = super(PayoutHistoryView, self).get_context_data(**kwargs)
        admin_profile = BaseProfile.objects.get(id=user_id)
        payment_history = PayoutHistory.objects.filter(driver=admin_profile, payment_processed=True)
        context['payment_hist'] = payment_history
        return context


class EditDistrict(TemplateView):
    template_name = 'dashboard/edit-district.html'

    def get_context_data(self, **kwargs):
        context = super(EditDistrict, self).get_context_data(**kwargs)
        city_id = kwargs['city_id']
        context['city_id'] = city_id
        districts = District.objects.filter(city__id=city_id)
        context['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
        if districts:
            context['districts'] = districts
        return context

    def post(self, request, *args, **kwargs):
        lat = self.request.POST.get('lat')
        lng = self.request.POST.get('lng')
        city_id = self.request.POST.get('city_id')
        city_name = self.request.POST.get('city', '')
        district_name = get_district_from_location(lat, lng)
        if district_name != "":
            city = City.objects.get(id=city_id)
            District.objects.create(city=city, name=district_name, latitude=lat, longitude=lng)
        elif city_name != '':
            city_name_arr = city_name.split(',')
            city_name = city_name_arr[0]
            city = City.objects.get(id=city_id)
            District.objects.create(city=city, name=city_name, latitude=lat, longitude=lng)
        else:
            messages.error(self.request, "Invalid district")
        return redirect("dashboard:edit-dist", city_id)


def DeleteDistrict(request, *args, **kwargs):
    if kwargs['district_id']:
        try:
            dist_obj = District.objects.get(id=kwargs['district_id'])
            dist_obj.delete()
            messages.success(request, "Deleted District")
        except:
            messages.error(request, "Failed to delete district")

    else:
        messages.error(request, 'Failed to delete district')
    return redirect(request.META['HTTP_REFERER'])


def UpdateDistrict(request, *args, **kwargs):
    if request.method == 'POST':
        lat = request.POST.get('lat', '')
        lng = request.POST.get('lng', '')
        dist_name = request.POST.get('city', '')

        dist_id = request.POST.get('dist_id', '')
        if dist_id:
            try:
                dist_obj = District.objects.get(id=dist_id)
                dist_obj.name = dist_name
                dist_obj.latitude = lat
                dist_obj.longitude = lng
                dist_obj.save()
                messages.success(request, 'District Updated Successfull')
            except:
                messages.error(request, 'Failed to update district')

        else:
            messages.error(request, 'Failed to update district')
    else:
        messages.error(request, 'Failed to update district')

    return redirect(request.META['HTTP_REFERER'])


@method_decorator((login_required, verify_permission(level='superuser')), name='dispatch')
class RefundList(TemplateView):
    template_name = 'dashboard/refund_list.html'

    def get_context_data(self, **kwargs):
        context = super(RefundList, self).get_context_data(**kwargs)
        refund_obj = RefundManagement.objects.all().order_by('-id')
        context['refunds'] = refund_obj
        return context


def RefundInitiate(request, *args, **kwargs):
    trans_id = kwargs['transfer_id']
    if trans_id:
        try:
            user_base_profile = BaseProfile.objects.get(user=request.user)
            trans_obj = Transfer.objects.get(id=trans_id)
            trans_obj.refund_initiated = True
            trans_obj.save()
            refund_obj = RefundManagement(added_by=user_base_profile, refund_cause='Damage Reported',
                                          amount_to_refund=trans_obj.penalty, transfer=trans_obj, status='requested')
            refund_obj.save()
            messages.success(request, "Refund Requested Successfully")
        except BaseProfile.DoesNotExist:
            messages.error(request, "Base profile not found")
        except Transfer.DoesNotExist:
            messages.error(request, "Invalid Transfer")
        except:
            messages.error(request, "Refund Request Failed")
    else:
        messages.error(request, "Refund Request Failed")
    return redirect(request.META['HTTP_REFERER'])


def RefundStatus(request, *args, **kwargs):
    refund_id = kwargs['refund_id']
    status = kwargs['status']
    try:
        refund_obj = RefundManagement.objects.get(id=refund_id)
        refund_obj.status = status
        refund_obj.save()
        messages.success(request, "Refund Status Successfully Changed")
    except RefundManagement.DoesNotExist:
        messages.success(request, "Refund Status Change Failed")
    except:
        messages.success(request, "Refund Status Change Failed")
    return redirect(request.META['HTTP_REFERER'])


def RefundTransfer(request, *args, **kwargs):
    if request.method == 'POST':
        trans_id = request.POST.get('trans_id', '')
        refund = request.POST.get('refund', 0)
        cause = request.POST.get('cause', '')
        try:
            user_base_profile = BaseProfile.objects.get(user=request.user)
            trans_obj = Transfer.objects.get(id=trans_id)
            trans_obj.refund_initiated = True
            trans_obj.save()
            refund_obj = RefundManagement(added_by=user_base_profile, refund_cause=cause,
                                          amount_to_refund=refund, transfer=trans_obj, status='requested')
            refund_obj.save()
            messages.success(request, "Refund Requested Successfully")
        except BaseProfile.DoesNotExist:
            messages.error(request, "Base profile not found")
        except Transfer.DoesNotExist:
            messages.error(request, "Invalid Transfer")
        except:
            messages.error(request, "Refund Request Failed")
        return redirect(request.META['HTTP_REFERER'])


class TripHistory(TemplateView):
    template_name = "dashboard/trip-history.html"

    def get_context_data(self, **kwargs):
        context = super(TripHistory, self).get_context_data(**kwargs)
        driver_obj = BaseProfile.objects.get(id=kwargs['driver_id'])
        payout_date = timezone.now()
        payout_date = payout_date_peru = payout_date.astimezone(pytz.timezone('America/Lima'))
        # PERU TIME - 1
        actual_payout_peru_date = payout_date_peru - timedelta(1)
        actual_payout_peru_date = actual_payout_peru_date.replace(hour=23, minute=59, second=59)
        actual_payout_utc = actual_payout_peru_date.astimezone(pytz.utc)
        if driver_obj.user_type == 'driver':
            previous_payouts = PayoutHistory.objects.filter(driver=driver_obj, payment_processed=True).order_by('-id')
        else:
            previous_payouts = PayoutHistory.objects.filter(driver__fleet_id=driver_obj,
                                                            payment_processed=True).order_by('-id')
        start_date = None
        if previous_payouts:
            # logger_me.debug('%%%%%----%%%%%')
            # logger_me.debug(previous_payouts[0].date)
            if previous_payouts[0].date.date() == timezone.now().date():
                if len(previous_payouts) > 1:
                    start_date = previous_payouts[1].date
                else:
                    start_date = previous_payouts[0].date - timedelta(days=7)
            else:
                start_date = previous_payouts[0].date
                # logger_me.debug('%%%%%----%%%%%')
        else:
            if driver_obj.user_type == 'driver':
                start_dates = Transfer.objects.filter(driver=driver_obj, status='completed').order_by(
                    'completed_on').values(
                    'transfer_on')
            else:
                start_dates = Transfer.objects.filter(driver__fleet_id=driver_obj, status='completed').order_by(
                    'completed_on').values(
                    'transfer_on')
            if start_dates:
                start_date = start_dates[0]['transfer_on'].date()

        if start_date:
            if driver_obj.user_type == 'driver':
                raw_bookings = Transfer.objects.filter(status='completed', driver=driver_obj,
                                                       completed_on__date__gte=start_date,
                                                       completed_on__lte=actual_payout_utc)
            else:
                raw_bookings = Transfer.objects.filter(status='completed', driver__fleet_id=driver_obj,
                                                       completed_on__date__gte=start_date,
                                                       completed_on__lte=actual_payout_utc)

            for transfer in raw_bookings:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer, loc_type='pickup')
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer, loc_type='drop')

                setattr(transfer, 'transfer_pickup', transfer_pickup.location_name)
                setattr(transfer, 'transfer_drop', transfer_drop.location_name)
                peru_timezone = pytz.timezone('America/Lima')
                transfer_on = transfer.transfer_on.astimezone(peru_timezone)
                added_time = str(transfer_on.strftime('%d-%m-%Y %I:%M %p')) + "\n"
                setattr(transfer, 'added_time', added_time)

            context['trips'] = raw_bookings
            context['display_template_label'] = 'Payout Trips'

        return context


class LogView(TemplateView):
    template_name = "dashboard/log.html"

    def get_context_data(self, **kwargs):
        context = super(LogView, self).get_context_data(**kwargs)
        logs = SearchFailedLog.objects.all().order_by('-transfer__id').distinct('transfer__id')
        for log in logs:
            setattr(log, 'driver', SearchFailedLog.objects.filter(transfer=log.transfer))
            peru_timezone = pytz.timezone('America/Lima')
            transfer_on = log.transfer.transfer_on.astimezone(peru_timezone)
            added_time = str(transfer_on.strftime('%d-%m-%Y %H:%M:%S')) + "\n"
            setattr(log, 'added_time', added_time)

        page = self.request.GET.get('page', 1)

        paginator = Paginator(logs, 10)
        try:
            logs = paginator.page(page)
        except PageNotAnInteger:
            logs = paginator.page(1)
        except EmptyPage:
            logs = paginator.page(paginator.num_pages)
        logger_me.debug(logs.has_other_pages())
        context['logs'] = logs
        return context


################################################################################################################
# --------------------------------------------OPERATOR MANAGEMENT START------------------------------------------ #
################################################################################################################

@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
class ListOperator(TemplateView):
    """
    View for listing operator's
    """
    template_name = 'dashboard/operator_list.html'

    def get_context_data(self, **kwargs):
        context = super(ListOperator, self).get_context_data(**kwargs)
        # Getting all the admin's except the current logged in admin
        operator_admins = []
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            operator_admins = BaseProfile.objects.filter(user_type='operator', status='active', city=admin_profile.city)
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_admin)
        context['operator_admins'] = operator_admins
        return context


@method_decorator((login_required, verify_permission(level='staff')), name='dispatch')
class AddOperator(View):
    """
    View for adding new Operator
    """

    @staticmethod
    def post(request):
        username = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        try:
            admin_profile = BaseProfile.objects.get(user=request.user)
            if username is not None:
                if not User.objects.filter(username=username):
                    try:
                        random_password = random_number_generator(8)
                        logger_me.debug('random_password')
                        logger_me.debug(random_password)
                        user = User.objects.create_user(
                            username=username, email=username, password=random_password, is_staff=True)
                        user.first_name = first_name
                        user.last_name = last_name
                        user.is_active = True
                        user.save()

                        user_profile, status = BaseProfile.objects.get_or_create(user=user)
                        user_profile.user_type = 'operator'
                        user_profile.city = admin_profile.city
                        user_profile.status = 'active'
                        user_profile.save()
                        messages.success(request, request.lbl_added_operator_success + " %s" % user.email)

                        # Sending password as email to new admin
                        subject = "Muberz new account info"
                        ctx = {
                            "lbl_password_txt": request.lbl_password_txt,
                            "new_acc_info_added": request.new_operator_info_added,
                            "lbl_login_txt": request.lbl_login_txt,
                            "username": user.email,
                            "password": random_password,
                            "link": "http://{0}/dashboard/login/?email={1}&pass={2}".format(
                                request.META['HTTP_HOST'], user.email, random_password)
                        }
                        content = get_template("dashboard/email-templates/new_account_info.html").render(ctx)
                        threading.Thread(target=send_template_email, args=(subject, content, [user.email])).start()
                    except IntegrityError:
                        messages.error(request, request.lbl_another_username_exists)
                else:
                    messages.error(request, request.lbl_another_username_exists)

            else:
                messages.error(request, request.lbl_provide_valid_data)
        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_admin)

        return redirect(reverse('dashboard:list-operator'))


@method_decorator((login_required, verify_permission(level=super)), name='dispatch')
class EditOperator(TemplateView):
    """View for Update to Operator"""

    template_name = "dashboard/edit-operator.html"

    def get_context_data(self, **kwargs):
        context = super(EditOperator, self).get_context_data(**kwargs)
        operator_id = kwargs['operator_id']
        try:
            # Fetching editable user data
            item_data = BaseProfile.objects.get(id=operator_id)
            context['item_data'] = item_data
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)

        return context

    def post(self, request, **kwargs):
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        operator_id = kwargs['operator_id']
        try:
            item_obj = BaseProfile.objects.get(id=operator_id)
            item_obj.user.first_name = first_name
            item_obj.user.last_name = last_name
            item_obj.save()
            item_obj.user.save()

            messages.success(request, request.lbl_operator_up_success)
            return redirect("dashboard:list-operator")

        except BaseProfile.DoesNotExist:
            messages.error(request, request.lbl_invalid_operator)
        return redirect(reverse('dashboard:list-operator'))


def delete_operator(request):
    if request.method == "GET":
        operator_id = request.GET.get('operator_id', '')
        try:
            user = User.objects.get(id=operator_id)
            user.delete()
            messages.success(request, request.lbl_operator_deleted)
            result_data = request.lbl_admin_deleted

        except User.DoesNotExist:
            messages.error(request, request.lbl_invalid_operator)
            result_data = request.lbl_invalid_operator

        return JsonResponse(result_data, safe=False)


@method_decorator((login_required, verify_permission(level='None')), name='dispatch')
class RentalList(TemplateView):
    """View for managing the rentals in the system"""

    def normalize_query(self, query_string):
        to_lower = query_string.lower()
        split = to_lower.split(" ")
        return split

    def post(self, request, **kwargs):
        context = {}
        trip_list = []
        admin_profile = BaseProfile.objects.get(user=self.request.user)
        # GET ALL TRANSFERS
        transfers = []
        statuses = ['not_paid']

        bike_id = request.GET.get('bike_id', '')
        user_id = request.GET.get('user_id', '')
        on_rental = request.GET.get('on_rental', '')
        page_length = request.GET.get('length', 10)
        start = int(request.GET.get('start', 10))
        draw = int(request.GET.get('draw', 1))
        get_coloumn_id = 'columns[' + str(request.GET.get('order[0][column]', '')) + '][data]'
        sort_by = str(request.GET.get(get_coloumn_id))
        sort_dir = request.GET.get('order[0][dir]')

        sorty = {
            "system": "bike__system__name",
            "bike_no": "bike__name",
            "user": "user__user__first_name",
            "username": "user__user__username",
            "start_time": "start_time",
            "end_time": "end_time",
            "device": "device",
            "app_version": "app_version",
            "": "charge_amount",
            "end_mode": "end_mode",
            "device_os": "device_os",
            "NONE": "start_time",
            "none": "start_time",
            "None": "start_time"
        }

        sort_by = sorty[sort_by]

        if start == 0:
            current_page = 1
        else:
            current_page = int(start) / int(page_length) + 1
        search = request.GET.get('search[value]', '')

        if sort_dir == 'desc':
            sort_by = '-' + sort_by

        # if admin_profile.user_type == 'fleet_admin':
        #     transfers = Transfer.objects.filter(driver__fleet_id=admin_profile).exclude(status__in=statuses)
        # elif admin_profile.user_type == 'admin_user' or admin_profile.user_type == 'operator':
        #     transfers = Transfer.objects.filter(city=admin_profile.city).exclude(status__in=statuses)
        # elif self.request.user.is_superuser:
        #     transfers = Transfer.objects.all()

        transfers = Transfer.objects.all()

        if search:
            terms = self.normalize_query(search)
            terms_filter = [i for i in terms if i]

            if len(terms_filter) == 1:
                transfers = transfers.filter(
                    Q(user__user__first_name__icontains=terms_filter[0]) |
                    Q(user__user__last_name__icontains=terms_filter[0]) |
                    Q(user__user__username__icontains=terms_filter[0]) |
                    Q(bike__name__icontains=terms_filter[0]) |
                    Q(device__icontains=terms_filter[0]) |
                    Q(device_os__icontains=terms_filter[0])
                )
            else:
                transfers = transfers.filter((
                        Q(user__user__first_name__icontains=terms_filter[0]) |
                        Q(user__user__last_name__icontains=terms_filter[1]))
                )

        transfers = transfers.select_related('driver')

        paginator = Paginator(transfers, page_length)
        trip_data = paginator.page(current_page)
        total = paginator.count



        for transfer in trip_data:
            try:
                transfer_pickup = TransferLocation.objects.get(transfer_id=transfer, loc_type='pickup')
            except TransferLocation.DoesNotExist:
                transfer_pickup = None

            try:
                transfer_drop = TransferLocation.objects.get(transfer_id=transfer, loc_type='drop')
            except TransferLocation.DoesNotExist:
                transfer_drop = None

            count = Damage.objects.filter(transfer_id=transfer).aggregate(count=Sum('count'))["count"]
            setattr(transfer, 'no_damaged_items', count)
            setattr(transfer, 'transfer_pickup', transfer_pickup.location_name if transfer_pickup else "")
            setattr(transfer, 'transfer_drop', transfer_drop.location_name if transfer_drop else "")
            peru_timezone = pytz.timezone('America/Lima')
            transfer_on = transfer.transfer_on.astimezone(peru_timezone)
            added_time = str(transfer_on.strftime('%d-%m-%Y %I:%M %p')) + "\n"
            setattr(transfer, 'added_time', added_time)
            payout_status = False
            payout = PayoutHistory.objects.filter(driver=transfer.driver).order_by('-id')
            if payout:
                if transfer in payout[0].transfers.all():
                    if payout[0].payment_processed:
                        payout_status = True
                    else:
                        payout_status = False
            setattr(transfer, 'payout_status', payout_status)
            trip_list.append({
                "user": '{0} {1}'.format(transfer.added_by.user.first_name, transfer.added_by.user.last_name),
                "driver_name": '{0} {1}'.format(transfer.driver.user.first_name if transfer.driver else '',
                                                transfer.driver.user.last_name if transfer.driver else ''),
                "pickup-location": transfer_pickup.location_name if transfer_pickup else '',
                "drop-location": transfer_drop.location_name if transfer_pickup else '',
                "transfer_on": transfer.transfer_on.astimezone(peru_timezone),
                "total_amount": transfer.total_amount,
                "payment_type": transfer.get_payment_type_display(),
                "status": transfer.get_status_display(),
                "id": transfer.id,
                "refund_initiated": transfer.refund_initiated,
                "payout_status": transfer.payout_status,

            })
        data = {}
        data["start"] = start
        data["draw"] = draw
        data["recordsTotal"] = total
        data["recordsFiltered"] = total
        data["data"] = trip_list

        # context['display_template_label'] = self.request.lbl_rentals
        # context['transfers'] = trip_list
        return JsonResponse(data, safe=False)


class TripList(ApiView):
    def post(self, request, **kwargs):

        try:
            trip_list = []
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # GET ALL TRANSFERS~
            transfers = []
            statuses = ['not_paid']

            page_length = request.GET.get('length', 10)
            start = int(request.GET.get('start', 10))
            draw = int(request.GET.get('draw', 1))
            context = {
                    "draw": draw,
                    "recordsTotal": 10,
                    "recordsFiltered": 10,
                    "data": [
                                {
                                  "user": "row_5",
                                  "driver_name": "Airi",
                                  "pickup-location": "Satou",
                                  "drop-location": "Accountant",
                                  "office": "Tokyo",
                                  "start_date": "28th Nov 08",
                                  "salary": "$162,700"
                                },
                                {
                                  "user": "row_25",
                                  "driver_name": "Angelica",
                                  "pickup-location":"Ramos",
                                  "drop-location": "Chief Executive Officer (CEO)",
                                  "office": "London",
                                  "start_date": "9th Oct 09",
                                  "salary": "$1,200,000"
                                },
                                {
                                  "user": "row_3",
                                  "driver_name": "Ashton",
                                  "pickup-location":"Cox",
                                  "drop-location": "Junior Technical Author",
                                  "office": "San Francisco",
                                  "start_date": "12th Jan 09",
                                  "salary": "$86,000"
                                },
                                {
                                  "user": "row_19",
                                  "driver_name": "Bradley",
                                  "pickup-location":"Greer",
                                  "drop-location": "Software Engineer",
                                  "office": "London",
                                  "start_date": "13th Oct 12",
                                  "salary": "$132,000"
                                },
                                {
                                  "user": "row_28",
                                  "driver_name": "Brenden",
                                  "pickup-location":"Wagner",
                                  "drop-location": "Software Engineer",
                                  "office": "San Francisco",
                                  "start_date": "7th Jun 11",
                                  "salary": "$206,850"
                                },
                                {
                                  "user": "row_6",
                                  "driver_name": "Brielle",
                                  "pickup-location": "Williamson",
                                  "drop-location": "Integration Specialist",
                                  "office": "New York",
                                  "start_date": "2nd Dec 12",
                                  "salary": "$372,000"
                                },
                                {
                                  "user": "row_43",
                                  "driver_name": "Bruno",
                                  "pickup-location":"Nash",
                                  "drop-location": "Software Engineer",
                                  "office": "London",
                                  "start_date": "3rd May 11",
                                  "salary": "$163,500"
                                },
                                {
                                  "user": "row_23",
                                  "driver_name": "Caesar",
                                  "pickup-location":"Vance",
                                  "drop-location": "Pre-Sales Support",
                                  "office": "New York",
                                  "start_date": "12th Dec 11",
                                  "salary": "$106,450"
                                },
                                {
                                  "user": "row_51",
                                  "driver_name": "Cara",
                                  "pickup-location":"Stevens",
                                  "drop-location": "Sales Assistant",
                                  "office": "New York",
                                  "start_date": "6th Dec 11",
                                  "salary": "$145,600"
                                },
                                {
                                  "user": "row_4",
                                  "driver_name": "Cedric",
                                  "pickup-location":"Kelly",
                                  "drop-location": "Senior Javascript Developer",
                                  "office": "Edinburgh",
                                  "start_date": "29th Mar 12",
                                  "salary": "$433,060"
                                }
                              ]
                    }
        except Exception as e:
            context['error']=str(e)
        self.flag = StatusCode.HTTP_200_OK
        return JsonResponse(context)



################################################################################################################
# -------------------------------------------- OPERATOR MANAGEMENT END------------------------------------------- #
################################################################################################################
class TruckTypes(TemplateView):
    template_name = "dashboard/trucktypes.html"

    def get_context_data(self, **kwargs):
        from api_base.models import TruckTypes
        context = super().get_context_data(**kwargs)
        try:
            admin_profile = BaseProfile.objects.get(user=self.request.user)
            # TO DISABLE ACTION PERMISSION FOR OPERATORS
            if admin_profile.user_type == 'operator':
                context['disable_action'] = True
            else:
                context['disable_action'] = False

            truck_types = TruckTypes.objects.all().order_by('vol_min')
            context['newval'] = admin_profile.user_type
            context['queryset'] = truck_types
            context['heading'] = 'Truck Types'
        except BaseProfile.DoesNotExist:
            messages.error(self.request, self.request.lbl_invalid_user)
        return context

    def post(self, request, *args, **kwargs):
        #email = request.POST.get('email')
        vol_min = float(request.POST.get('vol_min'))
        vol_max = float(request.POST.get('vol_max'))
        truck_id = int(request.POST.get('truck_id'))
        from api_base.models import TruckTypes
        trucks = TruckTypes.objects.get(id=truck_id)
        trucks.vol_min = vol_min
        trucks.vol_max = vol_max
        if trucks.vol_max <= trucks.vol_min:
            trucks.vol_max = vol_min + 1
        trucks.save()
        '''while truck_id != 4:
            truck_id = truck_id + 1
            nxt_truck = TruckTypes.objects.get(id=truck_id)
            if nxt_truck.vol_min <= vol_max:
                nxt_truck.vol_min = vol_max + 1
                nxt_truck.save()
            nxt_truck = TruckTypes.objects.get(id=truck_id)
            if nxt_truck.vol_max <= nxt_truck.vol_min:
                nxt_truck.vol_max = nxt_truck.vol_min + 1
                nxt_truck.save()'''
        messages.success(request, request.lbl_operator_up_success)
        return redirect(reverse('dashboard:trucktypes'))


class AddTruckCategory(View):
    """
    View for adding new Truck Category
    """
    def  post(self, request, *args, **kwargs):
        category_name = request.POST.get('cat_name', '')
        vol_min = request.POST.get('min_vol', '')
        vol_max = request.POST.get('max_vol', '')
        image1 = request.POST.get('image1', '')
        from api_base.models import TruckTypes
        if category_name != '':
            try:
                admin_profile = BaseProfile.objects.get(user=request.user)
                if not TruckTypes.objects.filter(category_name=category_name).exists():
                    item_obj = TruckTypes()
                    upload1 = "{0}{1}".format(str(settings.BUCKET_URL), str(image1))
                    item_obj.image = upload1
                    item_obj.category_name = category_name
                    item_obj.vol_min = vol_min
                    item_obj.vol_max = vol_max
                    item_obj.save()
                    messages.success(request, request.lbl_added_new_commodity)
                else:
                    messages.error(request, request.lbl_commodity_already_exist)
                    return redirect("dashboard:trucktypes")
            except BaseProfile.DoesNotExist:
                messages.error(request, request.lbl_invalid_user)
        else:
            messages.error(request, request.lbl_provide_valid_data)

        return redirect(reverse('dashboard:trucktypes'))


def delete_truck_category(request):
    if request.method == "GET":
        truck_id = request.GET.get('truck_id', '')
        #truck_id = kwargs['truck_id']
        try:
            from api_base.models import TruckTypes
            truck_obj = TruckTypes.objects.get(id=truck_id)
            truck_obj.delete()
            messages.success(request, "Deleted Truck Type")
            return redirect(reverse('dashboard:trucktypes'))

        except TruckTypes.DoesNotExist:
            messages.error(request, "Failed to delete truck")
            result_data = request.lbl_invalid_operator

        return JsonResponse(result_data, safe=False)


class UpdateHandlingFee(View):
    """
    View for adding new Truck Category
    """
    def  post(self, request, *args, **kwargs):
         transfer_id = request.POST.get('transfer_id', '')
         special_handling_fee = request.POST.get('special_handling_fee', '')
         transfer_obj = Transfer.objects.get(id=transfer_id)
         transfer_obj.special_handling_fee = special_handling_fee
         transfer_obj.save()
         messages.success(request, "Updated Handling Fee Successfully")
         return redirect('dashboard:view-rental',transfer_id=transfer_id)


class AddPromotion(TemplateView):
    template_name = "dashboard/add-promotion.html"

    def get_context_data(self, **kwargs):
        context = super(AddPromotion, self).get_context_data(**kwargs)
        from datetime import datetime, timedelta
        mydate = datetime.now() + timedelta(days=30)
        context['mydate'] = mydate
        promotion_list = Promotion.objects.all()
        context['promotion_list'] = promotion_list
        return context

    def  post(self, request, *args, **kwargs):
         promo_name = request.POST.get('name', '')
         percent = request.POST.get('percent', '')
         shortdesc = request.POST.get('short-description','')
         description = request.POST.get('description', '')
         exp_date = request.POST.get('expiry','')
         promo_obj = Promotion(name=promo_name, percentage=percent, short_description=shortdesc, description=description, expiry = exp_date )
         promo_obj.save()
         # logger_me.debug(promo_obj)

         messages.success(request, "Added promotion successfully")
         return redirect(reverse('dashboard:add-promotion'))


class EditPromotion(TemplateView):
    template_name = "dashboard/edit-promotion.html"

    def get_context_data(self, **kwargs):
        context = super(EditPromotion, self).get_context_data(**kwargs)
        promotion_id = kwargs['promotion_id']
        try:
            # Fetching editable user data
            item_data = Promotion.objects.get(id=promotion_id)
            context['item_data'] = item_data
        except Promotion.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)
        return context

    def  post(self, request, *args, **kwargs):
         promo_id = request.POST.get('promo_id','')
         promo_name = request.POST.get('name', '').upper()
         percent = request.POST.get('percent', '')
         shortdesc = request.POST.get('short-description','')
         description = request.POST.get('description', '')
         exp_date = request.POST.get('expiry','')

         try:
             promo_obj = Promotion.objects.get(id=promo_id)
             promo_obj.name = promo_name
             promo_obj.percentage = percent
             promo_obj.short_description = shortdesc
             promo_obj.description = description
             promo_obj.expiry = exp_date
             promo_obj.save()

             messages.success(request, "Promotion Updated Successfully")
             return redirect("dashboard:add-promotion")

         except Promotion.DoesNotExist:
             messages.error(request, "Promotion does not exist")
         return redirect(reverse('dashboard:add-promotion'))


def delete_promotion():
    if request.method == "GET":
        promotion_id = request.GET.get('promo_id', '')
        try:
            promo_obj = Promotion.objects.get(id=promotion_id)
            promo_obj.delete()
            messages.success(request, "Promotion Deleted")
            return redirect(reverse('dashboard:add-promotion'))
        except Promotion.DoesNotExist:
            messages.error(request, "Failed to delete promotion")
            return redirect(reverse('dashboard:add-promotion'))
        return JsonResponse(result_data, safe=False)


class AddAdvertisement(TemplateView):
    template_name = "dashboard/add-advertisement.html"

    def get_context_data(self, **kwargs):
        context = super(AddAdvertisement, self).get_context_data(**kwargs)
        from datetime import datetime, timedelta
        currentdate = datetime.now()
        nextdate = datetime.now() + timedelta(days=1)
        context['nextdate'] = nextdate
        context['currentdate'] = currentdate
        now_date = timezone.now()
        context['ads_list'] = Advertisement.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        added_by = BaseProfile.objects.get(user=request.user)
        adv_name = request.POST.get('name', '')
        date_start = request.POST.get('date_start', '')
        date_end = request.POST.get('date_end', '')
        user = request.POST.get('user', '')
        if user == '' :
            userbool = False
        else:
            userbool = True
        image1 = request.POST.get('image1', '')
        upload1 = "{0}{1}".format(str(settings.BUCKET_URL), str(image1))
        image = upload1
        partner = request.POST.get('partner', '')
        if partner == '' :
            partnerbool = False
        else:
            partnerbool = True
        adv_obj = Advertisement(added_by=added_by, name=adv_name, date_start=date_start, date_end=date_end, image=image, user=userbool, partner=partnerbool)
        adv_obj.save()
        # logger_me.debug("hi")
        # logger_me.debug(added_by)
        messages.success(request, "Added advertisement successfully")
        return redirect(reverse('dashboard:add-advertisement'))


class EditAdvertisement(TemplateView):
    template_name = "dashboard/edit-advertisemet.html"

    def get_context_data(self, **kwargs):
        context = super(EditAdvertisement, self).get_context_data(**kwargs)
        ads_id = kwargs['ads_id']
        try:
            # Fetching editable user data
            item_data = Advertisement.objects.get(id=ads_id)
            context['item_data'] = item_data
        except Advertisement.DoesNotExist:
            messages.error(self.request, self.request.lbl_no_entry)
        return context

    def post(self, request, *args, **kwargs):
        added_by = BaseProfile.objects.get(user=request.user)
        adv_id = request.POST.get('ads_id')
        adv_name = request.POST.get('name', '')
        date_start = request.POST.get('date_start', '')
        date_end = request.POST.get('date_end', '')
        user = request.POST.get('user', '')
        if user == '':
            userbool = False
        else:
            userbool = True
        image1 = request.POST.get('image1', '')
        if image1 != "":
            upload1 = "{0}{1}".format(str(settings.BUCKET_URL), str(image1))
            image = upload1
        else:
            image = request.POST.get('image_name', '')

        partner = request.POST.get('partner', '')
        if partner == '':
            partnerbool = False
        else:
            partnerbool = True
        try:
            ads_obj = Advertisement.objects.get(id=adv_id)
            ads_obj.name = adv_name
            ads_obj.date_start = date_start
            ads_obj.date_end = date_end
            ads_obj.image = image
            ads_obj.user = userbool
            ads_obj.partner = partnerbool
            ads_obj.save()
            messages.success(request, "Advertisement Updated Successfully")
            return redirect("dashboard:add-advertisement")

        except Advertisement.DoesNotExist:
            messages.error(request, "Advertisement does not exist")
        return redirect(reverse('dashboard:add-advertisement'))


def delete_advertisement(request):

    if request.method == "GET":
        adv_id = request.GET.get('ads_id', '')
        try:
            ads_obj = Advertisement.objects.get(id=adv_id)
            ads_obj.delete()
            messages.success(request, "Deleted")
            return redirect(reverse('dashboard:add-advertisement'))
        except Advertisement.DoesNotExist:
            messages.error(request, "Failed to delete Ads")
            return redirect(reverse('dashboard:add-advertisement'))
        return JsonResponse(result_data, safe=False)


class AddOnOffSwitch(View):
    """
    View for adding on off switch
    """
    def post(self, request, *args, **kwargs):
        added_by = BaseProfile.objects.get(user=request.user)
        start_time = request.POST.get('start-time', '')
        end_time = request.POST.get('end-time', '')
        status = request.POST.get('status', '')
        if status == "1":
            status_up = True
        else:
            status_up = False
        if start_time and end_time != '':
            count = OnOffSwitch.objects.all().count()
            if count >= 1:
                onoffswitch_obj = OnOffSwitch.objects.get(id=1)
                onoffswitch_obj.start_date = start_time
                onoffswitch_obj.end_date = end_time
                onoffswitch_obj.status = status_up
                onoffswitch_obj.save()
                messages.success(request, "Time intervals set successfully")
                return redirect(reverse('dashboard:update-profile'))
            else:
                onoffswitch_obj = OnOffSwitch(start_date=start_time, end_date=end_time, added_by=added_by, status = status_up)
                onoffswitch_obj.save()
                messages.success(request, "Time intervals set successfully")
                return redirect(reverse('dashboard:update-profile'))
            messages.success(request, "please provide a valid time intervals")
            return redirect(reverse('dashboard:update-profile'))


class SharingTripUser(TemplateView):
    template_name = "dashboard/sharing-trip-user.html"

    def get_context_data(self, **kwargs):
        context = super(SharingTripUser, self).get_context_data(**kwargs)
        trans_id = kwargs['transfer_id']
        try:
            # Fetching editable user data
            pickup_data =  TransferLocation.objects.filter(transfer_id=trans_id, loc_type='pickup')
            drop_data = TransferLocation.objects.filter(transfer_id=trans_id, loc_type='drop')

            driver_obj = Transfer.objects.get(id=trans_id).driver
            driver_lat = driver_obj.current_lat
            driver_long = driver_obj.current_lng

            for pickup in pickup_data:
                pickup_location = pickup.location_name
                pickup_lat = pickup.loc_lat
                pickup_long = pickup.loc_lng

            for drop in drop_data:
                drop_location = drop.location_name
                drop_lat = drop.loc_lat
                drop_long = drop.loc_lng

            context['drop_location'] = drop_location
            context['pickup_location'] = pickup_location
            context['pickup_lat'] = pickup_lat
            context['pickup_long'] = pickup_long
            context['drop_lat'] = drop_lat
            context['drop_long'] = drop_long
            context['driver_lat'] = driver_lat
            context['driver_long'] = driver_long
            context['transfer_id'] = trans_id
        except Advertisement.DoesNotExist:
            messages.error(self.request, "no location found")
        return context


class SharingTripPartner(TemplateView):
    """
    View for dispaying shared partner trip in the dashboard
    """
    template_name = "dashboard/sharing-trip-partner.html"

    def get_context_data(self, **kwargs):
        context = super(SharingTripPartner, self).get_context_data(**kwargs)
        try:
            transfer_list = Transfer.objects.filter(share_trip=True).order_by('-id')
            transfer_location = TransferLocation.objects.all()

            # logger_me.debug()
            context['transfer_list'] = transfer_list
            context['transfer_location'] = transfer_location
        except Transfer.DoesNotExist:
            messages.error(self.request, "No share trips")
        return context

    def post(self, request, *args, **kwargs):
        driver_id = request.POST.get('driverlist', '')
        transfer_id = request.POST.get('transfer_id', '')
        logger_me.debug("driver id")
        logger_me.debug(driver_id)
        logger_me.debug(transfer_id)
        transfer = Transfer.objects.get(id=transfer_id)
        driver_obj = BaseProfile.objects.get(id=driver_id)
        heading = lang_obj.get_lang_word('en', 'lbl_trip_assign_notification')
        message_body = lang_obj.get_lang_word('en', 'lbl_trip_assign_message')
        send_push_notification(transfer, driver_obj, message_body, heading)
        messages.success(request, "Notification has been send to the driver")
        return redirect(reverse('dashboard:sharing-trip-partner'))


class TurnSystemOff(View):
    """
        View for changing system status to off
        """
    def get(self, request, *args, **kwargs):
        switch_id = 1
        status_id = int(kwargs['status'])
        if status_id == 0:
            status = False
        else:
            status = True
        try:
            OnOffSwitch.objects.filter(id=switch_id).update(status=status)
            messages.success(request, "System status changed")
        except OnOffSwitch.DoesNotExist:
            messages.error(request, "Status not changes")
        return redirect('dashboard:update-profile')


# class TurnSystemOn(View):
#     """
#         View for changing system status to off
#         """
#     def get(self, request, *args, **kwargs):
#         switch_id = 1
#
#         try:
#             OnOffSwitch.objects.filter(id=switch_id).update(status=True)
#         except OnOffSwitch.DoesNotExist:
#             messages.error(request, "Status not changed")
#         return redirect('dashboard:update-profile')

