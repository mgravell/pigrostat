# Periodic WiFi connect + NTP time sync, for Pico W / WH.
#
# The RP2040 RTC has no battery and starts at a fixed date on every boot, so
# we only trust the clock after a successful NTP sync; we then re-sync
# periodically to correct drift. Between syncs WiFi is switched off (unless
# "stay_connected" is set), and the RTC keeps time on its own.
#
# Settings come from network.json, which is deliberately *not* checked in
# (see network.example.json). If the file is missing, or the firmware has no
# network support (plain Pico / Pico H), load() returns None and the caller
# should carry on without time.
#
# Note: this file must not be called network.py, as that would collide with
# MicroPython's built-in "network" module.

import time, ujson

try:
    import network, ntptime
except ImportError:
    network = None

# ticks_ms() wraps, and ticks_diff() is only valid for spans under ~6 days
MAX_INTERVAL_HOURS = 72

def utc_now():
    # on MicroPython localtime() and gmtime() are both UTC (no time zones);
    # prefer gmtime() where available so this also reads correctly on a PC
    return (time.gmtime if hasattr(time, 'gmtime') else time.localtime)()

class NetClock:
    def __init__(self, cfg):
        self.ssid = cfg["ssid"]
        self.password = cfg["password"]
        self.hostname = cfg.get("hostname", "pigrostat")
        self.country = cfg.get("country", "GB") # WiFi regulatory domain (ISO 3166 alpha-2)
        self.ntp_host = cfg.get("ntp_host", "pool.ntp.org")
        self.connect_timeout = cfg.get("connect_timeout", 15) # seconds
        self.stay_connected = cfg.get("stay_connected", False)
        sync_hours = min(cfg.get("sync_hours", 6), MAX_INTERVAL_HOURS)
        retry_minutes = cfg.get("retry_minutes", 5)
        self.__sync_ms = int(sync_hours * 3600 * 1000)
        self.__retry_ms = int(retry_minutes * 60 * 1000)
        self.__last_attempt = None
        self.__synced = False
        self.wlan = None

    @staticmethod
    def load(path = 'network.json'):
        if network is None:
            print('No network support in this firmware; time sync disabled')
            return None
        try:
            f = open(path, 'r')
        except OSError:
            print(f'{path} not found; time sync disabled')
            return None
        try:
            cfg = ujson.loads(f.read())
        finally:
            f.close()
        return NetClock(cfg)

    def synced(self):
        """True once NTP has succeeded at least once since boot."""
        return self.__synced

    def due(self):
        """True if it is time to (re)try a sync; retries sooner until the
        first success."""
        if self.__last_attempt is None:
            return True
        interval = self.__sync_ms if self.__synced else self.__retry_ms
        return time.ticks_diff(time.ticks_ms(), self.__last_attempt) >= interval

    def __connect(self):
        try:
            network.country(self.country)
        except AttributeError: # older firmware
            import rp2
            rp2.country(self.country)
        network.hostname(self.hostname)

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        self.wlan = wlan
        if wlan.isconnected():
            return True

        print(f'Connecting to {self.ssid} as {self.hostname}...')
        wlan.connect(self.ssid, self.password)
        deadline = time.ticks_add(time.ticks_ms(), int(self.connect_timeout * 1000))
        while not wlan.isconnected():
            status = wlan.status()
            if status < 0: # e.g. wrong password, no AP found
                print(f'WiFi connect failed, status {status}')
                return False
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                print(f'WiFi connect timed out, status {status}')
                return False
            time.sleep(0.25)
        print(f'WiFi connected: {wlan.ifconfig()[0]}')
        return True

    def __disconnect(self):
        if self.wlan is None or self.stay_connected:
            return
        try:
            self.wlan.disconnect()
            self.wlan.active(False)
        except Exception as e:
            print(f'WiFi disconnect error: {e}')

    def sync(self):
        """Connect, set the RTC from NTP (UTC), disconnect. Blocks for up to
        connect_timeout plus a few seconds; returns True on success."""
        self.__last_attempt = time.ticks_ms()
        ok = False
        try:
            if self.__connect():
                ntptime.host = self.ntp_host
                for attempt in range(3):
                    try:
                        ntptime.settime() # sets the RTC to UTC
                        ok = True
                        break
                    except Exception as e:
                        print(f'NTP attempt {attempt + 1} via {self.ntp_host} failed: {e}')
                        time.sleep(1)
        except Exception as e:
            print(f'Time sync error: {e}')
        finally:
            self.__disconnect()

        if ok:
            self.__synced = True
            print(f'Time synced via NTP; UTC now {utc_now()}')
        elif self.__synced:
            print('Time re-sync failed; continuing on RTC')
        else:
            print('Time sync failed; using default thresholds until it succeeds')
        return ok
