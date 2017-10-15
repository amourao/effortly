
def metersPerSecondToKmH(mps):
    return "{:.2f}".format(mps*3.6)

def metersPerSecondToMiH(mps):
    return "{:.2f}".format(mps*2.237)

def metersToMeters(m):
    return "{:.2f}".format((m))

def metersToMiles(m):
    return "{:.2f}".format((m/1609.34))

def metersToFeet(m):
    return "{:.2f}".format((m*3.28))

def metersToKm(m):
    return "{:.2f}".format(m/1000.0)

def bpmToBpm(bpm):
    return "{:.2f}".format(bpm)

def secondsToMinutesSecs(s):
    return decMinutesToMinutesSecs(s/60.0)

def decMinutesToMinutesSecs(mpkm):
    if mpkm == 0:
        return "0:00"
    elif mpkm > 0:
        hpkm = int(mpkm/60)
        mpkm = mpkm-hpkm*60
        if hpkm > 0:
            return "{}:{:02.0f}:{:02.0f}".format(int(hpkm),int(mpkm), int((mpkm-(int(mpkm)))*60)%60)   
        else:
            return "{}:{:02.0f}".format(int(mpkm), int((mpkm-(int(mpkm)))*60)%60)   
    else:
        mpkm = -mpkm
        hpkm = int(mpkm/60)
        mpkm = mpkm-hpkm*60
        if hpkm > 0:
            return "-{}:{:02.0f}:{:02.0f}".format(int(hpkm),int(mpkm), int((mpkm-(int(mpkm)))*60)%60)
        else:
            return "-{}:{:02.0f}".format(int(mpkm), int((mpkm-(int(mpkm)))*60)%60)


def metersPerSecondToMinPerMi(mps):
    if mps == 0:
        return secondsPerMeterToMinPerMi(0)
    return secondsPerMeterToMinPerMi(1.0/mps)

def metersPerSecondToMinPerKm(mps):
    if mps == 0:
        return secondsPerMeterToMinPerMi(0)
    return secondsPerMeterToMinPerKm(1.0/mps)

def secondsPerMeterToMinPerKm(spm):
    mpkm = spm*1000.0/60.0
    return decMinutesToMinutesSecs(mpkm)

def secondsPerMeterToMinPerMi(spm):
    mpmi = spm*1609.34/60.0
    return decMinutesToMinutesSecs(mpmi)

def invertTimeDistance(mps):
    if mps == 0:
        return 0
    return (1.0/mps)