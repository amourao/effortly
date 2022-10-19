from powersong.models import metric_legends, imperial_legends


def metersPerSecondToKmH(mps):
    if mps == None:
        return None
    return "{:.2f}".format(mps*3.6)

def metersPerSecondToMiH(mps):
    if mps == None:
        return None
    return "{:.2f}".format(mps*2.237)

def metersToMeters(m):
    if m == None:
        return None
    return "{:.2f}".format((m))

def metersToMiles(m):
    if m == None:
        return None
    return "{:.2f}".format((m/1609.34))

def metersToFeet(m):
    if m == None:
        return None
    return "{:.2f}".format((m*3.28))

def metersToKm(m):
    if m == None:
        return None
    return "{:.2f}".format(m/1000.0)

def bpmToBpm(bpm):
    if bpm == None:
        return None
    return "{:.2f}".format(bpm)

def secondsToMinutesSecs(s):
    if s == None:
        return None
    return decMinutesToMinutesSecs(s/60.0)

def secondsToHoursMinutesSecs(s):
    if s == None:
        return None
    return decMinutesToHoursMinutesSecs(s/60.0)

def decMinutesToHoursMinutesSecs(mpkm):
    if mpkm == None:
        return None
    if mpkm == 0:
        return "0:00:00"
    if mpkm < 0:
        mpkm = -mpkm
    hpkm = int(mpkm/60)
    mpkm = mpkm-hpkm*60
    spkm = int((mpkm - (int(mpkm))) * 60) % 60
    return "{}{}:{:02.0f}:{:02.0f}".format("-" if mpkm < 0 else "", int(hpkm), int(mpkm), int(spkm))


def decMinutesToMinutesSecs(mpkm):
    if mpkm == None:
        return None
    if mpkm == 0:
        return "0:00"

    if mpkm < 0:
        mpkm = -mpkm

    hpkm = int(mpkm/60)
    mpkm = mpkm-hpkm*60
    spkm = int((mpkm-(int(mpkm)))*60)%60
    if hpkm > 0:
        return "{}{}:{:02.0f}:{:02.0f}".format("-" if mpkm < 0 else "", int(hpkm), int(mpkm), int(spkm))
    else:
        return "{}{}:{:02.0f}".format("-" if mpkm < 0 else "",int(mpkm), int(spkm))



def metersPerSecondToMinPerMi(mps):
    if mps == None:
        return None
    if mps == 0:
        return secondsPerMeterToMinPerMi(0)
    return secondsPerMeterToMinPerMi(1.0/mps)

def metersPerSecondToMinPerKm(mps):
    if mps == None:
        return None
    if mps == 0:
        return secondsPerMeterToMinPerKm(0)
    return secondsPerMeterToMinPerKm(1.0/mps)

def secondsPerMeterToMinPerKm(spm):
    if spm == None:
        return None
    mpkm = spm*1000.0/60.0
    return decMinutesToMinutesSecs(mpkm)

def secondsPerMeterToMinPer100m(spm):
    if spm == None:
        return None
    mp100m = spm * 100.0 / 60.0
    return decMinutesToMinutesSecs(mp100m)

def secondsPerMeterToMinPerMi(spm):
    if spm == None:
        return None
    mpmi = spm*1609.34/60.0
    return decMinutesToMinutesSecs(mpmi)

def secondsPerMeterToMinPer100yd(spm):
    if spm == None:
        return None
    mp100yd = spm * 109.361 / 60.0
    return decMinutesToMinutesSecs(mp100yd)

def invertTimeDistance(mps):
    if mps == None:
        return None
    if mps == 0:
        return 0
    return (1.0/mps)


def get_speed_pretty_units(measurement_preference, act_type):
    if (measurement_preference == 0) and (act_type == 0):
        return metric_legends['speed_s']
    elif (measurement_preference == 0) and (act_type == 1):
        return metric_legends['speed']
    elif (measurement_preference == 0) and (act_type == 2):
        return metric_legends['speed_smaller']
    elif (measurement_preference == 1) and (act_type == 0):
        return imperial_legends['speed_s']
    elif (measurement_preference == 1) and (act_type == 1):
        return imperial_legends['speed']
    elif (measurement_preference == 1) and (act_type == 2):
        return imperial_legends['speed_smaller']
    return ""


def get_speed_pretty(speed, measurement_preference, act_type):
    if (measurement_preference == 0) and (act_type == 0):
        return secondsPerMeterToMinPerKm(invertTimeDistance(speed))
    elif (measurement_preference == 0) and (act_type == 1):
        return metersPerSecondToKmH(speed)
    elif (measurement_preference == 0) and (act_type == 2):
        return secondsPerMeterToMinPer100m(invertTimeDistance(speed))
    elif (measurement_preference == 1) and (act_type == 0):
        return secondsPerMeterToMinPerMi(invertTimeDistance(speed))
    elif (measurement_preference == 1) and (act_type == 1):
        return metersPerSecondToMiH(speed)
    elif (measurement_preference == 1) and (act_type == 2):
        return secondsPerMeterToMinPer100yd(invertTimeDistance(speed))
    return ""