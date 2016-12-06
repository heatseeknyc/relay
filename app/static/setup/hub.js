$(function() {

  function refresh() {
    $.when($.get(HUB_PARTIAL_URL), $.get(CELLS_PARTIAL_URL))
      .done(function(hub_response, cells_response) {
        $('#hub-data').html(hub_response[0]);
        $('#cells-data').html(cells_response[0]);
        refreshSoon();
      });
  }

  function refreshSoon() {
    setTimeout(refresh, 5000);
  }

  $('#hourly').click(function() {
    $.post(HUB_PATCH_URL, {hourly: true});
  });
  $('#test').click(function() {
    $.post(HUB_PATCH_URL, {test_mode: true});
  });

  refreshSoon();

});
