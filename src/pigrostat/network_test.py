import time, socket, machine, ujson
from machine import Pin
from netclock import NetClock, utc_now

# quick test for WiFi, NTP and UDP send (pairs with src/listener); needs a
# network.json - copy network.example.json and fill in your details

# set time to known-bad Jan 1st 2023; this simplifies debugging, because Thonny
# synchronizes the clock for us automatically, and we want known-state
machine.RTC().datetime((2023, 1, 1, 1, 0, 0, 0, 0))
print(f'Time (before): {utc_now()}')

clock = NetClock.load()
if clock is None:
    raise RuntimeError('Network not available')
clock.stay_connected = True # keep WiFi up for the UDP test below
if not clock.sync():
    raise RuntimeError('Time sync failed')
print(f'Time (UTC): {utc_now()}')

f = open('network.json', 'r')
config = ujson.loads(f.read())
f.close()

led = Pin("LED", Pin.OUT)
send_ip = config["send_ip"]
send_port = config["send_port"]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f'Sending to {send_ip}:{send_port}')
while True:
    led.on()
    try:
        result = sock.sendto("Test message".encode(), (send_ip, send_port))
        print(f'Sent: {result}')
    finally:
        led.off()
    time.sleep(2)
