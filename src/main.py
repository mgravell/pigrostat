import time, sht30, ujson
from machine import I2C, SoftI2C, Pin, ADC
from ssd1306 import SSD1306_I2C

try:
    print("Loading configuration...")
    f = open('config.json', 'r')
    config = ujson.loads(f.read())
    f.close()

    class DummyPin:
        def on(self):
            pass
        def off(self):
            pass
        def value(self):
            return 0
        def value(self, val):
            pass

    try:
        led = machine.Pin.board.LED
        led.on()
        print(f'Using onboard LED: {led}')
    except:
        print('Using dummy LED')
        led = DummyPin()
        
    class DebugDisplay:
        def fill(self, x):
            pass # no-op

        def show(self):
            pass # no-op

        def text(self, msg, x, y):
            print(msg)

    def getI2C(bridges, sda, scl, addr, label):
        key = (sda, scl)
        if key in bridges:
            print(f"Reusing I2C for {key}")
            i2c = bridges[key]
        else:
            print(f"Creating new I2C bridge for {key}")
            # the sensor fails with hardware I2C, but works with SoftI2C; I don't know why
            i2c = SoftI2C(sda=Pin(sda), scl=Pin(scl))
            time.sleep(1) # allow things to initialize
            bridges[key] = i2c

        print(f"Scanning for I2C device {hex(addr)} ({addr})...")
        devices = i2c.scan()
        print(f'Available devices: {devices}')
        
        if addr in devices:
            print(f'Device ({label}) found')
            return i2c

        print(f'Device ({label}) not found')
        return None
    
    display = DebugDisplay()
    bridges = dict() # I2C could be shared between pins; we'll re-use
    
    if 'display' in config:
        try:
            print("Configuring display...")
            cfg = config["display"]
            i2c = getI2C(bridges, cfg["sda"], cfg["scl"], cfg["addr"], 'display')
            
            if i2c is not None:
                display = SSD1306_I2C(cfg["width"], cfg["height"], i2c, cfg["addr"])
                display.fill(0)
                display.text('Initializing...', 0, 0)
                display.show()                
        except:
            print('Fault configuring display')
            raise
    else:
        print('Display not configured')

    sensor = config["sensor"]
    print(sensor)
    values = sensor["values"]
    print(f'Sensor has {len(values)} output values')
    for val in values:
        if 'relay' in val:
            if val["relay"] is None:
                val.pop("relay")
            else:
                val["relay"] = Pin(val["relay"], Pin.OUT)

    print("Configuring sensor...")
    i2c = getI2C(bridges, sensor["sda"], sensor["scl"], sensor["addr"], 'sensor')
    sht = None
    if i2c is not None:
        sht=sht30.SHT30(i2c=i2c, i2c_address=sensor["addr"])

    cpu = machine.ADC(4) # allows access to CPU temperature

    # main loop (note: no point running if we don't have a sensor)
    print('Running...')
    while sht is not None:
        # enable the device LED to show we're alive
        led.on()

        display.fill(0) # wipe and redraw

        # read the values from the sensor
        tuple = sht.measure()
        for idx, x in enumerate(values):
            val = tuple[idx]
            
            status = ""
            if 'relay' in x:
                relay = x["relay"]
                current = relay.value()
                target = current # assume no change

                # logic here is absurdly simple latch; we don't need to be clever
                if current >= 0.9: # treat as on
                    if val >= x["off"]:
                        target = 0
                else:
                    if val <= x["on"]:
                        target = 1
                
                status = "on" if target >= 0.9 else "off"
                    

                if target != current:
                    relay.value(target)
                    print(f'{x["name"]} now {relay.value()}')
                    
            display.text(f'{x["label"]}: {round(val, 1)} {x["unit"]} {status}', 0, idx * 12)

        # read the ambient CPU temperature (ADC 4 is a slope showing temp,
        # with defined gradient/origin; these numbers are from the spec)
        # see: https://electrocredible.com/raspberry-pi-pico-temperature-sensor-tutorial/
        ADC_voltage = cpu.read_u16() * (3.3 / (65536))
        cputemp = 27 - (ADC_voltage - 0.706) / 0.001721

        display.text(f'CPU: {round(cputemp, 1)} C', 0, 24)
        display.show()

        # pause for long enough to ensure the status LED is visible
        time.sleep(0.05)

        # show that we're done thinking (thinking will appear as a flash)
        led.off()

        # wait a second (there's no point updating too frequently)
        time.sleep(config["delay"])
finally:
    # show exit condition
    try:
        display.fill(0) # wipe and redraw
        display.text('Terminated', 0, 0)
        display.show()
    except:
        pass

    for i in range(5):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
