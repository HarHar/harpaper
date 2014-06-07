$(document).ready(function() {
    var oldhtml = $('body').html();
    var WEB_SOCKET_SWF_LOCATION = '/static/js/socketio/WebSocketMain.swf',
    controlSocket = io.connect('/control');
        
    controlSocket.on('sethtml_full', function (html) {
    	if (html != oldhtml) {
    		$('body').html(html);
    		oldhtml = html;
    	}
    });

    var aux = 0;
    var bars = 0;

    controlSocket.on('mpdvisClear', function() {
        $('.mpdvisBar').css('width', '0px');
    });

    controlSocket.on('mpdvisInfo', function(channels) {
        $('.mpdvisBar').css('display', 'inline');
        $.each(channels, function(i, value) {
            if ($('#mpdvisBar' + i).length == 0) {
                aux = aux + 1;
                if (bars < 20) {
                    bars = bars + 1;
                    if (aux == 1) {
                        $('#mpdvis_container').append('<div class="mpdvisBar bar_red" id="mpdvisBar' + i + '"></div>');
                    } else if (aux == 2) {
                        $('#mpdvis_container').append('<div class="mpdvisBar bar_yellow" id="mpdvisBar' + i + '"></div>');
                    } else if (aux == 3) {
                        $('#mpdvis_container').append('<div class="mpdvisBar bar_blue" id="mpdvisBar' + i + '"></div>');
                    } else if (aux == 4) {
                        $('#mpdvis_container').append('<div class="mpdvisBar bar_purple" id="mpdvisBar' + i + '"></div>');
                        aux = 0;
                    }
                }
            }

            $('#mpdvisBar' + i).css('top', (i*10)-3);

            //$('#mpdvisBar' + i).css('width', parseInt(value)*7);
            $('#mpdvisBar' + i).animate({
                width: parseInt(value)*3
            }, 25, "linear", function() {

            });
        });
    });

    controlSocket.emit('init');
});