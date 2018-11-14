import numpy as np

def convert_bytes_to_np(bdata,btime):
    data = np.fromstring(bdata,dtype=np.float16)
    time = np.fromstring(btime,dtype=np.uint8)
    return data,time

def get_best_curve_fit(qs):
    tmp_data = []
    tmp_time = []
    max_time = -1
    for q in qs:
        data, time = convert_bytes_to_np(q['data'],q['time'])
        data -= data[0]

        dtime = [range(np.max(time))]
        ddata = np.interp(dtime,time,data)
        
        tmp_data.append(ddata)

        if np.max(time) > max_time:
            max_time = np.max(time)

    xdata = np.array([range(max_time)], dtype=np.uint8)
    ydata_count = np.zeros(shape=(1,max_time), dtype=np.uint8)
    ydata = np.zeros(shape=(1,max_time), dtype=np.float16)

    for data in tmp_data:
        data_count = np.ones(shape=data.shape,dtype=np.uint8)
        data = np.resize(data,ydata.shape)
        data_count = np.resize(data_count,ydata.shape)
        ydata += data
        ydata_count += data_count
    return xdata, ydata/ydata_count
    

