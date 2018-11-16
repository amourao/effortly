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
        return mark_safe('<i class="fa fa-chevron-circle-up green_arrow"></i>')
    elif value < -0.001:
        return mark_safe('<i class="fa fa-chevron-circle-down red_arrow"></i>')
    else:
        return mark_safe('<i class="blue_arrow">=</i>')

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

