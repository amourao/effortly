from django import template
from django.utils.safestring import mark_safe

import numpy as np

from powersong.curve_fit import convert_bytes_to_np, running_mean

register = template.Library()

@register.simple_tag
def get_delta_symbol(value,reverse):
    if value == None:
        return ''
    if reverse == 1:
        value = -value
        
    if value > 0.001:
        return mark_safe('<i class="fa fa-chevron-circle-up green_arrow" data-toggle="tooltip" data-placement="top" title="Higher"></i>')
    elif value < -0.001:
        return mark_safe('<i class="fa fa-chevron-circle-down red_arrow" data-toggle="tooltip" data-placement="top" title="Lower"></i>')
    else:
        return mark_safe('<i class="blue_arrow" data-toggle="tooltip" data-placement="top" title="No Change">=</i>')

@register.simple_tag
def get_song_symbol(spotify_id):
    result = ''

    if spotify_id:
        result += '<i class="fab fa-spotify" data-toggle="tooltip" data-placement="top" title="Spotify"></i>'

    if result:
        result = mark_safe('{}'.format(result))

    return result

#runs: 0 -> ‘default’, 1 -> ‘race’, 2 -> ‘long run’, 3 -> ‘workout’; 
# for rides: 10 -> ‘default’, 11 -> ‘race’, 12 -> ‘workout’
@register.simple_tag
def get_symbols(value,flagged,flagged_hr):
    result = ''
        
    if value == 1 or value == 11:
        result += '<i class="fa fa-flag-checkered" data-toggle="tooltip" data-placement="top" title="Race"></i>'
    elif value == 2:
        result += '<i class="fa fa-mountain" data-toggle="tooltip" data-placement="top" title="Long Run"></i>'
    elif value == 3 or value == 12:
        result += '<i class="fa fa-circle-notch" data-toggle="tooltip" data-placement="top" title="Workout"></i>'

    if flagged:
        result += '<i class="fa fa-flag" data-toggle="tooltip" data-placement="top" title="Flagged"></i>'

    if flagged_hr:
        result += '<i class="fa fa-heartbeat" data-toggle="tooltip" data-placement="top" title="HR Flagged!"></i>'
    
    if result:
        result = mark_safe('<p>{}</p>'.format(result))

    return result


@register.simple_tag
def decode_bytes_data(**kwargs):
    data,time = convert_bytes_to_np(kwargs['data'],kwargs['time'])
    return zip((data-data[0]),time)

@register.simple_tag
def decode_bytes_data_no_normal(**kwargs):
    data,time = convert_bytes_to_np(kwargs['data'],kwargs['time'])
    return zip(data,time)

@register.simple_tag
def decode_all(**kwargs):
    N = 5
    last_time = 0
    results = []
    for q in kwargs['qs']:
        data,time = convert_bytes_to_np(q['data'],q['time'])
        last_time_q = time[-1]
        time_ajusted = time + last_time
        last_time += last_time_q+1
        results.append(zip(data,time_ajusted,time))
        #results.append(zip(np.append(data[:N-1],running_mean(data,N)),time_ajusted,time))
    return results

