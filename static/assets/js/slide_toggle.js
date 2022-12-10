$(function () {
    $('#add_offer_form').css('display', 'none');
    $('.expand_click').click(function () {
        $('#add_offer_form').slideToggle();
        if ($(this).find('i').hasClass('fa-plus')) {
            $(this).find('i').removeClass('btn-success');
            $(this).find('i').removeClass('fa-plus');

            $(this).find('i').addClass('btn-danger');
            $(this).find('i').addClass('fa-minus');
        }
        else {
            $(this).find('i').removeClass('btn-danger');
            $(this).find('i').removeClass('fa-minus');

            $(this).find('i').addClass('btn-success');
            $(this).find('i').addClass('fa-plus');
        }
    })
});

