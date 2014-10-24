$(document).ready(function() {
 $("#background").bind('load', function() {
    var oldhtml = $('body').html();
    var WEB_SOCKET_SWF_LOCATION = '/static/js/socketio/WebSocketMain.swf',
    controlSocket = io.connect('/control');

    //main color
    var i = 0;
    var color = tinycolor(getAverageRGB($('#background')[0]));
    var mcolor = tinycolor.analogous(color)[1].toHexString();

    var color_ = tinycolor(color);
    var mcolor_ = tinycolor(mcolor);

    var color_brightness = color_.getBrightness();
    var mcolor_brightness = mcolor_.getBrightness();
    var canRead = true;
    if (Math.abs(color_brightness - mcolor_brightness) < 10) {
        canRead = false;
    }

    if (canRead == false) {
        if (color_.isLight() && mcolor_.isLight()) {
            mcolor = tinycolor.darken(mcolor).toHexString();
        } else if (color_.isDark() && mcolor_.isDark()) {
            mcolor = tinycolor.brighten(mcolor).toHexString();
        }
    }

    //text color
    var allColors = [];
    for (var i in tinycolor.names) {
        allColors.push(i);
    }
    var tcolor = tinycolor.mostReadable(mcolor, allColors);

    controlSocket.emit('setColor', mcolor);
    $('#musicInfo_title').css('color', mcolor);
    $('#musicInfo_artist').css('color', mcolor);

    controlSocket.on('sethtml_full', function (html) {
    	if (html != oldhtml) {
    		$('body').html(html);
    		oldhtml = html;
    	}
    });

    var aux = 0;
    var bars = 0;
    var maxbars = 20;
    var isplaying = false;
    var layeropacity = $('#layer').css('opacity');
    $('#layer').css('opacity', 0);
    $('#mpdvis_container').css('height', (maxbars*5)+10);
    $('#layer').css('height', $('#mpdvis_container').css('height'));

    controlSocket.on('mpdvisClear', function() {
        if (isplaying) {
            isplaying = false;
            $('.mpdvisBar').animate({
                width: 0
            }, 1000, "swing", function () {
                $("#layer").animate({
                    opacity: 0
                }, 500);
            });
        }
    });

    controlSocket.on('refreshWP', function() {
        location.reload();
    });

    controlSocket.on('chcolor', function(color) {
        //$('.mpdvisBar').css('background-color', color)
        //$('#partypooper').stop(true, true);
        //$('#partypooper').animate({
        //    backgroundColor: color
        //}, 200);
        //$('#yeahbaby').css('background-color', color)
        $('#yeahbaby').stop(true, true);
        $('#yeahbaby').animate({
            backgroundColor: color
        }, 80);
    });

    controlSocket.on('musicInfo_artist', function(text) {
        $('#musicInfo_artist').text(text);
    });

    controlSocket.on('musicInfo_title', function(text) {
        $('#musicInfo_title').text(text);
    });

    controlSocket.on('setUiColor', function(c) {
        mcolor = c;
        $('.mpdvisBar').css('background-color', c);
        $('#musicInfo_title').css('color', c);
        $('#musicInfo_artist').css('color', c);
    });

    controlSocket.on('mpdvisInfo', function(channels) {
        if (isplaying == false) {
            isplaying = true;
            $('.mpdvisBar').stop(true, true);
            $('#layer').stop(true, true);
            $('#layer').css('opacity', layeropacity);
        }
        
        if (bars != maxbars) {
            bars = bars + 1;
            $.each(Array(maxbars), function(i, value) {
                $('#mpdvis_container').append('<div class="mpdvisBar" id="mpdvisBar' + i + '" style="background-color: ' + mcolor + '"></div>');
                $('#mpdvisBar' + i).css('left', (i*5));
                $('.mpdvisBar').css('display', 'inline');
            });
        }
''
        $.each(channels, function(i, value) {
            if (i > maxbars) {
                return true;
            }

            //$('#mpdvisBar' + i).css('width', parseInt(value)*4);
            $('#mpdvisBar' + i).animate({
                height: parseInt(value)*0.8
            }, 80, "linear");
        });
    });

    controlSocket.emit('init');
});

function getAverageRGB(imgEl) {
    
    var blockSize = 5,
        defaultRGB = {r: 0, g: 0, b: 0},
        canvas = document.createElement('canvas'),
        context = canvas.getContext && canvas.getContext('2d'),
        data, width, height,
        i = -4,
        length,
        rgb = {r: 0, g: 0, b: 0},
        count = 0;
        
    if (!context) {
        return defaultRGB;
    }
    
    height = canvas.height = imgEl.naturalHeight || imgEl.offsetHeight || imgEl.height;
    width = canvas.width = imgEl.naturalWidth || imgEl.offsetWidth || imgEl.width;
    
    context.drawImage(imgEl, 0, 0);
    
    try {
        data = context.getImageData(0, 0, width, height);
    } catch(e) {
        return defaultRGB;
    }
    
    length = data.data.length;
    
    while ((i += blockSize * 4) < length) {
        ++count;
        rgb.r += data.data[i];
        rgb.g += data.data[i+1];
        rgb.b += data.data[i+2];
    }
    
    rgb.r = ~~(rgb.r/count);
    rgb.g = ~~(rgb.g/count);
    rgb.b = ~~(rgb.b/count);
    
    return rgb;
    
 }
});

