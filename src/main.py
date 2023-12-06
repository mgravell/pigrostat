import time, sht30
from machine import I2C, SoftI2C, Pin, ADC
from ssd1306 import SSD1306_I2C

i2c_display=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
time.sleep(1) # allow things to initialize
print("Scanning for display I2C...")
print(i2c_display.scan()) # this is purely for debug; we don't need these values
display = SSD1306_I2C(128, 32, i2c_display)

i2c_hygro=SoftI2C(sda=Pin(4), scl=Pin(5))
print("Scanning for hygro I2C...")
print(i2c_hygro.scan()) # this is purely for debug; we don't need these values

print("Measuring SHT30 on 0x44...")
sht=sht30.SHT30(i2c=i2c_hygro, i2c_address=0x44) # 68, default addr

cpu = machine.ADC(4) # https://electrocredible.com/raspberry-pi-pico-temperature-sensor-tutorial/

onboardLED = Pin(25, Pin.OUT)

while True: # loop forever
    # enable the device LED to show we're alive
    onboardLED.value(1)
    
    # read the values from the sensor
    tuple = sht.measure()
    display.fill(0) # wipe and redraw
    display.text(f'T: {round(tuple[0], 1)}C',0,0)
    display.text(f'H: {round(tuple[1], 1)}%',0,12)
    
    # read the ambient CPU temperature (ADC 4 is a slope showing temp,
    # with defined gradient/origin; these numbers are from the spec)
    ADC_voltage = cpu.read_u16() * (3.3 / (65536))
    cputemp = 27 - (ADC_voltage - 0.706)/0.001721
    
    display.text(f'CPU: {round(cputemp, 1)}C',0,24)
    display.show()
    
    # show that we're done thinking (thinking will appear as a flash)
    onboardLED.value(0)
    
    # wait a second (there's no point updating too frequently)
    time.sleep(1.0)
