import time, sht30, ujson
from machine import I2C, SoftI2C, Pin, ADC
from ssd1306 import SSD1306_I2C

print("Loading configuration...")
f = open('config.json', 'r')
config = ujson.loads(f.read())
f.close()

onboardLED = Pin(25, Pin.OUT)

display = None;
if 'display' in config:
    print("Configuring display...")
    cfg = config["display"]
    i2c_display=I2C(0, sda=Pin(cfg["sda"]), scl=Pin(cfg["scl"]), freq=cfg["freq"])
    time.sleep(1) # allow things to initialize
    print("Scanning for display I2C...")
    devices = i2c_display.scan()
    if len(devices) == 1:
        print(f'Discovered at {devices[0]}')
        display = SSD1306_I2C(cfg.width, cfg.height, i2c_display)
    else:
        print('Display is configured but was not found')
else:
    print('Display not configured')

sensor = config["sensor"]
print(sensor)
values = sensor["values"]
print(f'Sensor has {len(values)} output values')
for val in values:
    print(f'Disabling {val["name"]} relay')
    val["pin"] = Pin(val["relay"], Pin.OUT)
    val["pin"].value(0)


print("Configuring sensor...")
i2c_sensor=SoftI2C(sda=Pin(sensor["sda"]), scl=Pin(sensor["scl"]))
print("Scanning for sensor...")
devices = i2c_sensor.scan()
sht = None
if sensor["addr"] in devices:
    print(f'Sensor detected, configuring...')
    sht=sht30.SHT30(i2c=i2c_sensor, i2c_address=sensor["addr"])
else:
    print('No sensor detected with specified address')

# main loop (note: no point running if we don't have a sensor)
print('Running...')
while sht is not None:
    # enable the device LED to show we're alive
    onboardLED.value(1)
    
    if display is not None:
        display.fill(0) # wipe and redraw
    
    if sht is not None:
        # read the values from the sensor
        tuple = sht.measure()
        if display is not None:
            display.text(f'T: {round(tuple[0], 1)}C',0,0)
            display.text(f'H: {round(tuple[1], 1)}%',0,12)
    
    if display is not None:
        # read the ambient CPU temperature (ADC 4 is a slope showing temp,
        # with defined gradient/origin; these numbers are from the spec)
        ADC_voltage = cpu.read_u16() * (3.3 / (65536))
        cputemp = 27 - (ADC_voltage - 0.706)/0.001721
        
        display.text(f'CPU: {round(cputemp, 1)}C',0,24)
        display.show()
    
    # pause for long enough to ensure the status LED is visible
    time.sleep(0.05)
    
    # show that we're done thinking (thinking will appear as a flash)
    onboardLED.value(0)
    
    # wait a second (there's no point updating too frequently)
    time.sleep(config["delay"])

print('Exit')