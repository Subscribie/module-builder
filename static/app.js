document.addEventListener('DOMContentLoaded', subscribieInit);

function subscribieInit(e) {
  console.log("subscribieInit ready.");
  Subscribie.showBuildingSite();
}

Subscribie = {
    showBuildingSite: function() {
      try {
          form = document.getElementById('items');
          form.addEventListener('submit', function(e){
              btn = document.getElementById('submit-start-building');
              btn.value = 'Please wait, building your site..';
              btn.disabled = true;
          });
      } catch (e) {
          console.error(e);
      }
    }
}

// File Upload - Adding Filename to the upload widget

$("body").on("change", "input[type=file]", function(){
    var name = $(this).attr("name");
    var filename = $(this).val().replace(/C:\\fakepath\\/i, '');
    $("#" + name + "-label").text(filename);
  })
;

// Modals

jQuery(document).ready(function ($) {
  $('.modal-button').click(function() {
    console.log("Modal Opened");
    var target = $(this).data('target');
    $('html').addClass('is-clipped');
    $('#' + target).addClass('is-active');
  });
  $('.modal-background, .modal-close').click(function() {
    $('html').removeClass('is-clipped');
    $('.modal').removeClass('is-active');
  });
  $('.modal-card-head .delete').click(function() {
    $('html').removeClass('is-clipped');
    $('.modal').removeClass('is-active');
  });
  $('.modal-card-body #close').click(function() {
    $('html').removeClass('is-clipped');
    $('.modal').removeClass('is-active');
  });
  $(document).on('keyup',function(e) {
    if (e.keyCode == 27) {
      $('html').removeClass('is-clipped');
      $('.modal').removeClass('is-active');
    }
  });
});
