from django import template
from django.utils.safestring import mark_safe

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
