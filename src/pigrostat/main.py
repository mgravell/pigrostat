import time, sht30, ujson
from machine import I2C, SoftI2C, Pin, ADC
from ssd1306 import SSD1306_I2C
from pico_i2c_lcd import I2cLcd

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
        led = Pin("LED", Pin.OUT)
        led.on()
        print(f'Using onboard LED: {led}')
    except:
        print('Using dummy LED')
        led = DummyPin()
        
    class Display:
        def clear(self, hard = False):
            pass # no-op

        def show(self):
            pass # no-op

        def simple(self, msg):
            self.clear(True)
            self.text(msg, 0)
            self.show()

        def text(self, msg, y):
            print(msg)

    class Lcd1602Display(Display):
        def __init__(self, lcd):
            self.__lcd = lcd

        def clear(self, hard = False):
            if hard:
                self.__lcd.clear()

        def text(self, msg, y):
            if y >= 0 and y < 2:
                self.__lcd.move_to(0, y)
                self.__lcd.putstr(msg)
                if len(msg) < 16:
                    self.__lcd.move_to(len(msg), y)
                    self.__lcd.putstr(" " * (16 - len(msg)))
            else:
                super().text(msg, y) # use default logic

    class Ssd1306Display(Display):
        def __init__(self, ssd):
            self.__ssd = ssd

        def clear(self, hard = False):
            self.__ssd.fill(0)

        def text(self, msg, y):
            self.__ssd.text(msg, 0, y * 12)

        def show(self):
            self.__ssd.show()

    def getI2C(bridges, sda, scl, addr, label):
        key = (sda, scl)
        if key in bridges:
            print(f"Reusing I2C bridge for {key}")
            i2c = bridges[key]
        else:
            print(f"Creating new I2C bridge for {key}")

            # hardware I2C bridge seems less reliable; may times hardware_test.py
            # will work fine with software, and utterly fail with hardware bridge
            # note this may be sub-revision related; hardware I2C on Pico WH seems
            # more reliable than hardware I2C on Pico H - or maybe I somehow destroyed
            # the I2C controller by shorting bad pins, who knows!
            i2c = SoftI2C(sda=Pin(sda), scl=Pin(scl))

            """ # this would be nice, but is less reliable
            # Pico has two hardware I2C controllers; module 0 handles SDA 0/4/8/12/16/20,
            # module 1 handles SDA 2/6/10/14/18/26 (where SCL=SDA+1); try to use hardware
            try:
                i2c = I2C((sda >> 1) & 1, sda=Pin(sda), scl=Pin(scl))
                print(f"Using hardware I2C, controller {(sda >> 1) & 1}")
            except ValueError:
                print("Unable to use hardware I2C; trying software...")
                i2c = SoftI2C(sda=Pin(sda), scl=Pin(scl))
            """
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

    def statusString(val):
        return "on" if val >= 0.8 else "off"
    
    display = Display()
    bridges = dict() # I2C could be shared between pins; we'll re-use
    
    if 'display' in config:
        try:
            print("Configuring display...")
            cfg = config["display"]
            i2c = getI2C(bridges, cfg["sda"], cfg["scl"], cfg["addr"], 'display')
            
            if i2c is not None:
                print(f'Configuring {cfg["type"]} display...')
                if cfg["type"] == "ssd1306":
                    display = Ssd1306Display(SSD1306_I2C(cfg["width"], cfg["height"], i2c, cfg["addr"]))
                elif cfg["type"] == "lcd1602":
                    display = Lcd1602Display(I2cLcd(i2c, cfg["addr"], 2, 16))
        except:
            print('Fault configuring display')
            raise
    else:
        print('Display not configured')

    display.simple("Initializing...")

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

        display.clear() # soft clear; minimize 1602 flicker

        # read the values from the sensor
        try:
            tuple = sht.measure()
        except:
            tuple = None
        
        for idx, x in enumerate(values):
            val = None if tuple is None else tuple[idx]
            
            if val is None:
                display.text(f'{x["label"]}: ERR', idx)
            else:
                try:
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

                        status = statusString(target)

                        if target != current:
                            relay.value(target)
                            print(f'{x["name"]} now {statusString(relay.value())}')

                    unit = x["unit"].replace("°", chr(223)) # fix code-page
                    display.text(f'{x["label"]}: {round(val, 1)} {unit} {status}', idx)
                except:
                    display.text(f'{x["label"]}: ERR', idx)

        # read the ambient CPU temperature (ADC 4 is a slope showing temp,
        # with defined gradient/origin; these numbers are from the spec)
        # see: https://electrocredible.com/raspberry-pi-pico-temperature-sensor-tutorial/
        ADC_voltage = cpu.read_u16() * (3.3 / (65536))
        cputemp = 27 - (ADC_voltage - 0.706) / 0.001721

        display.text(f'CPU: {round(cputemp, 1)} C', 2)
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
        display.simple("Sensor failure" if sht is None else "Terminated")
        for i in range(5):
            led.on()
            time.sleep(0.5)
            led.off()
            time.sleep(0.5)
    except:
        pass

    # something went wrong, but we probably want to keep working; try rebooting
    try:
        display.simple('Rebooting')
        time.sleep(1)
        machine.reset()
        display.simple('Reboot failed') # we shouldn't get here
    except:
        pass
