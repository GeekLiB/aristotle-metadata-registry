// Set (then unset) this to supress the ajax loading animation
var suppressLoadingBlock = false;

// Scrap modals if they lose focus so they can be loaded with new content
$(document).ready(function() {
    $('.modal').on('hidden.bs.modal', function(e)
    { 
        console.log(this)
        $(this).removeData();
        x = $(this).find('.modal-content > *');
        console.log(x)
        x.remove()
    });
});


$(document).ajaxSend(function(event, request, settings) {
    if (!suppressLoadingBlock) {
        $('#loading_indicator').show().addClass('loading').removeClass('hidden');
    }
});

$(document).ajaxComplete(function(event, request, settings) {
    $('#loading_indicator').hide().removeClass('loading');
});

// OVerrides callback for notify menu
function fill_aristotle_notification_menu(data) {
    var menu = document.getElementById(notify_menu_id);
    if (menu) {
        menu.innerHTML = "";
        if (consecutive_misfires < 10) {
            if (data.unread_list.length > 0) {
                for (var i=0; i < data.unread_list.length; i++) {
                    var item = data.unread_list[i];
                    menu.innerHTML = menu.innerHTML + "<li><a href='/item/"+item.target_object_id+"'>"+item.verb+" - "+item.actor+"</a></li>";
                }
                menu.innerHTML = menu.innerHTML + '<li role="presentation" class="divider"></li>';
                menu.innerHTML = menu.innerHTML + "<li><a href='#' onclick='mark_all_unread();return false'><i class='fa fa-envelope-o fa-fw'></i> Mark all as read</a></li>";
                menu.innerHTML = menu.innerHTML + "<li><a href='"+notify_unread_url+"'><i class='fa fa-inbox fa-fw'></i> View all unread notifications...</a></li>";
            } else {
                menu.innerHTML = "<li><a href='"+notify_unread_url+"'><i class='fa fa-inbox fa-fw'></i> No unread notifications...</a></li>";
            }
        } else {
            menu.innerHTML = menu.innerHTML + "<li><a href='#' onclick='refresh_misfires();return false'>[!] Notification stream lost, click to re-establish connection</a></li>";
        }
    }
}

function mark_all_unread() {
    var r = new XMLHttpRequest();
    r.open("GET", notify_mark_all_unread_url, true);
    r.onreadystatechange = function () {
        if (r.readyState != 4 || r.status != 200) {
            return;
        }
        var badge = document.getElementById(notify_badge_id);
        if (badge) {
            badge.innerHTML = 0;
        }
    }
    r.send();
}

function refresh_misfires() {
    var badge = document.getElementById(notify_badge_id);
    if (badge) {
        badge.innerHTML = "...";
    }
    consecutive_misfires = 0;
    setTimeout(fetch_api_data,notify_refresh_period);
}