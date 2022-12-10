# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
from django.utils import translation


class BenchmarkMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if "language" not in request.session:
            request.session['language'] = 'span'
        try:
            if request.session['language'] == 'en':
                request.lbl_login_no_permission = "You don't have permission to access this area"
                request.lbl_welcome = "Welcome "
                request.lbl_accnt_not_active = "Your account is not active. Please contact the Administrator."
                request.lbl_invalid_username_password = "Username / password invalid. Try again"
                request.lbl_provide_valid_username_password = "Provide a valid username / password"
                request.lbl_password_changed_success = "Changed your password successfully. Please login with your new password"
                request.lbl_incorrect_old_password = "Provided that the previous password is not correct. Try again"
                request.lbl_old_password_new_password_same = "New Password should not be same as old password"
                request.lbl_provide_valid_data = "Please provide valid data"
                request.lbl_invalid_user = "Invalid User"
                request.lbl_profile_details_updated = "Profile Details Updated"
                request.lbl_added_new_commodity = "New Item added"
                request.lbl_commodity_already_exist = "Item Already Exists"
                request.lbl_commodity_deleted = "Item Deleted"
                request.lbl_commodity_image_deleted = "Item Image Deleted"
                request.lbl_invalid_commodity = "Invalid Item ID"
                request.lbl_no_entry = "No such Entry"
                request.lbl_admin_up_success = "Admin Details Updated successfully"
                request.lbl_invalid_admin = "Invalid Admin Id"
                request.lbl_admin_deleted = "Administrator Deleted"
                request.lbl_added_admin_success = "Added a new administrator with email"
                request.lbl_another_username_exists = "Another user with same username exist"
                request.lbl_another_mobile_exists = "Another user with same mobile number exist"
                request.lbl_commodity_update = "Commodity updated successfully"
                request.new_acc_info_added = "A new account has been created with your email address"
                request.lbl_login_txt = "Login"
                request.lbl_password_txt = "Password"
                request.lbl_forgot_pwd_link_reset = "Click the below button to reset your password. The link will only be valid for 1 hour"
                request.lbl_reset_pwd = "Reset Password"
                request.lbl_email_sent_to = "We have sent an email to"
                request.lbl_with_reset_link = "with a link to reset your password"
                request.lbl_page_redirect_5_sec = "Page will be automatically redirected after 5 seconds"
                request.lbl_conf_mail = "Confirmation Mail"
                request.lbl_reset_password_success = "Password reset successfully. Please try to login"

                request.lbl_added_new_transfer_type = "New Density Factor added"
                request.lbl_transfer_type_already_exist = "Density Factor Already Exists"
                request.lbl_transfer_type_deleted = "Density Factor Deleted"
                request.lbl_invalid_transfer_type = "Invalid Density Factor ID"
                request.lbl_transfer_type_update = "Density Factor updated successfully"

                request.lbl_added_new_service = "New Service added"
                request.lbl_service_already_exist = "Service Name Already Exists"
                request.lbl_service_deleted = "Service Deleted"
                request.lbl_invalid_service = "Invalid Service ID"
                request.lbl_service_update = "Service updated successfully"

                request.lbl_added_new_city = "New City added"
                request.lbl_city_already_exist = "City Already Exists"
                request.lbl_city_deleted = "City Deleted"
                request.lbl_invalid_city = "Invalid City ID"
                request.lbl_city_update = "City updated successfully"

                request.lbl_profile_image_deleted = "Profile Image Deleted"

                request.lbl_added_new_discount = "Discount added"
                request.lbl_discount_already_exist = "Discount Already Exists"
                request.lbl_discount_deleted = "Discount Deleted"
                request.lbl_invalid_discount = "Invalid Discount ID"
                request.lbl_discount_update = "Discount updated successfully"

                request.lbl_added_new_truck_crew = "Truck Details added"
                request.lbl_truck_crew_already_exist = "Truck Details Already Exists"
                request.lbl_truck_crew_deleted = "Truck Crew Details Deleted"
                request.lbl_helper_deleted = "Deleted helper"
                request.lbl_invalid_truck_crew = "Invalid Truck Details ID"
                request.lbl_truck_crew_update = "Truck Details updated successfully"

                request.lbl_user_blocked = "Blocked User"
                request.lbl_user_unblocked = "Unblocked User"

                request.lbl_new_registrations = "New Fleet Registrations"
                request.lbl_fleet_approved = "Approved Fleet Manager"
                request.lbl_fleet_deleted = "Fleet Manager Deleted"
                request.lbl_fleet_blocked = "Blocked Fleet Managers"
                request.lbl_fleet_unblocked = "Unblocked Fleet Manager"

                request.lbl_new_partner_registrations = "New Truck Registrations"
                request.lbl_partner_approved_regns = "Approved Truck Registrations "
                request.lbl_partner_deleted = "Deleted Truck Registrations"
                request.lbl_partner_blocked_regns = "Blocked Trucks"
                request.lbl_partner_approved = "Approved Truck "
                request.lbl_partner_blocked = "Blocked Truck "
                request.lbl_partner_unblocked = "Unblocked Truck "
                request.lbl_security_amount_updated = "Security Deposit Updated"
                request.lbl_fleet_signup_success1 = "Fleet registration with email"
                request.lbl_fleet_signup_success2 = " has been completed successfully. " \
                                                    "You can login after approval of Administrator which will be notified by an email. "
                request.lbl_dear_user = "Dear"
                request.lbl_fleet_account_with_email = "Your fleet account associated with the email"
                request.lbl_partner_account = "Your Driver account "
                request.lbl_account_approved = "has been approved by the Muberz Administrator. Please try to login with your credentials"
                request.lbl_muberz_team = "Muberz Team"
                request.lbl_fleet_reg_approved = "Fleet Registration has been approved by Muberz Administration"
                request.lbl_partner_reg_approved = "Driver Registration has been approved by Muberz Administration"

                request.lbl_damages_reported = "Damages Reported"
                request.lbl_penalty_added = "Penalty Amount Updated"
                request.lbl_add_penalty_after_48_hours = "The penalty amount can only be updated after 48 hours of transfer time"
                request.lbl_invalid_transfer = "Invalid Transfer ID"

                request.lbl_document_added = "Document Uploaded"
                request.lbl_partner_details_added = "New truck details added"
                request.lbl_partner_registrations = "Trucks"
                request.lbl_basic_details_updated = "Basic Profile Details Updated"
                request.lbl_updated_commission = "Updated commission"

                request.lbl_no_vehicle_message = "Driver don't have any vehicle attached"
                request.lbl_trip_cancelled = "Trip cancelled successfully"
                """Menu for Offer Management"""
                request.lbl_offers = "Offers"
                request.lbl_add_offer = "Add Offer"
                request.lbl_list_offer = "Offer List"
                request.lbl_offermgmt_success = "Added Offer Successfully"
                request.lbl_offermgmt_failed = "Failed to add offer"
                request.lbl_offermgmt_validation = "Fields cannot be blank"
                request.lbl_offer_deleted = "Offer Deleted Successfuly"
                request.lbl_invalid_offer = "Invalid Offer"

                request.lbl_rentals = "All Trips"

                request.lbl_added_security_deposit = "Security Deposit added"
                request.lbl_security_deposit_already_exist = "Security Deposit Already Exists"
                request.lbl_security_deposit_deleted = "Security Deposit Details Deleted"
                request.lbl_invalid_security_deposit = "Invalid Security Deposit ID"
                request.lbl_security_deposit_update = "Security Deposit updated successfully"
                request.lbl_provide_volume_between_0_40 = "Please enter valid Truck Volume"

                request.lbl_payout_error_message = "Payouts can only be processed on"

                request.lbl_operator_up_success = "Operator Details Updated successfully"
                request.lbl_invalid_operator = "Invalid Operator Id"
                request.lbl_operator_deleted = "Operator Deleted"
                request.lbl_added_operator_success = "Added a new operator with email"
                request.new_operator_info_added = "A new operator account has been created with your email address"
                request.lbl_fleet_truck_approved ="Truck you have added associated with the mobile number {0} has been approved by the Muberz Administrator"
                request.lbl_fleet_truck_approved_heading = "Your Truck has been approved"


            else:
                request.lbl_login_no_permission = "No tienes permiso para acceder a esta área"
                request.lbl_welcome = "Bienvenido "
                request.lbl_accnt_not_active = "Su cuenta no está activa. Por favor contacte al administrador."
                request.lbl_invalid_username_password = "Usuario / contraseña invalida. Inténtalo de nuevo "
                request.lbl_provide_valid_username_password = "Proporcione un nombre de usuario / contraseña válidos "
                request.lbl_password_changed_success = "Cambió su contraseña exitosamente. Por favor inicie sesión con su nueva contraseña "
                request.lbl_incorrect_old_password = "Cambió su contraseña exitosamente. Por favor inicie sesión con su nueva contraseña "
                request.lbl_old_password_new_password_same = "La nueva contraseña no debe ser igual a la contraseña anterior"
                request.lbl_provide_valid_data = "Por favor proporcione datos válidos"
                request.lbl_invalid_user = "Usuario invalido"
                request.lbl_profile_details_updated = "Detalles del perfil actualizados"
                request.lbl_added_new_commodity = "Nueva mercancía añadida"
                request.lbl_commodity_already_exist = "La materia prima ya existe"
                request.lbl_commodity_deleted = "Producto eliminado"
                request.lbl_commodity_image_deleted = "Imagen de productos eliminados"
                request.lbl_invalid_commodity = "ID de mercancía no válida"
                request.lbl_no_entry = "No hay tal entrada"
                request.lbl_admin_up_success = "Detalles de administrador actualizados con éxito"
                request.lbl_invalid_admin = "ID de administrador no válido"
                request.lbl_admin_deleted = "Administrador eliminado"
                request.lbl_added_admin_success = "Se agregó un nuevo administrador con correo electrónico"
                request.lbl_another_username_exists = "Otro usuario con el mismo nombre de usuario existe"
                request.lbl_another_mobile_exists = "Otro usuario con el mismo número de móvil existe"
                request.lbl_commodity_update = "Producto actualizado con éxito"
                request.new_acc_info_added = "Se ha creado una nueva cuenta con su dirección de correo electrónico"
                request.lbl_login_txt = "Iniciar sesión"
                request.lbl_password_txt = "Contraseña"
                request.lbl_forgot_pwd_link_reset = "Haga clic en el botón a continuación para restablecer su contraseña. El enlace solo será válido por 1 hora"
                request.lbl_reset_pwd = "Restablecer la contraseña"
                request.lbl_email_sent_to = "Hemos enviado un correo electrónico a"
                request.lbl_with_reset_link = "con un enlace para restablecer su contraseña"
                request.lbl_page_redirect_5_sec = "La página será redirigida automáticamente después de 5 segundos"
                request.lbl_conf_mail = "Correo de confirmación"
                request.lbl_reset_password_success = "Restablecimiento de contraseña exitosamente. Por favor intente iniciar sesión"

                request.lbl_added_new_transfer_type = "Tipo de transferencia agregado"
                request.lbl_transfer_type_already_exist = "El tipo de transferencia ya existe"
                request.lbl_transfer_type_deleted = "Tipo de transferencia eliminado"
                request.lbl_invalid_transfer_type = "ID de tipo de transferencia no válido"
                request.lbl_transfer_type_update = "Tipo de transferencia actualizado con éxito"

                request.lbl_added_new_service = "Servicio agregado"
                request.lbl_service_already_exist = "El servicio ya existe"
                request.lbl_service_deleted = "Servicio eliminado"
                request.lbl_invalid_service = "ID de servicio inválido"
                request.lbl_service_update = "Servicio actualizado con éxito"

                request.lbl_added_new_city = "Nueva ciudad agregada"
                request.lbl_city_already_exist = "La ciudad ya existe"
                request.lbl_city_deleted = "Ciudad eliminada"
                request.lbl_invalid_city = "ID de la ciudad no válida"
                request.lbl_city_update = "Ciudad actualizada con éxito"

                request.lbl_profile_image_deleted = "Profilo bildo forigita"

                request.lbl_added_new_discount = "Descuento agregado"
                request.lbl_discount_already_exist = "El descuento ya existe"
                request.lbl_discount_deleted = "Descuento eliminado"
                request.lbl_invalid_discount = "ID de descuento no válido"
                request.lbl_discount_update = "Descuento actualizado con éxito"

                request.lbl_added_new_truck_crew = "Detalles del camión agregados"
                request.lbl_truck_crew_already_exist = "Los detalles de camiones ya existen"
                request.lbl_truck_crew_deleted = "Detalles de la tripulación de camiones eliminados"
                request.lbl_helper_deleted = "Ayuda eliminada"
                request.lbl_invalid_truck_crew = "ID de detalles inválidos"
                request.lbl_truck_crew_update = "Camión actualizado con éxito"

                request.lbl_user_blocked = "Usuario bloqueado"
                request.lbl_user_unblocked = "Usuario desbloqueado"

                request.lbl_new_registrations = "Nuevos registros de flota"
                request.lbl_fleet_approved = "Gerente de Flota Aprobado"
                request.lbl_fleet_deleted = "Administrador de flota eliminado"
                request.lbl_fleet_blocked = "Gerente bloqueado de la flota"
                request.lbl_fleet_unblocked = "Administrador de flota desbloqueado"

                request.lbl_new_partner_registrations = "Nuevos registros de camiones"
                request.lbl_partner_approved_regns = "Registros de camiones aprobados "
                request.lbl_partner_deleted = "Eliminación de registros de camiones"
                request.lbl_partner_blocked_regns = "Camiones bloqueados"
                request.lbl_partner_approved = "Camión aprobado "
                request.lbl_partner_blocked = "Camión bloqueado "
                request.lbl_partner_unblocked = "Camión desbloqueado "
                request.lbl_security_amount_updated = "Depósito de seguridad actualizado"
                request.lbl_fleet_signup_success1 = "Registro de flota con correo electrónico"
                request.lbl_fleet_signup_success2 = " ha sido completado exitosamente Puede iniciar sesión después de la aprobación del Administrador, se le notificará por correo electrónico. "

                request.lbl_dear_user = "Estimado"
                request.lbl_fleet_account_with_email = "Su cuenta de flota asociada con el correo electrónico"
                request.lbl_partner_account = "Su registro de conductor"
                request.lbl_account_approved = "ha sido aprobado por el Administrador de Muberz. Por favor, intente iniciar sesión con sus credenciales"
                request.lbl_muberz_team = "Equipo Muberz"
                request.lbl_fleet_reg_approved = "El registro de la flota ha sido aprobado por la administración de Muberz"
                request.lbl_partner_reg_approved = "El registro de conductor ha sido aprobado por la administración de Muberz"

                request.lbl_damages_reported = "Daños Reportados"
                request.lbl_penalty_added = "Monto de penalización actualizado"
                request.lbl_add_penalty_after_48_hours = "La cantidad de penalización solo se puede actualizar después de 48 horas de tiempo de transferencia"
                request.lbl_invalid_transfer = "ID de transferencia inválida"
                request.lbl_document_added = "Documento cargado"

                request.lbl_partner_details_added = "Nuevos detalles del controlador agregados"
                request.lbl_partner_registrations = "Vehículos"
                request.lbl_basic_details_updated = "Detalles básicos del perfil actualizados"
                request.lbl_updated_commission = "Comisión actualizada"

                request.lbl_no_vehicle_message = "El conductor no tiene ningún vehículo conectado"
                request.lbl_trip_cancelled = "Viaje cancelado exitosamente"
                """Menu for Offer Management"""
                request.lbl_offers = "Ofertas"
                request.lbl_add_offer = "Agregar oferta"
                request.lbl_list_offer = "Lista de ofertas"

                request.lbl_offermgmt_success = "Oferta agregada con éxito"
                request.lbl_offermgmt_failed = "La oferta no se pudo agregar"
                request.lbl_offermgmt_validation = "Los campos no pueden estar en blanco"
                request.lbl_offer_deleted = "Oferta eliminada con éxito"
                request.lbl_invalid_offer = "Oferta inválida"

                request.lbl_rentals = "Servicios"

                request.lbl_added_security_deposit = "Depósito de seguridad agregado"
                request.lbl_security_deposit_already_exist = "El depósito de seguridad ya existe"
                request.lbl_security_deposit_deleted = "Detalles de depósito de seguridad eliminados"
                request.lbl_invalid_security_deposit = "ID de depósito de seguridad inválido"
                request.lbl_security_deposit_update = "Depósito de seguridad actualizado con éxito"
                request.lbl_provide_volume_between_0_40 = "Por favor ingrese el Volumen de camión válido"

                request.lbl_payout_error_message = "Payouts can only be processed on"

                request.lbl_operator_up_success = "Detalles del operador Actualizado con éxito"
                request.lbl_invalid_operator = "Identificador de operador inválido"
                request.lbl_operator_deleted = "Operador eliminado"
                request.lbl_added_operator_success = "Se agregó un nuevo operador con correo electrónico"
                request.new_operator_info_added = "Se ha creado una nueva cuenta de operador con su dirección de correo electrónico"

                request.lbl_fleet_truck_approved = "El camión que ha agregado asociado con el número de móvil {0} ha sido aprobado por el Administrador de Muberz"
                request.lbl_fleet_truck_approved_heading = "Su camión ha sido aprobado"


        except:
            request.session['language'] = 'span'
        return self.get_response(request)

    def process_template_response(self, request, response):
        if "language" not in request.session:
            request.session['language'] = 'span'
        try:
            if request.session['language'] == 'en':
                response.context_data['username'] = 'Username'
                response.context_data['password'] = 'Password'
                response.context_data['user_type'] = 'Type'
                response.context_data['login'] = 'Login'
                response.context_data['fleet_signup'] = 'Fleet Registration'
                response.context_data['company_name'] = 'Company Name'
                response.context_data['address'] = 'Address'
                response.context_data['ceo_id_proof'] = "CEO's ID Proof"
                response.context_data['superadmin'] = 'Super Admin'
                response.context_data['management'] = 'Management'
                response.context_data['lbl_commodity'] = 'Items Listing & Pricing'
                response.context_data['lbl_commodity_list'] = 'Items List'
                response.context_data['lbl_is_plugable'] = 'Is plugable Item'
                response.context_data['lbl_item'] = 'Item'
                response.context_data['lbl_registration_no'] = "Registration Number"
                response.context_data['lbl_assistants'] = "Helpers"
                response.context_data['lbl_volume'] = 'Volume'
                response.context_data['lbl_length'] = 'Length'
                response.context_data['lbl_breadth'] = 'Breadth'
                response.context_data['lbl_height'] = 'Height'
                response.context_data['lbl_material_type'] = 'Material Type'
                response.context_data['lbl_charge'] = 'Charge'
                response.context_data['lbl_installation_charge'] = 'Installation Charge'
                response.context_data['lbl_image'] = 'Image'
                response.context_data['lbl_upload_file'] = 'Upload'
                response.context_data['lbl_profile_photo'] = 'Profile Photo'
                response.context_data['lbl_edit'] = 'Edit'
                response.context_data['lbl_districts'] = 'List Districts'
                response.context_data['delete'] = 'Delete'
                response.context_data['no_items_found'] = 'No items found'
                response.context_data['lbl_search'] = 'Search'
                response.context_data['lbl_previous'] = 'Previous'
                response.context_data['lbl_next'] = 'Next'
                response.context_data['lbl_export'] = 'Export'
                response.context_data['lbl_showing'] = 'Showing'
                response.context_data['lbl_entries'] = 'records'
                response.context_data['lbl_display'] = 'Show'
                response.context_data['add_new_commodity'] = 'Add New Item'
                response.context_data['lbl_submit'] = 'Submit'
                response.context_data['lbl_upd_commodity'] = 'Update Commodity'
                response.context_data['lbl_update'] = 'Update'
                response.context_data['want_to_delete'] = 'Do you want to delete this Commodity?'
                response.context_data['lbl_want_to_delete_image'] = 'Do you want to delete this image?'
                response.context_data['admins'] = 'Administrators'
                response.context_data['update_admins'] = 'Update administration details'
                response.context_data['first_name'] = 'First Name'
                response.context_data['last_name'] = 'Last Name'
                response.context_data['admin_det_up_success'] = 'Admin details updated successfully'
                response.context_data['lbl_admin_list'] = 'Admin List'
                response.context_data['lbl_name'] = 'Name'
                response.context_data['lbl_email'] = 'Email'
                response.context_data['lbl_add_new_admin'] = 'Add New Admin'
                response.context_data['lbl_want_del_user'] = 'Do you want to delete this User?'
                response.context_data['lbl_change_password'] = 'Change Password'
                response.context_data['lbl_old_password'] = 'Old Password'
                response.context_data['lbl_new_password'] = 'New Password'
                response.context_data['lbl_reset_changes'] = 'Reset Changes'
                response.context_data['lbl_update_profile'] = 'Update Profile'
                response.context_data['lbl_profile_picture'] = 'Profile Picture'
                response.context_data['lbl_validating_and_uploading'] = 'Validating and Uploading...'
                response.context_data['lbl_footer'] = 'Copyright © 2017 Muberz. All Rights Reserved.'
                response.context_data['lbl_forgot_password'] = 'Forgot password'
                response.context_data['lbl_dont_have_account'] = "Don't have an account?"
                response.context_data['lbl_fleet_registration'] = "Fleet Registration"
                response.context_data['lbl_enter_email'] = 'Enter email'
                response.context_data['lbl_send_email'] = 'Send Email'
                response.context_data['lbl_sign_in'] = 'Sign In'
                response.context_data['lbl_sign_up'] = 'Sign Up'
                response.context_data['lbl_invalid_reset_key'] = 'Reset key is invalid or it expired'
                response.context_data['lbl_reset_pwd_txt'] = "Reset Password"
                response.context_data['lbl_enter_pwd_txt'] = "Enter new password"

                response.context_data['lbl_transfer_type'] = 'Transfer Types & Pricing'
                response.context_data['lbl_transfer_from'] = 'Transfer From'
                response.context_data['lbl_transfer_to'] = 'Transfer To'
                response.context_data['lbl_transfer_type_list'] = 'Transfer Type List'
                response.context_data['add_new_transfer_type'] = 'Add new Transfer Type'
                response.context_data['lbl_upd_transfer_type'] = 'Update Transfer Type'
                response.context_data['lbl_want_to_delete_transfer_type'] = 'Do you want to delete this Transfer Type?'

                response.context_data['lbl_service_name'] = 'Service Name'
                response.context_data['lbl_service_name_en'] = 'Service Name(En)'
                response.context_data['lbl_service_name_es'] = 'Service Name(Es)'
                response.context_data['lbl_description_en'] = 'Description(En)'
                response.context_data['lbl_description_es'] = 'Description(Es)'

                response.context_data['lbl_services'] = 'Service Types Setting'
                response.context_data['lbl_service_list'] = 'Service List'
                response.context_data['lbl_add_new_service'] = 'Add new Service'
                response.context_data['lbl_upd_service'] = 'Update Service'
                response.context_data['lbl_want_to_delete_service'] = 'Do you want to delete this Service?'

                response.context_data['lbl_city_name'] = 'City Name'
                response.context_data['lbl_cities'] = 'Cities'
                response.context_data['lbl_city_list'] = 'City List'
                response.context_data['lbl_add_new_city'] = 'Add City'
                response.context_data['lbl_upd_city'] = 'Update City'
                response.context_data['lbl_want_to_delete_city'] = 'Do you want to delete this City?'

                response.context_data['lbl_validation_item_name'] = 'Please enter Item Name'
                response.context_data['lbl_validation_length'] = 'Please enter Length'
                response.context_data['lbl_validation_breadth'] = 'Please enter Breadth'
                response.context_data['lbl_validation_height'] = 'Please enter Height'
                response.context_data['lbl_validation_material_type'] = 'Please Enter material type'
                response.context_data['lbl_validation_charge'] = 'Please Enter charge'
                response.context_data['lbl_validation_icon'] = 'Please Choose an icon image'

                response.context_data['lbl_validation_company_name'] = 'Please enter Company Name'
                response.context_data['lbl_validation_address'] = 'Please enter Address'
                response.context_data['lbl_validation_email'] = 'Please enter Email'
                response.context_data['lbl_validation_password'] = 'Please enter Password'
                response.context_data['lbl_validation_proof'] = 'Please Choose identity Proof of CEO'
                response.context_data['lbl_choose_city'] = 'Please choose a city'

                response.context_data['lbl_discount'] = 'Discount'
                response.context_data['lbl_service'] = 'Service'
                response.context_data['lbl_price_range'] = 'Price Range'
                response.context_data['lbl_discount_list'] = 'Discount List'
                response.context_data['add_new_discount'] = 'Add new Discount'
                response.context_data['lbl_upd_discount'] = 'Update Discount'
                response.context_data['lbl_want_to_delete_discount'] = 'Do you want to delete this Discount?'

                response.context_data['lbl_app_users'] = "Users"
                response.context_data['lbl_mobile'] = "Mobile"
                response.context_data['lbl_status'] = "Status"
                response.context_data['lbl_rating'] = "Rating"
                response.context_data['lbl_approved_on'] = "Approved On"
                response.context_data['lbl_joining_date'] = "Registration Date"
                response.context_data['lbl_action'] = "Action"
                response.context_data['lbl_block'] = "Block"
                response.context_data['lbl_unblock'] = "Unblock"
                response.context_data['lbl_total_earnings'] = "Total Earnings"

                response.context_data['lbl_approve'] = "Approve"
                response.context_data['lbl_fleets'] = "Fleet Managers"
                response.context_data['lbl_new_fleets'] = "New Fleet Registrations"
                response.context_data['lbl_blocked_fleets'] = "Blocked Fleet Managers"

                response.context_data['lbl_partners'] = "Trucks"
                response.context_data['lbl_new_partners'] = "New Truck Registrations"
                response.context_data['lbl_blocked_partners'] = "Blocked Trucks"
                response.context_data['lbl_vehicle_volume'] = "Vehicle Volume"
                response.context_data['lbl_vehicle_height'] = "Vehicle Height"
                response.context_data['lbl_fleet_name'] = "Fleet"

                response.context_data['lbl_add_partner'] = "Add Truck"
                response.context_data['lbl_serviceable_area'] = 'Serviceable Area'
                response.context_data['lbl_fleet_or_individual'] = 'Fleet/Individual'
                response.context_data['lbl_driver_licence'] = 'Driver License'
                response.context_data['lbl_commercial_insurance'] = 'Commercial Insurance'
                response.context_data['lbl_vehicle_registration'] = 'Vehicle Registration Certificate'
                response.context_data['lbl_fitness_certificate'] = 'Fitness Certificate'
                response.context_data['lbl_tax_certificate'] = 'Tax Certificate'
                response.context_data['lbl_deposit_amount'] = 'Deposit Amount'
                response.context_data['lbl_individual'] = 'Individual'
                response.context_data['lbl_amount'] = 'Recharge Amount'

                response.context_data['lbl_crew_mgmt'] = 'Crew Management'
                response.context_data['lbl_add_new_crew'] = 'Add New'
                response.context_data['lbl_crew_list'] = 'Truck Crew List'
                response.context_data['lbl_truck_capacity'] = 'Truck Capacity'
                response.context_data['lbl_loaders'] = 'Number of Loaders'
                response.context_data['lbl_drivers'] = 'Number of Drivers'
                response.context_data['lbl_capacity_from'] = 'Capacity From'
                response.context_data['lbl_capacity_to'] = 'Capacity To'
                response.context_data['lbl_want_to_delete_crew'] = 'Do you want to delete this Crew?'
                response.context_data['lbl_upd_crew'] = 'Update Truck Crew'

                response.context_data['lbl_damages_reported'] = "Damages Reported"
                response.context_data['lbl_transfer_on'] = "Transfer On"
                response.context_data['lbl_transfer_loc'] = "Transfer Location"
                response.context_data['lbl_driver_name'] = "Driver Name"
                response.context_data['lbl_transfer_amount'] = "Total Amount"
                response.context_data['lbl_amount_paid'] = "Amount Paid"
                response.context_data['lbl_damaged_items'] = "Damaged Items"
                response.context_data['lbl_damage_type'] = "Damage Type"
                response.context_data['lbl_open'] = "Not Resolved"
                response.context_data['lbl_closed'] = "Resolved"
                response.context_data['lbl_penalty'] = "Penalty Amount"
                response.context_data['lbl_penalty_amt_already_added'] = "The amount of penalty was already added against these damaged items"
                response.context_data['lbl_trip_type'] = "Type"
                response.context_data['instant_transfer'] = "Instant Transfer"
                response.context_data['scheduled_transfer'] = "Scheduled Transfer"

                response.context_data['lbl_list_documents'] = 'Document List'
                response.context_data['lbl_doc_type'] = 'Document Type'
                response.context_data['lbl_document'] = 'Document'
                response.context_data['lbl_language'] = 'Language'
                response.context_data['lbl_validation_document_type'] = 'Please enter Document Type'
                response.context_data['lbl_validation_language'] = 'Please enter Language'
                response.context_data['lbl_validation_document'] = 'Please choose valid Document'
                response.context_data['lbl_add_update_document'] = 'Add/Update Document'
                response.context_data['lbl_view_file'] = 'View File'

                response.context_data['lbl_validation_name'] = 'Please enter Name'
                response.context_data['lbl_validation_email'] = 'Please enter Valid Email'
                response.context_data['lbl_validation_mobile_number'] = 'Please enter Mobile Number with country code'
                response.context_data['lbl_validation_vehicle_volume'] = 'Please enter valid Vehicle Volume'
                response.context_data['lbl_validation_driver_licence'] = 'Please Choose Driving Licence'
                response.context_data['lbl_validation_commercial_insurance'] = 'Please Choose Commercial Insurance'
                response.context_data['lbl_validation_vehicle_registration'] = 'Please Choose Vehicle Registration'
                response.context_data['lbl_validation_fitness_certificate'] = 'Please Choose Fitness Certificate'
                response.context_data['lbl_validation_tax_certificate'] = 'Please Choose Tax Certificate'

                response.context_data['lbl_profile_not_completed'] = "Profile not Completed"
                response.context_data['lbl_edit_basic_details'] = "Edit Basic Details"
                response.context_data['lbl_basic_details'] = "Basic Details"
                response.context_data['lbl_id_proof'] = "ID Proof"
                response.context_data['lbl_transit_peoples'] = "Helpers"
                response.context_data['lbl_commission_list'] = "Commission List"
                response.context_data['lbl_update_commission'] = "Update Commission"
                response.context_data['lbl_commission'] = "Commission Settings"

                response.context_data['lbl_transfers'] = "Transfers"
                response.context_data['lbl_transfers_details'] = "Transfer Details"

                response.context_data['lbl_user'] = "User"
                response.context_data['lbl_driver'] = "Driver"
                response.context_data['lbl_payment_type'] = "Payment Type"
                response.context_data['lbl_completed_on'] = "Completed On"

                """Menu for Offer Management"""
                response.context_data['lbl_offers'] = "Offers"
                response.context_data['lbl_add_offer'] = "Add Offer"
                response.context_data['lbl_list_offer'] = "Offer List"

                response.context_data['lbl_offer_type'] = "Offer Type"
                response.context_data['lbl_trip_duration'] = "Total Trip Duration"
                response.context_data['lbl_offer_count'] = "Trip Count"
                response.context_data['lbl_offer_from'] = "Valid From"
                response.context_data['lbl_offer_to'] = "Valid To"
                response.context_data['lbl_offer_cashamt'] = "Commission Amount"
                response.context_data['lbl_offer_perc'] = "Reduction in Commission"
                response.context_data['lbl_offer_user'] = "Fleet/User"
                response.context_data['lbl_offer_cash'] = "Cash/Percent"
                response.context_data['lbl_time'] = "Time Based"
                response.context_data['lbl_trip'] = "Trip Based"
                response.context_data['lbl_cash'] = "Cash"
                response.context_data['lbl_perc'] = "Percent"
                response.context_data['lbl_appliedto'] = "Driver/Fleet"
                response.context_data['lbl_user'] = "User"
                response.context_data['lbl_fleet'] = "Fleet"
                response.context_data['lbl_offer_based_on'] = "Condition"
                response.context_data['lbl_daily'] = "Daily"
                response.context_data['lbl_weekly'] = "Weekly"
                response.context_data['lbl_monthly'] = "Monthly"
                response.context_data['lbl_offer_duration'] = "Offer Duration"
                response.context_data['lbl_offer_list'] = "Offer List"
                response.context_data['lbl_want_to_delete_offer'] = "Do you want to delete this offer?"
                response.context_data['lbl_edit_offer'] = "Edit offer"
                response.context_data['lbl_id_proof'] = "Id Proof"
                response.context_data['lbl_vehicle_number'] = "Registration Number"

                response.context_data['lbl_pickup_location'] = "Pickup Location"
                response.context_data['lbl_drop_location'] = "Drop Location"
                response.context_data['lbl_total_amount'] = "Total Amount"

                response.context_data['lbl_view'] = "Details"
                response.context_data['lbl_transfer_details'] = "Transfer Details"

                response.context_data['lbl_no_items'] = "Number of Items"
                response.context_data['lbl_damage_refund'] = "Damage Refund"
                response.context_data['lbl_payable_amount'] = "Balance to be paid"
                response.context_data['lbl_service_type'] = "Service Type"
                response.context_data['lbl_rate_details'] = "Rate Details"

                #Dashboard Reports and active trips
                response.context_data['lbl_active_users'] = "Active Users"
                response.context_data['lbl_active_partners'] = "Active Trucks"
                response.context_data['lbl_active_trips'] = "Active Trips"
                response.context_data['lbl_completed_trips'] = "Completed Trips"
                response.context_data['lbl_damages_reported'] = "Damages Reported"
                response.context_data['lbl_rentals'] = "Trips"

                response.context_data['add_new_density_factor'] = 'Add new Complexity Factor'
                response.context_data['lbl_density_factor'] = 'Complexity Factor'
                response.context_data['lbl_density_factor_list'] = 'Complexity Factors'
                response.context_data['lbl_density_factor_between'] = 'Complexity Factor Between'
                response.context_data['lbl_update_density_factor'] = 'Update Complexity Factor'

                response.context_data['lbl_city_name_validate'] = 'Please choose a valid city name'

                response.context_data['lbl_security_deposit_management'] = 'Security Deposit'
                response.context_data['lbl_add_new_security_deposit'] = 'Add New Security Deposit'
                response.context_data['lbl_security_deposit_list'] = 'Security Deposit List'
                response.context_data['lbl_want_to_delete'] = 'Do you want to delete?'
                response.context_data['lbl_upd_security_deposit'] = 'Update Security Deposit'
                response.context_data['lbl_deposit_needed'] = 'Deposit Needed'

                response.context_data['lbl_payout_management'] = 'Payout Management'
                response.context_data['lbl_payout_history'] = 'Payout History'
                response.context_data['lbl_total_booking_amnt'] = 'Total Booking Amount'
                response.context_data['lbl_net_payable'] = 'Net Payable Amount'

                response.context_data['lbl_add_new_operator'] = 'Add New Operator'
                response.context_data['lbl_operator_list'] = 'Operators List'
                response.context_data['update_operators'] = 'Update Operator details'
                response.context_data['operators'] = 'Operators'

                response.context_data['lbl_details'] = "Details"
                response.context_data['lbl_damage_details'] = "Damage Details"
                response.context_data['lbl_description'] = "Description"
                response.context_data['lbl_stolen'] = "Stolen"
                response.context_data['lbl_fully_damaged'] = "Fully Damaged"
                response.context_data['lbl_truck_types'] = "Truck Types"
                response.context_data['lbl_promotion_list'] = 'Promotions'

                response.context_data['lbl_add_promotion'] = "Add Promotion"
                response.context_data['lbl_promo_name'] = "Name"
                response.context_data['lbl_promo_percentage'] = "Percentage"
                response.context_data['lbl_promo_srtdescription'] = "Short Description"
                response.context_data['lbl_promo_description'] = "description"
                response.context_data['lbl_promo_expiry'] = "expiry"
                response.context_data['lbl_validation_percentage'] = 'enter the correct percentage'
                response.context_data['lbl_validation_short_description'] = 'Please enter the short description'
                response.context_data['lbl_promo'] = 'Promotion Name'
                response.context_data['lbl_percentage'] = 'Percentage'
                response.context_data['lbl_short_description'] = 'Short Description'
                response.context_data['lbl_description'] = 'Description'
                response.context_data['lbl_expiry'] = 'Expiry Date'

                response.context_data['lbl_add_advertisement'] = 'Advertisement'
                response.context_data['lbl_adv_header'] = 'Header'
                response.context_data['lbl_adv_image'] = 'Image'
                response.context_data['lbl_adv_start'] = 'Start Date'
                response.context_data['lbl_adv_end'] = 'End Date'
                response.context_data['lbl_adv_typeof'] = 'Type of Users'
                response.context_data['lbl_adv_list'] = 'Advertisement list'
                response.context_data['lbl_adv_name'] = 'Advertisement Text'
                response.context_data['lbl_adv_users'] = 'Type of users'

                response.context_data['lbl_on_off_switch'] = 'System On/Off'
                response.context_data['lbl_start_time'] = 'Start time'
                response.context_data['lbl_end_time'] = 'End time'
                response.context_data['lbl_reset'] = 'Reset'

                response.context_data['lbl_diver_name'] = 'Driver'
                response.context_data['lbl_new_assignee'] = 'Assignee Name'
                response.context_data['lbl_distance'] = 'Distance'
                response.context_data['lbl_last'] = 'Last'
                response.context_data['lbl_first'] = 'First'

            else:
                response.context_data['username'] = 'Nombre de usuario'
                response.context_data['password'] = 'Contraseña'
                response.context_data['user_type'] = 'Tipo'
                response.context_data['login'] = 'Iniciar sesión'
                response.context_data['fleet_signup'] = 'Registro de flota'
                response.context_data['company_name'] = 'nombre de empresa'
                response.context_data['address'] = 'Dirección'
                response.context_data['ceo_id_proof'] = "Prueba de identidad del CEO"
                response.context_data['superadmin'] = 'Super administrador'
                response.context_data['superadmin'] = 'Super administrador'
                response.context_data['management'] = 'Administración'
                response.context_data['lbl_commodity'] = 'Listado de artículos y precios'
                response.context_data['lbl_commodity_list'] = 'Lista de ít'
                response.context_data['lbl_is_plugable'] = 'Es un objeto enchufable'

                response.context_data['lbl_item'] = 'ít.'
                response.context_data['lbl_registration_no'] = "Número de registro"
                response.context_data['lbl_assistants'] = "Ayudantes"
                response.context_data['lbl_volume'] = 'Volumen'
                response.context_data['lbl_length'] = 'Longitud'
                response.context_data['lbl_breadth'] = 'Width'
                response.context_data['lbl_height'] = 'Altura'
                response.context_data['lbl_material_type'] = 'tipo de material'
                response.context_data['lbl_charge'] = 'Prezo'
                response.context_data['lbl_installation_charge'] = 'Cargo por la instalación'
                response.context_data['lbl_image'] = 'Imagen'
                response.context_data['lbl_upload_file'] = 'Elija'
                response.context_data['lbl_profile_photo'] = 'Profilo Foto'
                response.context_data['lbl_edit'] = 'Editar'
                response.context_data['lbl_districts'] = 'Distritos'
                response.context_data['delete'] = 'Borrar'
                response.context_data['no_items_found'] = 'No se encontraron artículos'
                response.context_data['lbl_search'] = 'Buscar'
                response.context_data['lbl_previous'] = 'Anterior'
                response.context_data['lbl_next'] = 'Siguiente'
                response.context_data['lbl_export'] = 'Exportar'
                response.context_data['lbl_showing'] = 'mostrando'
                response.context_data['lbl_entries'] = 'registros'
                response.context_data['lbl_display'] = 'Mostrar'
                response.context_data['add_new_commodity'] = 'agregar nuevo ít'
                response.context_data['lbl_submit'] = 'Enviar'
                response.context_data['lbl_upd_commodity'] = 'Actualización de productos'
                response.context_data['lbl_update'] = 'Actualizar'
                response.context_data['want_to_delete'] = '¿Desea eliminar esta mercancía?'
                response.context_data['lbl_want_to_delete_image'] = '¿Quieres eliminar esta imagen?'
                response.context_data['admins'] = 'Administradores'
                response.context_data['update_admins'] = 'Actualizar detalles de administración'
                response.context_data['first_name'] = 'Nombre de pila'
                response.context_data['last_name'] = 'Apellido'
                response.context_data['admin_det_up_success'] = 'Detalles de administrador actualizados con éxito'
                response.context_data['lbl_admin_list'] = 'Lista de Admin'
                response.context_data['lbl_name'] = 'Nombre'
                response.context_data['lbl_email'] = 'Correo Electrónico'
                response.context_data['lbl_add_new_admin'] = 'Agregar nuevo administrador'
                response.context_data['lbl_want_del_user'] = '¿Quieres borrar este Usuario?'
                response.context_data['lbl_change_password'] = 'Cambia la contraseña'
                response.context_data['lbl_old_password'] = 'Contraseña anterior'
                response.context_data['lbl_new_password'] = 'Nueva contraseña'
                response.context_data['lbl_reset_changes'] = 'Restablecer cambios'
                response.context_data['lbl_update_profile'] = 'Actualización del perfil'
                response.context_data['lbl_profile_picture'] = 'Foto perfil'
                response.context_data['lbl_validating_and_uploading'] = 'Validar y cargar .....'
                response.context_data['lbl_footer'] = 'Derechos de autor © 2017 Muberz. Todos los derechos reservados.'
                response.context_data['lbl_forgot_password'] = 'Olvidaste tu contraseña'
                response.context_data['lbl_dont_have_account'] = "No tienes una cuenta?"
                response.context_data['lbl_fleet_registration'] = "Registro de flota"
                response.context_data['lbl_enter_email'] = 'ingrese correo electrónico'
                response.context_data['lbl_send_email'] = 'Enviar correo electrónico'
                response.context_data['lbl_sign_in'] = 'Registrarse'
                response.context_data['lbl_sign_up'] = 'Regístrate'
                response.context_data['lbl_invalid_reset_key'] = 'La tecla Restablecer no es válida o ha caducado'
                response.context_data['lbl_reset_pwd_txt'] = 'Restablecer la contraseña'
                response.context_data['lbl_enter_pwd_txt'] = 'Introduzca nueva contraseña'

                response.context_data['lbl_transfer_type'] = 'Tipo de transferencia y precios'
                response.context_data['lbl_transfer_from'] = 'Translokigo de'
                response.context_data['lbl_transfer_to'] = 'Translokiĝi al'
                response.context_data['lbl_transfer_type_list'] = 'Lista de tipos de transferencia'
                response.context_data['add_new_transfer_type'] = 'Agregar nuevo tipo de transferencia'
                response.context_data['lbl_upd_transfer_type'] = 'Actualizar tipo de transferencia'
                response.context_data['lbl_want_to_delete_transfer_type'] = '¿Desea eliminar este tipo de transferencia?'

                response.context_data['lbl_service_name'] = 'Nombre del Servicio'
                response.context_data['lbl_service_name_en'] = 'Nombre del servicio (En)'
                response.context_data['lbl_service_name_es'] = 'Nombre del servicio (Es)'
                response.context_data['lbl_description_en'] = 'Descripción(En)'
                response.context_data['lbl_description_es'] = 'Descripción(Es)'

                response.context_data['lbl_services'] = 'Configuración del tipo de servicio'
                response.context_data['lbl_service_list'] = 'Lista de servicios'
                response.context_data['lbl_add_new_service'] = 'Agregar nuevo servicio'
                response.context_data['lbl_upd_service'] = 'Servicio de actualización'
                response.context_data['lbl_want_to_delete_service'] = '¿Quieres eliminar este servicio?'

                response.context_data['lbl_city_name'] = 'Nombre de la ciudad'
                response.context_data['lbl_cities'] = 'Ciudades'
                response.context_data['lbl_city_list'] = 'Lista de ciudades'
                response.context_data['lbl_add_new_city'] = 'Añadir ciudad'
                response.context_data['lbl_upd_city'] = 'Actualizar ciudad'
                response.context_data['lbl_want_to_delete_city'] = '¿Desea eliminar esta ciudad?'

                response.context_data['lbl_validation_item_name'] = 'Por favor ingrese el nombre del artículo'
                response.context_data['lbl_validation_length'] = 'Por favor, introduzca la longitud'
                response.context_data['lbl_validation_breadth'] = 'Por favor ingrese Amplitud'
                response.context_data['lbl_validation_height'] = 'Por favor ingrese Altura'
                response.context_data['lbl_validation_material_type'] = 'Por favor ingrese el tipo de material'
                response.context_data['lbl_validation_charge'] = 'Por favor, introduzca la carga'
                response.context_data['lbl_validation_icon'] = 'Por favor, elija una imagen de icono'

                response.context_data['lbl_validation_company_name'] = 'Por favor ingrese el nombre'
                response.context_data['lbl_validation_address'] = 'Por favor ingrese la dirección'
                response.context_data['lbl_validation_email'] = 'Por favor ingrese correo electrónico'
                response.context_data['lbl_validation_password'] = 'Por favor, ingrese contraseña'
                response.context_data['lbl_validation_proof'] = "Por favor, elija la prueba de identidad del CEO"
                response.context_data['lbl_choose_city'] = 'Por favor elija una ciudad'

                response.context_data['lbl_discount'] = 'Descuento'
                response.context_data['lbl_service'] = 'Servicio'
                response.context_data['lbl_price_range'] = 'Rango de precios'
                response.context_data['lbl_discount_list'] = 'Discount List'
                response.context_data['add_new_discount'] = 'Add new Discount'
                response.context_data['lbl_upd_discount'] = 'Update Discount'
                response.context_data['lbl_want_to_delete_discount'] = 'Do you want to delete this Discount?'

                response.context_data['lbl_app_users'] = "Usuarios de la aplicación"
                response.context_data['lbl_mobile'] = "Celular Conductor"
                response.context_data['lbl_status'] = "Estatus"
                # TODO: NEED TRANSLATION
                response.context_data['lbl_rating'] = "Rating"
                response.context_data['lbl_approved_on'] = "Aprobado"
                response.context_data['lbl_joining_date'] = "Registration Date"
                response.context_data['lbl_action'] = "Acción"
                response.context_data['lbl_block'] = "Bloquear"
                response.context_data['lbl_unblock'] = "Desatascar"
                response.context_data['lbl_total_earnings'] = "Ganancias Totales"

                response.context_data['lbl_approve'] = "Aprobar"
                response.context_data['lbl_fleets'] = "Administradores de flota"
                response.context_data['lbl_new_fleets'] = "Nuevos registros de flota"
                response.context_data['lbl_blocked_fleets'] = "Gerentes de flota bloqueados"

                response.context_data['lbl_partners'] = "Vehículos"
                response.context_data['lbl_new_partners'] = "Nuevos registros de Controladores"
                response.context_data['lbl_blocked_partners'] = "Camiones bloqueados"
                response.context_data['lbl_vehicle_volume'] = "Volumen en m3 del Vehículo"
                response.context_data['lbl_vehicle_height'] = "Altura del vehículo"
                response.context_data['lbl_fleet_name'] = "Flota"

                response.context_data['lbl_add_partner'] = "Agregar Vehículo"
                response.context_data['lbl_serviceable_area'] = 'Área útil'
                response.context_data['lbl_fleet_or_individual'] = 'Flota / Individual'
                response.context_data['lbl_driver_licence'] = 'Licencia de Conducir'
                response.context_data['lbl_commercial_insurance'] = 'Seguro Vehicular'
                response.context_data['lbl_vehicle_registration'] = 'Tarjeta de Propiedad'
                response.context_data['lbl_fitness_certificate'] = 'Certificado de Antecedentes Policiales'
                response.context_data['lbl_tax_certificate'] = 'Certificado de Antecedentes Penales'
                response.context_data['lbl_deposit_amount'] = 'Cantidad del depósito'
                response.context_data['lbl_individual'] = 'Individual'

                response.context_data['lbl_amount'] = 'Monto de recarga'

                response.context_data['lbl_crew_mgmt'] = 'Gestión de camiones'
                response.context_data['lbl_add_new_crew'] = 'Agregar nuevo '
                response.context_data['lbl_crew_list'] = 'Lista de tripulación de camiones'
                response.context_data['lbl_truck_capacity'] = 'Capacidad del camión'
                response.context_data['lbl_loaders'] = 'Cantidad de cargadores'
                response.context_data['lbl_drivers'] = 'Controladores'
                response.context_data['lbl_capacity_from'] = 'Capacidad de'
                response.context_data['lbl_capacity_to'] = 'Capacidad para'
                response.context_data['lbl_want_to_delete_crew'] = '¿Quieres borrar esto?'
                response.context_data['lbl_upd_crew'] = 'Actualizar la tripulación del camión'

                response.context_data['lbl_damages_reported'] = "Daños reportados"
                response.context_data['lbl_transfer_on'] = "Realizado En"
                response.context_data['lbl_transfer_loc'] = "Recojo y Entrega"
                response.context_data['lbl_driver_name'] = "Nombre Conductor"
                response.context_data['lbl_transfer_amount'] = "Cantidad total"
                response.context_data['lbl_amount_paid'] = "Precio total"
                response.context_data['lbl_damaged_items'] = "Items Dañados"
                response.context_data['lbl_damage_type'] = "Tipo de Daño"
                response.context_data['lbl_open'] = "No resuelto"
                response.context_data['lbl_closed'] = "Resuelto"
                response.context_data['lbl_penalty'] = "Cantidad de penalidad"
                response.context_data['lbl_penalty_amt_already_added'] = "la cantidad de penalidad ya se agregó contra estos artículos dañados"
                response.context_data['lbl_trip_type'] = "Tipo"
                response.context_data['instant_transfer'] = "Transferencia instantánea"
                response.context_data['scheduled_transfer'] = "Transferencia programada"

                response.context_data['lbl_list_documents'] = 'Lista de documentos'
                response.context_data['lbl_doc_type'] = 'Tipo de Documento'
                response.context_data['lbl_document'] = 'Documento'
                response.context_data['lbl_language'] = 'Idioma'
                response.context_data['lbl_validation_document_type'] = 'Por favor ingrese el tipo de documento'
                response.context_data['lbl_validation_language'] = 'Por favor, elija Idioma'
                response.context_data['lbl_validation_document'] = 'Por favor elija un documento válido'
                response.context_data['lbl_add_update_document'] = 'Agregar / actualizar documento'
                response.context_data['lbl_view_file'] = 'Ver archivo'

                response.context_data['lbl_validation_name'] = 'Por favor ingrese el nombre'
                response.context_data['lbl_validation_email'] = 'Por favor introduzca un correo electrónico válido'
                response.context_data['lbl_validation_mobile_number'] = 'Ingrese el número de teléfono móvil con el código de país'
                response.context_data['lbl_validation_vehicle_volume'] = 'Ingrese el Volumen de vehículo válido'
                response.context_data['lbl_validation_driver_licence'] = 'Por favor, elija la licencia de conducir'
                response.context_data['lbl_validation_commercial_insurance'] = 'Elija un seguro comercial'
                response.context_data['lbl_validation_vehicle_registration'] = 'Por favor elija el registro del vehículo'
                response.context_data['lbl_validation_fitness_certificate'] = 'Por favor agregue certificado de aptitud'
                response.context_data['lbl_validation_tax_certificate'] = 'Por favor elija certificado de impuestos'

                response.context_data['lbl_profile_not_completed'] = 'Perfil no completado'

                response.context_data['lbl_edit_basic_details'] = "Editar detalles básicos"
                response.context_data['lbl_basic_details'] = "Detalles básicos"
                response.context_data['lbl_id_proof'] = "Documento de identificación"
                response.context_data['lbl_transit_peoples'] = "Ayudantes"
                response.context_data['lbl_commission_list'] = "Lista de la Comisión"
                response.context_data['lbl_update_commission'] = "Actualizar Comisión"
                response.context_data['lbl_commission'] = "Configuración de la Comisión"

                response.context_data['lbl_transfers'] = "Transferencias"
                response.context_data['lbl_transfers_details'] = "Detalles de transferencia"

                response.context_data['lbl_user'] = "Usuario"
                response.context_data['lbl_driver'] = "Conductor"
                response.context_data['lbl_payment_type'] = "Tipo de Pago"
                response.context_data['lbl_completed_on'] = "Completado en"
                """Menu for Offer Management"""
                response.context_data['lbl_offers'] = "Ofertas"
                response.context_data['lbl_add_offer'] = "Agregar oferta"
                response.context_data['lbl_list_offer'] = "Lista de ofertas"

                response.context_data['lbl_offer_type'] = "Tipo de oferta"
                response.context_data['lbl_trip_duration'] = "Duración total del viaje"
                response.context_data['lbl_offer_count'] = "Cuenta de viaje"
                response.context_data['lbl_offer_from'] = "Válida desde"
                response.context_data['lbl_offer_to'] = "Válido hasta"
                response.context_data['lbl_offer_cashamt'] = "Monto de la comisión"
                response.context_data['lbl_offer_perc'] = "Reducción en la Comisión"
                response.context_data['lbl_offer_user'] = "Flota / Usuario"
                response.context_data['lbl_offer_cash'] = "Efectivo / Porcentaje"
                response.context_data['lbl_time'] = "Basado en tiempo"
                response.context_data['lbl_trip'] = "Basado en viajes"
                response.context_data['lbl_cash'] = "Efectivo"
                response.context_data['lbl_perc'] = "Porcentaje"
                response.context_data['lbl_appliedto'] = "Conductor / Flota"
                response.context_data['lbl_user'] = "Usuario"
                response.context_data['lbl_fleet'] = "Flota"
                response.context_data['lbl_offer_based_on'] = "Condición"
                response.context_data['lbl_daily'] = "Diario"
                response.context_data['lbl_weekly'] = "Semanal"
                response.context_data['lbl_monthly'] = "Mensual"
                response.context_data['lbl_offer_duration'] = "Duración de la oferta"
                response.context_data['lbl_offer_list'] = "Lista de ofertas"
                response.context_data['lbl_want_to_delete_offer'] = "Desea eliminar esta oferta??"
                response.context_data['lbl_edit_offer'] = "Editar oferta"
                response.context_data['lbl_id_proof'] = "Prueba de Identificación"
                response.context_data['lbl_vehicle_number'] = "Placa del Vehiculo"

                response.context_data['lbl_pickup_location'] = "Lugar Recojo"
                response.context_data['lbl_drop_location'] = "Lugar Entrega"
                response.context_data['lbl_total_amount'] = "Importe"

                response.context_data['lbl_view'] = "Detalles"

                response.context_data['lbl_transfer_details'] = "Detalles de transferencia"
                response.context_data['lbl_no_items'] = "Número de items"

                response.context_data['lbl_damage_refund'] = "Reembolso de daños"
                response.context_data['lbl_payable_amount'] = "Saldo a pagar"
                response.context_data['lbl_service_type'] = "Tipos de servicio"

                response.context_data['lbl_rate_details'] = "Detalles de la tarifa"
                # Dashboard Reports and active trips
                response.context_data['lbl_active_users'] = "Usuarios Activos"
                response.context_data['lbl_active_partners'] = "Camiones activos"
                response.context_data['lbl_active_trips'] = "Servicios Activos"
                response.context_data['lbl_completed_trips'] = "Servicios Completados"
                response.context_data['lbl_damages_reported'] = "Daños Reportados"
                response.context_data['lbl_rentals'] = "Servicios"

                response.context_data['add_new_density_factor'] = 'Agregar nuevo factor de complejidad'
                response.context_data['lbl_density_factor'] = 'Factor de complejidad'
                response.context_data['lbl_density_factor_list'] = 'Factores de complejidad'
                response.context_data['lbl_density_factor_between'] = 'Factor de complejidad entre'
                response.context_data['lbl_update_density_factor'] = 'Actualizar el factor de complejidad'

                response.context_data['lbl_city_name_validate'] = 'Por favor, elija un nombre de ciudad válido'

                response.context_data['lbl_security_deposit_management'] = 'Gestión de depósitos de seguridad'
                response.context_data['lbl_add_new_security_deposit'] = 'Agregar nuevo depósito de seguridad'
                response.context_data['lbl_security_deposit_list'] = 'Lista de depósito de seguridad'
                response.context_data['lbl_want_to_delete'] = '¿Quieres borrar?'
                response.context_data['lbl_upd_security_deposit'] = 'Actualización de depósito de seguridad'
                response.context_data['lbl_deposit_needed'] = 'Depósito Necesario'

                response.context_data['lbl_payout_management'] = 'Payout Management'
                response.context_data['lbl_payout_history'] = 'Payout History'
                response.context_data['lbl_total_booking_amnt'] = 'Total Booking Amount'
                response.context_data['lbl_net_payable'] = 'Net Payable Amount'
                response.context_data['lbl_districts'] = 'List Districts'

                response.context_data['lbl_add_new_operator'] = 'Agregar nuevo operador'
                response.context_data['lbl_operator_list'] = 'Lista de operadores'
                response.context_data['update_operators'] = 'Actualizar detalles del operador'
                response.context_data['operators'] = 'Operadores'

                response.context_data['lbl_details'] = "Detalles"
                response.context_data['lbl_damage_details'] = "Detalle Daños"
                response.context_data['lbl_description'] = "Descripción"
                response.context_data['lbl_stolen'] = "Robado"
                response.context_data['lbl_fully_damaged'] = "Daño Total"
                response.context_data['lbl_truck_types'] = "Tipos de Camiones"
                response.context_data['lbl_add_promotion'] = "Añadir Promociones"
                response.context_data['lbl_promo_name'] = "Nombre de Promociones"
                response.context_data['lbl_promo_percentage'] = "Porcentage"
                response.context_data['lbl_promo_srtdescription'] = "Breve descripción"
                response.context_data['lbl_promo_description'] = "Descripción"
                response.context_data['lbl_promo_expiry'] = "Expiración"
                response.context_data['lbl_validation_percentage'] = 'ingrese el porcentaje correcto'
                response.context_data['lbl_validation_short_description'] = 'por favor ingrese la breve descripción'
                response.context_data['lbl_validation_description'] = 'por favor ingrese la descripción'
                response.context_data['lbl_promotion_list'] = 'Promociones'
                response.context_data['lbl_promo'] = 'Nombre De Promocions'
                response.context_data['lbl_percentage'] = 'Porcentaje'
                response.context_data['lbl_short_description'] = 'Breve Descripción'
                response.context_data['lbl_description'] = 'Descripción'
                response.context_data['lbl_expiry'] = 'Fecha de caducidad'

                response.context_data['lbl_add_advertisement'] = 'Anuncio'
                response.context_data['lbl_adv_header'] = 'Encabezamiento'
                response.context_data['lbl_adv_image'] = 'Imagen'
                response.context_data['lbl_adv_start'] = 'Fecha de inicio'
                response.context_data['lbl_adv_end'] = 'Fetcha final'
                response.context_data['lbl_adv_typeof'] = 'Tipo de usuarios'
                response.context_data['lbl_adv_list'] = 'Lista de anuncios'
                response.context_data['lbl_adv_name'] = 'Texto publicitario'
                response.context_data['lbl_adv_users'] = 'Tipo de usuarios'
                response.context_data['lbl_on_off_switch'] = 'Sistema encendido/apagado'
                response.context_data['lbl_end_time'] = 'Hora de finalización'
                response.context_data['lbl_start_time'] = 'Hora de Inicio'
                response.context_data['lbl_reset'] = 'Reiniciar'

                response.context_data['lbl_diver_name'] = 'Conductor'
                response.context_data['lbl_new_assignee'] = 'Cesionaria'
                response.context_data['lbl_distance'] = 'Distancia'
                response.context_data['lbl_last'] = 'Primera'
                response.context_data['lbl_first'] = 'Ultimo'




        except:
            request.session['language'] = 'span'

        return response
