from django.conf.urls import url, include
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from dashboard.views import *

urlpatterns = [
    url(r'^login/$', LoginView.as_view(), name='dashboard-login'),
    url(r'^fleet-signup/$', SignupView.as_view(), name='fleet-signup'),
    url(r'^$', HomeView.as_view(), name='dashboard-home-page'),

    url(r'^logout/$', LogoutView.as_view(), name='logout-user'),
    url(r'^forgot-password/$', ForgotPasswordView.as_view(), name='forgot-password'),
    url(r'^reset-password/(?P<reset_key>.*)/$', ResetPasswordView.as_view(), name='reset-password'),
    url(r'^change-password/$', ChangePassword.as_view(), name='change-password'),
    url(r'^$forgot-password-success', TemplateView.as_view(template_name="dashboard/page-confirm-mail.html"),
        name='forgot-password-success'),
    url(r'^update-profile/$', UpdateProfile.as_view(), name='update-profile'),
    url(r'^404/$', Error404View.as_view(), name='404'),
    url(r'^delete-profile-image/$', csrf_exempt(delete_profile_image), name="delete-profile-image"),

    # # System Documents Management
    url(r'^list-documents/$', ListDocuments.as_view(), name='list-documents'),
    url(r'^add-document/$', AddDocument.as_view(), name='add-document'),

    # # System Admin management
    url(r'^list-admin/$', ListAdmin.as_view(), name='list-admin'),
    url(r'^add-admin/$', AddAdmin.as_view(), name='add-admin'),
    url(r'^edit-admin/(?P<admin_id>\d+)/$', EditAdmin.as_view(), name="edit-admin"),
    url(r'^delete-admin/$', csrf_exempt(delete_admin), name="delete-admin"),
    # url(r'^delete-admin/$', DeleteAdmin.as_view(), name='delete-admin'),

    # url(r'^login/$', DashboardLoginView.as_view()),
    # url(r'^logout/$', DashboardLogoutView.as_view()),
    # url(r'^profile/$',login_required(DashboardProfileView.as_view(), login_url='/dashboard/login')),
    # url(r'^$', login_required(DashboardHomeView.as_view(), login_url='/dashboard/login')),

    # FLEET LOGIN URLS
    url(r'^add-partner/$', AddPartner.as_view(), name='add-partner'),
    url(r'^edit/partner/(?P<partner_id>\d+)/$', EditPartner.as_view(), name="edit-partner"),
    url(r'^delete/partner/(?P<partner_id>\d+)/$', DeletePartner.as_view(), name="delete-partner"),
    url(r'^list-partners/$', ListPartners.as_view(), name='list-partners'),
    url(r'^fleet-driver/approve/(?P<driver_id>\d+)/$', ApproveFleetDriver.as_view(), name='fleet-approve-driver'),
    url(r'^list-partners/save-assistants/$', login_required(SaveAssistant), name='save-assistant'),
    url(r'^update-serviceable-area/$', csrf_exempt(update_serviceable_area), name="update-serviceable-area"),
    # url(r'^edit/commodity/(?P<commodity_id>\d+)/$', EditCommodity.as_view(), name="edit-commodity"),
    # url(r'^delete-commodity/$', csrf_exempt(delete_commodity), name="delete-commodity"),
    # url(r'^delete-commodity-image/$', csrf_exempt(delete_commodity_image), name="delete-commodity-image"),

    url(r'^list-commodity/$', ListCommodity.as_view(), name='list-commodity'),
    url(r'^add-commodity/$', AddCommodity.as_view(), name='add-commodity'),
    url(r'^upload-commodity-csv/$', UploadCommodityCsv.as_view(), name='upload-commodity-as-csv'),
    url(r'^edit/commodity/(?P<commodity_id>\d+)/$', EditCommodity.as_view(), name="edit-commodity"),
    url(r'^delete-commodity/$', csrf_exempt(delete_commodity), name="delete-commodity"),
    url(r'^delete-commodity-image/$', csrf_exempt(delete_commodity_image), name="delete-commodity-image"),

    url(r'^list-transfer-type/$', ListTransferType.as_view(), name='list-transfer-type'),
    url(r'^add-transfer-type/$', AddTransferType.as_view(), name='add-transfer-type'),
    url(r'^edit/transfer-type/(?P<transfer_type_id>\d+)/$', EditTransferType.as_view(), name="edit-transfer-type"),
    url(r'^delete-transfer-type/$', csrf_exempt(delete_transfer_type), name="delete-transfer-type"),

    url(r'^list-service/$', ListService.as_view(), name='list-service'),
    url(r'^add-service/$', AddService.as_view(), name='add-service'),
    url(r'^edit/service/(?P<service_id>\d+)/$', EditService.as_view(), name="edit-service"),
    url(r'^delete-service/$', csrf_exempt(delete_service), name="delete-service"),

    url(r'^list-city/$', ListCity.as_view(), name='list-city'),
    url(r'^add-city/$', AddCity.as_view(), name='add-city'),
    url(r'^edit/city/(?P<city_id>\d+)/$', EditCity.as_view(), name="edit-city"),
    url(r'^edit/district/(?P<city_id>\d+)/$', EditDistrict.as_view(), name="edit-dist"),
    url(r'^delete-city/$', csrf_exempt(delete_city), name="delete-city"),

    url(r'^list-discount/$', ListDiscount.as_view(), name='list-discount'),
    url(r'^add-discount/$', AddDiscount.as_view(), name='add-discount'),
    url(r'^edit/discount/(?P<discount_id>\d+)/$', EditDiscount.as_view(), name="edit-discount"),
    url(r'^delete-discount/$', csrf_exempt(delete_discount), name="delete-discount"),

    url(r'^list-truck-crew/$', ListTruckCrew.as_view(), name='list-truck-crew'),
    url(r'^add-truck-crew/$', AddTruckCrew.as_view(), name='add-truck-crew'),
    url(r'^edit/truck-crew/(?P<crew_id>\d+)/$', EditTruckCrew.as_view(), name="edit-truck-crew"),
    url(r'^delete-truck-crew/$', csrf_exempt(delete_truck_crew), name="delete-truck-crew"),

    url(r'^set-session/$', csrf_exempt(set_session), name="set-session"),

    url(r'^manage-users/$', UserManagement.as_view(), name='manage-users'),

    url(r'^manage-fleets/(?P<status>\D+)$', FleetManagement.as_view(), name='manage-fleets'),
    url(r'^approve-user/$', ApproveUser.as_view(), name='approve-user'),
    url(r'^delete-user/$', DeleteUser.as_view(), name='delete-user'),
    url(r'^user/block-unblock/$', BlockUnblockUser.as_view(), name='block-unblock-user'),

    url(r'^manage-partners/(?P<status>\D+)$', PartnerManagement.as_view(), name='manage-partners'),
    url(r'^partner/view/(?P<vehicle_id>\d+)/$', csrf_exempt(PartnerDetailsApi.as_view()), name='partner-view'),
    # url(r'^add-partner/$', AddPartner.as_view(), name='add-partner'),
    # url(r'^verify-mobile/$', csrf_exempt(verify_mobile), name="verify-mobile"),
    # url(r'^verify-otp/$', csrf_exempt(verify_otp), name="verify-otp"),
    # url(r'^approve-partner/$', ApprovePartner.as_view(), name='approve-partner'),
    # url(r'^delete-partner/$', DeletePartner.as_view(), name='delete-partner'),
    # url(r'^partner/block-unblock/$', BlockUnblockFleet.as_view(), name='block-unblock-partner'),
    url(r'^damage-reports/$', DamageReportManagement.as_view(), name='damage-reports'),
    url(r'^damage/view/(?P<transfer_id>\d+)/$', DamageDetailsApi.as_view(), name='damage-view'),
    url(r'^update-panalty/$', csrf_exempt(update_penalty), name="update-panalty"),
    url(r'^payout-management/$', PayoutManagement.as_view(), name="payout-management"),
    url(r'^generate-payout/$', csrf_exempt(GeneratePartnerPayout.as_view()), name="generate-payout"),
    url(r'^payout-history/(?P<user_id>\d+)/$', PayoutHistoryView.as_view(), name="payout-history"),

    url(r'^commission/manage/$', csrf_exempt(ListFleetAndDriverCommission.as_view()), name="commission-management"),

    # Offer Management URLS
    # Author:Hari
    # Date:12-03-2018

    url(r'^offer-management/$', OfferManagement.as_view(), name='offer-management'),
    url(r'^offer-management-edit/(?P<offer_id>\d+)/$', OfferManagementEdit.as_view(), name='edit-offer'),
    url(r'^delete-offer/$', csrf_exempt(delete_offer), name="delete-offer"),
    url(r'^delete-assistant/$', csrf_exempt(delete_assistant), name="delete-assistant"),
    url(r'^edit-assistants/$', csrf_exempt(edit_assistant), name="edit-assistant"),
    url(r'^get-trucks/$', csrf_exempt(get_truck.as_view()), name="get-truck"),

    url(r'^rental-management/$', RentalManagement.as_view(), name='rental-management'),
    url(r'^view-rental/(?P<transfer_id>\d+)/$', ViewRental.as_view(), name="view-rental"),

    url(r'^list-security-deposit/$', SecurityDepositList.as_view(), name='list-security-deposit'),
    url(r'^add-security-deposit/$', AddSecurityDeposit.as_view(), name='add-security-deposit'),
    url(r'^update-security-deposit/$', update_security_deposit, name='update-security-deposit'),
    url(r'^edit/security-deposit/(?P<deposit_id>\d+)/$', EditSecurityDeposit.as_view(), name="edit-security-deposit"),
    url(r'^delete-security-deposit/$', csrf_exempt(delete_security_deposit), name="delete-security-deposit"),

    url(r'^delete-district/(?P<district_id>\d+)/$', csrf_exempt(DeleteDistrict), name="delete-district"),
    url(r'^request-refund/(?P<transfer_id>\d+)/$', csrf_exempt(RefundInitiate), name="request-refund"),
    url(r'^update-district/$', csrf_exempt(UpdateDistrict), name="update-district"),
    url(r'^refunds/$', RefundList.as_view(), name="refunds"),
    url(r'^refund-transfer/$', csrf_exempt(RefundTransfer), name="refunds-transfer"),
    url(r'^refunds/(?P<status>\D+)/(?P<refund_id>\d+)/$', csrf_exempt(RefundStatus), name="refund-status"),
    url(r'^trip-details/(?P<driver_id>\d+)/$', TripHistory.as_view(), name="trip-details"),
    url(r'^logs/$', LogView.as_view(), name="logs"),

    # # Operator Admin management
    url(r'^list-operator/$', ListOperator.as_view(), name='list-operator'),
    url(r'^add-operator/$', AddOperator.as_view(), name='add-operator'),
    url(r'^edit-operator/(?P<operator_id>\d+)/$', EditOperator.as_view(), name="edit-operator"),
    url(r'^delete-operator/$', csrf_exempt(delete_operator), name="delete-operator"),
    url(r'^trip-list/$', csrf_exempt(RentalList.as_view()), name="trip-list"),
    # url(r'^delete-admin/$', DeleteAdmin.as_view(), name='delete-admin'),
    url(r'^trucktypes/$', TruckTypes.as_view(), name="trucktypes"),
    url(r'^add-truckcategory/$', AddTruckCategory.as_view(), name = 'add-truckcategory'),
    url(r'^delete-truck-category/$', csrf_exempt(delete_truck_category), name="delete-truck-category"),
    url(r'^update-handling-fee/$', csrf_exempt(UpdateHandlingFee.as_view()), name="update-handling-fee"),
    url(r'^add-promotion/$', AddPromotion.as_view(), name='add-promotion'),
    url(r'^edit-promotion/(?P<promotion_id>\d+)/$', EditPromotion.as_view(), name='edit-promotion'),
    url(r'^delete-promotion',csrf_exempt(delete_promotion),name='delete-promotion'),
    # #Advertisemnt
    url(r'^add-advertisement/$', AddAdvertisement.as_view(), name='add-advertisement'),
    url(r'^edit-advertisement/(?P<ads_id>\d+)/$', EditAdvertisement.as_view(), name='edit-advertisement'),
    url(r'^delete-advertisement/', csrf_exempt(delete_advertisement), name='delete-advertisement'),

    url(r'^add-on-off-switch/', AddOnOffSwitch.as_view(), name='add-on-off-switch'),
    url(r'^sharing-trip-users/(?P<transfer_id>\d+)/$', SharingTripUser.as_view(), name='sharing-trip-users'),
    url(r'^sharing-trip-partners/$', SharingTripPartner.as_view(), name='sharing-trip-partner'),
    url(r'^trip-list-server/$', csrf_exempt(TripList.as_view()), name='trip-list-server'),
    url(r'^turn-system-off/(?P<status>\d+)/$', TurnSystemOff.as_view(), name='turn-system-off'),
]
