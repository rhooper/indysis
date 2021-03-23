function createCookie(name,value,days) {
    if (days) {
	var date = new Date();
	date.setTime(date.getTime()+(days*24*60*60*1000));
	var expires = "; expires="+date.toGMTString();
    }
    else var expires = "";
    document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
	var c = ca[i];
	while (c.charAt(0)==' ') c = c.substring(1,c.length);
	if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}


$(document).ready(function() {
    // Check cookies to see if sections are already open
    var headers = ['a_general', 'a_attendance', 'a_alumni'];
    if (readCookie('a_general') == null) { // Default is open
	createCookie('a_general', 'true');
    }
    for (var i=0; i<headers.length; i++) {
	if (readCookie(headers[i]) == "true") {
	    $("#" + headers[i]).toggleClass('expanded').next(".sv-main").show();
	}
    }
    
    // Switches CSS classes. This controls the right and down arrows.  
    $(".section-header").click(function () {
	$(this).parent().removeClass('hidden-print');
	if ($(this).hasClass("subsection")) {
	    $(this).toggleClass('sub-expanded');
	    $(this).toggleClass('hidden-print');
	} else {
	    if ($(this).hasClass('expanded')) {
		createCookie($(this).attr('id'), 'false');
	    } else {
		createCookie($(this).attr('id'), 'true');
	    }
	    $(this).toggleClass('expanded');
	    $(this).toggleClass('hidden-print');
	}
	
	// Toggle the section.
	$(this).next(".sv-main").slideToggle(600);
    });
});

function ajax_include_deleted(){
    var checked = $('#id_include_deleted').is(":checked");
    $.ajax({
	url: "/studentdb/ajax_include_deleted?checked=" + checked
    });
}
