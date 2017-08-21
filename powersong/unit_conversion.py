
def metersPerSecondToKmH(mps):
    return "{:.2f}".format(mps*3.6)

def metersPerSecondToMiH(mps):
    return "{:.2f}".format(mps*2.237)

def metersToMeters(m):
    return "{}".format((m))

def metersToMiles(m):
    return "{}".format((m/1609.34))

def metersToFeet(m):
    return "{}".format((m*3.28))

def metersToKm(m):
    return "{:.2f}".format(m/1000.0)

def secondsToMinutesSecs(s):
    return decMinutesToMinutesSecs(s/60.0)

def decMinutesToMinutesSecs(mpkm):
    if mpkm == 0:
        return "0:00"
    elif mpkm > 0:
        return "{}:{:02.0f}".format(int(mpkm), int((mpkm-(int(mpkm)))*60)%60)   
    else:
        mpkm=-mpkm
        return "-{}:{:02.0f}".format(int(mpkm), int((mpkm-(int(mpkm)))*60)%60)


def metersPerSecondToMinPerMi(mps):
    return secondsPerMeterToMinPerMi(1.0/mps)

def metersPerSecondToMinPerKm(mps):
    return secondsPerMeterToMinPerKm(1.0/mps)

def secondsPerMeterToMinPerKm(spm):
    mpkm = spm*1000.0/60.0
    return decMinutesToMinutesSecs(mpkm)

def secondsPerMeterToMinPerMi(spm):
    mpmi = spm*1609.34/60.0
    return decMinutesToMinutesSecs(mpmi)

def invertTimeDistance(mps):
    return (1.0/mps)