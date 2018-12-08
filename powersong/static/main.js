var first_play = true
var init = false


var play = ({
      spotify_uri,
      position,
      playerInstance: {
        _options: {
          getOAuthToken,
          id
        }
      }
    }) => {
      getOAuthToken(access_token => {
        fetch(`https://api.spotify.com/v1/me/player/play?device_id=${id}`, {
          method: 'PUT',
          body: JSON.stringify({ uris: spotify_uri, position_ms: position }),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${access_token}`
          },
        });
      });
    };




function playList(){
    if (first_play){
        createPlayer()
        first_play = false
    } else if (init) {
        player.togglePlay()
    }
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}



function sendPost(activity_id, type, key, value) {
  data = {}
  data[key] = value
  $.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
  });

  $.ajax({
      type: "POST",
      url: "/" + type + "/" + activity_id + '/',
      data: JSON.stringify(data),
      success: setTimeout(function(){ location.reload(); }, 1000)
  });
}

function sendGet(url) {
  $.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
  });
  $.ajax({
      type: "GET",
      url: url,
      success: setTimeout(function(){ location.reload(); }, 4000)
  });
}

function createPlayer(){
    player = new Spotify.Player({
    name: 'PowerSong web player',
    getOAuthToken: cb => { cb(token); }
    });
    player.addListener('initialization_error', ({ message }) => { 
        console.error(message); 
        document.getElementById('nowPlaying').innerHTML = message
    });
    player.addListener('account_error', ({ message }) => {
        console.error(message); 
        document.getElementById('nowPlaying').innerHTML = message
    });
    player.addListener('playback_error', ({ message }) => {
        console.error(message); 
        document.getElementById('nowPlaying').innerHTML = message
    });
    player.addListener('player_state_changed', state => {
       title = state.track_window.current_track.name
       artists = state.track_window.current_track.artists
       artist = ''
       artists.forEach(function(entry) {
          artist += entry.name + ', '
       });
       artist = artist.substring(0,artist.length-2)
       all = artist + ' - ' + title
       document.getElementById('nowPlaying').innerHTML = all
    });

    player.addListener('authentication_error', ({ message }) => {
        document.getElementById('nowPlaying').innerHTML = 'Refreshing token'
        $.ajax({ 
            type: 'GET', 
            url: '/strava_oauth_refresh/', 
            dataType: 'json',
            success: function( data ) {
              token = data['token']
              player.disconnect()
              createPlayer()
              
            }
        });
    });

    // Ready
    player.addListener('ready', ({ device_id }) => {
        console.log('Ready with Device ID', device_id);
        document.getElementById('nowPlaying').innerHTML = 'Player ready';
        init = true;

        var filtered = spotify_ids.filter(function(value, index, arr){
            return value != "spotify:track:None";
        });
        play({
            playerInstance: player,
            spotify_uri: filtered,
            position: 0
        });
    });
    player.addListener('not_ready', ({ device_id }) => {
        console.log('Device ID has gone offline', device_id);
        document.getElementById('nowPlaying').innerHTML = 'Player has gone offline';
        init = false;
    });

    // Connect to the player!
    player.connect();
}    
