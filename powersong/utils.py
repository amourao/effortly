import math

def generate_header(data, n, page, total_length):
    if page > 0:
        page += 1
    return "Page {} of {} - Total results: {}".format(page, math.ceil(total_length / n), total_length)
