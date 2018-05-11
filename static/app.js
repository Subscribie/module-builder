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
