from django.contrib import admin
from api_base.models import *


class AdminDisplay(admin.ModelAdmin):

    def __init__(self, model, admin_site):
        self.list_display = ['id']
        self.list_display += [field.name for field in model._meta.fields if field.name != "id"]
        super(AdminDisplay, self).__init__(model, admin_site)

# Register your models here.


class NotificationsAdmin(admin.ModelAdmin):
  list_display = ('message_headline', 'message', 'transfer_id')


admin.site.register(BaseProfile, AdminDisplay)
admin.site.register(UserProfile, AdminDisplay)
admin.site.register(Assistants, AdminDisplay)
admin.site.register(Attachments, AdminDisplay)
admin.site.register(VehicleDetails, AdminDisplay)
admin.site.register(NotificationsSettings, AdminDisplay)
admin.site.register(Commodity, AdminDisplay)
admin.site.register(TransferType, AdminDisplay)
admin.site.register(Service, AdminDisplay)
admin.site.register(Transfer, AdminDisplay)
admin.site.register(Damage, AdminDisplay)
admin.site.register(DamagePhotos, AdminDisplay)
admin.site.register(DamageDescriptions, AdminDisplay)
admin.site.register(TruckRequest, AdminDisplay)
admin.site.register(Rating, AdminDisplay)
admin.site.register(Documents, AdminDisplay)
admin.site.register(Notifications, AdminDisplay)
admin.site.register(NotificationHistory, AdminDisplay)
admin.site.register(TruckCrew, AdminDisplay)
admin.site.register(TransferLocation, AdminDisplay)
admin.site.register(ServiceableArea, AdminDisplay)
admin.site.register(City, AdminDisplay)
admin.site.register(District, AdminDisplay)
admin.site.register(Discount, AdminDisplay)
admin.site.register(TransferCommodity, AdminDisplay)
admin.site.register(DriveStatusHistory, AdminDisplay)
admin.site.register(DriverOffer, AdminDisplay)
admin.site.register(PayoutHistory, AdminDisplay)
admin.site.register(Transaction, AdminDisplay)
admin.site.register(RefundManagement, AdminDisplay)
admin.site.register(SearchFailedLog, AdminDisplay)
admin.site.register(TruckTypes, AdminDisplay)

# class TruckCrewAdmin(admin.ModelAdmin):
#     list_display = ('capacity_from', 'capacity_to', 'no_drivers', 'loading_peoples')



#
# class TransferCommodityAdmin(admin.ModelAdmin):
#     list_per_page = 950




