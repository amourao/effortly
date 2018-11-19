import numpy as np

import logging
logger = logging.getLogger(__name__)

ROLLING_MEAN_N = 3

def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0)) 
    return (cumsum[N:] - cumsum[:-N]) / float(N)

def convert_bytes_to_np(bdata,btime):
    data = np.fromstring(bdata,dtype=np.float16).reshape(-1)
    time = np.fromstring(btime,dtype=np.uint16).reshape(-1)
    return data,time

def get_best_curve_fit(qs):
    tmp_data = []
    tmp_time = []
    max_time = -1
    if not qs:
        return np.array([]), np.array([])
    for q in qs:
        data, time = convert_bytes_to_np(q['data'],q['time'])
        data -= data[0]

        dtime = [range(np.max(time))]
        ddata = np.interp(dtime,time,data).reshape(-1)
        
        tmp_data.append(ddata)

        if np.max(time) > max_time:
            max_time = np.max(time)

    xdata = np.array([range(max_time)], dtype=np.uint16)
    ydata_count = np.zeros(shape=(max_time), dtype=np.uint16)
    ydata = np.zeros(shape=(max_time), dtype=np.float16)

    for data in tmp_data:
        data_count = np.ones(shape=data.shape,dtype=np.uint16)
        diff = max_time - data_count.shape[0]
        if diff > 0:
            data = np.append(data,np.zeros(shape=(diff), dtype=np.float16))
            data_count = np.append(data_count,np.zeros(shape=(diff), dtype=np.uint16))
        ydata += data
        ydata_count += data_count

    return xdata[0][(ROLLING_MEAN_N-1):], running_mean(ydata/ydata_count,ROLLING_MEAN_N)
