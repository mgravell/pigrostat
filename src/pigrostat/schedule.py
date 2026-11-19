# Time-of-day threshold zones, plus local-time (UTC offset / DST) helpers.
#
# Deliberately pure Python with no hardware imports, so the logic can be
# exercised on a PC as well as on the device.
#
# A value's "on"/"off" are the defaults; an optional "schedule" overrides them
# for daily zones. Each zone applies from its "from" time until the next zone
# starts, wrapping past midnight (so the last zone of the day runs until the
# first zone of the next day). Anything a zone doesn't specify is inherited
# from the defaults. The defaults are also used whenever the time is unknown
# (no network, NTP not yet synced, etc).
#
#   "on": 60, "off": 65,
#   "schedule": [
#     { "from": "07:00", "on": 70, "off": 75 },
#     { "from": "21:30", "on": 55 }
#   ]

def parse_hhmm(text):
    parts = str(text).split(':')
    if len(parts) != 2:
        raise ValueError(f'invalid time "{text}"; expected "HH:MM"')
    h = int(parts[0])
    m = int(parts[1])
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise ValueError(f'invalid time "{text}"; expected "HH:MM"')
    return h * 60 + m

class Zone:
    def __init__(self, start, on, off, label):
        self.start = start # minutes since midnight (local)
        self.on = on
        self.off = off
        self.label = label

def _check(on, off, label):
    # the latch turns on at/below "on" and off at/above "off"; if those overlap
    # the relay would toggle every cycle, which is exactly what we don't want
    if on >= off:
        raise ValueError(f'{label}: "on" ({on}) must be less than "off" ({off})')

class Schedule:
    def __init__(self, cfg, name = '?'):
        self.default = Zone(0, cfg["on"], cfg["off"], 'default')
        _check(self.default.on, self.default.off, f'{name} default')

        zones = []
        for entry in cfg.get("schedule") or []:
            start = parse_hhmm(entry["from"])
            on = entry.get("on", self.default.on)
            off = entry.get("off", self.default.off)
            label = f'from {entry["from"]}'
            _check(on, off, f'{name} {label}')
            zones.append(Zone(start, on, off, label))
        zones.sort(key = lambda z: z.start)
        for i in range(1, len(zones)):
            if zones[i].start == zones[i - 1].start:
                raise ValueError(f'{name}: duplicate schedule time {zones[i].label}')
        self.zones = zones

    def active(self, minutes):
        """The zone in effect at the given local minutes-since-midnight,
        or the default zone if the time is unknown (None) or unscheduled."""
        if minutes is None or not self.zones:
            return self.default
        current = self.zones[-1] # before the first start: yesterday's last zone
        for zone in self.zones:
            if zone.start <= minutes:
                current = zone
            else:
                break
        return current

# --- local time ---

def _dow_sunday0(y, m, d):
    # Sakamoto's algorithm; 0 = Sunday
    t = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    if m < 3:
        y -= 1
    return (y + y // 4 - y // 100 + y // 400 + t[m - 1] + d) % 7

def eu_dst(y, mo, d, h):
    """EU/UK summer time, given a UTC date/hour: from 01:00 UTC on the last
    Sunday in March until 01:00 UTC on the last Sunday in October."""
    if mo < 3 or mo > 10:
        return False
    if mo > 3 and mo < 10:
        return True
    last_sunday = 31 - _dow_sunday0(y, mo, 31) # March and October both have 31 days
    if mo == 3:
        return d > last_sunday or (d == last_sunday and h >= 1)
    return d < last_sunday or (d == last_sunday and h < 1)

class TimeZone:
    def __init__(self, cfg = None):
        cfg = cfg or {}
        self.offset = int(round(float(cfg.get("utc_offset", 0)) * 60)) # minutes
        self.dst = cfg.get("dst", "none")
        if self.dst not in ("none", "eu"):
            raise ValueError(f'unknown dst rule "{self.dst}"; expected "eu" or "none"')

    def local_minutes(self, utc):
        """Local minutes-since-midnight from a UTC time tuple
        (year, month, day, hour, minute, ...) as returned by time.gmtime()."""
        y, mo, d, h, mi = utc[0], utc[1], utc[2], utc[3], utc[4]
        offset = self.offset
        if self.dst == "eu" and eu_dst(y, mo, d, h):
            offset += 60
        return (h * 60 + mi + offset) % 1440

def format_minutes(minutes):
    if minutes is None:
        return '--:--'
    return '%02d:%02d' % (minutes // 60, minutes % 60)
