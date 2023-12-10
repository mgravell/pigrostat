import time, sht30
from machine import Pin, I2C, SoftI2C, ADC
from pico_i2c_lcd import I2cLcd

# quick test for pin setup, etc

print('Testing onboard LED')
led = Pin("LED", Pin.OUT)
for i in range(2):
    led.on()
    time.sleep(0.25)
    led.off()
    time.sleep(0.25)

print('Probing system voltage')
cpu = machine.ADC(4)
ADC_voltage = cpu.read_u16() * (3.3 / (65536))
cputemp = 27 - (ADC_voltage - 0.706) / 0.001721
print(f'CPU: {round(cputemp, 1)} °C')

def TestSht30(i2c):
    devices = i2c.scan()
    print(f'Devices: {devices}') # expect [68] if single device on bus
    for addr in devices:
        print(f'Testing SHT30 on {hex(addr)} ({addr})')
        try:
            sht = sht30.SHT30(i2c=i2c, i2c_address=addr)
            print(sht.measure())
        except:
            print('Failure communicating with SHT30')

# sensor
print('Testing sensor (software I2C)')
TestSht30(SoftI2C(sda=Pin(0), scl=Pin(1)))

print('Testing sensor (hardware I2C)')
TestSht30(I2C(0, sda=Pin(0), scl=Pin(1)))

def TestLcd1602(i2c, y, msg):
    devices = i2c.scan()
    print(f'Devices: {devices}') # expect [68] if single device on bus
    for addr in devices:
        print(f'Testing LCD1602 on {hex(addr)} ({addr})')
        try:
            lcd = I2cLcd(i2c, addr, 2, 16)
            lcd.move_to(0, y)
            lcd.putstr(f'{msg}: pass')
        except:
            print('Failure communicating with LCD1602')
    
# screen (1602)
print('Testing screen (software I2C)')
TestLcd1602(SoftI2C(sda=Pin(4), scl=Pin(5)), 0, 'soft I2C')

print('Testing screen (hardware I2C)')
TestLcd1602(I2C(0, sda=Pin(4), scl=Pin(5)), 1, 'hard I2C')

# relays
relays = [6, 7] # 2-relay HAT
# relays = [18, 19, 20, 21] # 4-relay board
print(f'Testing relays on {relays}')
for relay in relays:
    for i in range(2):
        pin = Pin(relay, Pin.OUT)
        pin.on()
        time.sleep(0.25)
        pin.off()
        time.sleep(0.25)
