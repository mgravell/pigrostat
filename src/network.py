import rp2, network, time, ntptime, ujson, socket
from machine import Pin

# set time to known-bad Jan 1st 2023; this simplifies debugging, because Thonny
# synchronizes the clock for us automatically, and we want known-state
machine.RTC().datetime((2023, 1, 1, 1, 0, 0, 0, 0))
        
try:
    print("Loading network configuration...")
    f = open('network.json', 'r')
    config = ujson.loads(f.read())
    f.close()

    rp2.country('UK') # channel frequencies
    host = "pigrostat" if "hostname" not in config else config["hostname"]
    print(f'Connecting to {config["ssid"]} as {host}')
    network.hostname(host)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # print(wlan.scan()) # show available SSIDs - useful in case of problems
    wlan.connect(config["ssid"], config["password"])
    # Wait for connect or fail
    retries = 10
    while retries > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        retries -= 1
        print('...')
        time.sleep(1)
    
    if wlan.isconnected():
        print(f'Connected successfully; attempting to set network time...')
        
        retries = 10
        while retries > 0:
            retries -= 1
            try:
                ntptime.settime()
                print(f'Time updated via NTP')
                break
            except:
                pass

        print(f'Time (UTC): {time.localtime()}')
            
        led = Pin("LED", Pin.OUT)
        send_ip = config["send_ip"]
        send_port = config["send_port"]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while True:
            led.on()
            try:
                message = "Test message"
                sock.sendto(message.encode(), (send_ip, send_port))
            except:
                print ("Failure sending UDP packet")
                raise
            finally:
                led.off()

            time.sleep(2)
except:
    print('Network failure')
    raise