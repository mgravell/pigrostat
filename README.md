# pigrostat

A basic hygrostat implementation for Pi Pico, SHT30 and relay HAT, using MicroPython

## Status

This is a work-in-progress, and is a hobby project for myself. It involves controlling external electrical devices, and the relays involved can work
with low-voltage DC or mains-voltage AC; I am *very deliberately* not going to offer any advice on how you use this information,
as no matter what I say, there will be gaps and I don't want to be sat in a court-room with some lawyer saying:

> I put it to the court that you recklessly failed to tell my client that they couldn't use this device to control the lights in the shower,
> and this failure on your part led to the fire that ultimately destroyed the family home; we ask the court to order compensation accordingly.

Seriously, this is a "maker" project; do your own due diligence and use common sense. If you don't know *exactly* what you're doing
with electricity, maybe just buy off-the-shelf.

Status:

- [x] Pico H provisioned
- [x] Basic status LED and debug output
- [x] Communication over I2C with SHT30 sensor
- [x] Communication over I2C with relay kit
- [x] Basic external configuration
- [x] Display over I2C with SSD1306
- [x] Display over I2C with LCD1602
- [x] I2C shared bridge logic
- [x] Main work loop and latch logic
- [x] In-situ "on/off" comparison vs off-the-shelf hygrostat
- [ ] Code refactor (in particular: object model separate to configuration model)
- [ ] Enclosure and power
  - (ordered)
- [ ] Networking
  - [x] Pico WH provisioned
  - [x] Network configuration
  - [x] Reliable time
  - [ ] Status broadcast
  - [ ] Server/listener
  - [ ] Remote configure
- [ ] Timer functionality (requires reliable time)

## Motivation

tl;dr: prebuilt hygrostat relays keep failing!

I look after a number of exotic animals, which require specific environments; some require specific humidity - for example
Phyll (an [African bullfrog](https://en.wikipedia.org/wiki/African_bullfrog)) likes a humidity of around 60-80%. This is
usually achieved via a hygrostat - a controller device that is basically a humidity sensor paired to a relay, to manage the
power for a separate humidifier device.

Sounds great - just buy off the shelf, job done? Well, not really. I've had a terrible experience with hygrostats, even those
designed and marketed specifically for exotic animals. In particular, the relays keep failing! The device reports that it
has switched the power off, but: the power just keeps on flowing - leading to the environment going absurdly over-humid. I
have exhausted every supplier and seen this on *every available device* - from £25 to £250 (GBP). Sometimes the devices last
a few months, more recently they've been lasting a matter of weeks or even days (which at least means I can send them back).
Having to keep replacing and reconfiguring hygrostats is a huge inconvenience (even if they're often failing well inside of their
warranty period, so it doesn't actually hurt me financially), and having the right conditions isn't ideal for the animals!

And yes, I've had my electrical supply tested. And no, this isn't an issue with electrical devices operating in a humid
environment: the only thing inside the vivarium is the sensor - the relay etc is external in a regular UK domestic environment.

## The hardware

tl;dr: Pi Pico with a SHT30 and relay kit; right now, purely experimental on a breadboard:

![Pi Pico and SHT30 on breadboard, showing temperature and humidity on a basic display](https://github.com/mgravell/pigrostat/blob/main/img/breadboard.jpg?raw=true)

In frustration, I decided to see what I could do myself! I've tinkered with a Raspberry Pi in the past, and I have a *conceptual*
understanding that the GPIO pins can be used to control things like sensors, but: I've never done this before - what the heck,
even if I fail, I can learn some things! And if the relays still fail: at least I can simply swap the relay! Or if I'm using a multi-relay
board: rotate between different relays on the same board, murdering them each in turn.

A typical category of sensors for such devices is the SHT30; these are available in a few form factors, but since this will be
inside an animal environment, I want an enclosed device. For example, [here](https://thepihut.com/products/sht30-temperature-and-humidity-sensor-wired-enclosed-shell)
or [here](https://thepihut.com/products/sht-30-mesh-protected-weather-proof-temperature-humidity-sensor). I went for the latter
mostly for the single enclosed, heavy duty cable, which seems like a better choice for my scenario.

I originally planned on using a Pi 4 Model B (upgrading to Pi 5 when available), but on a whim (and because it was the start of December),
I also picked up the [Pi Pico H advent calendar](https://thepihut.com/products/maker-advent-calendar-includes-raspberry-pi-pico-h) for £40 (the
Pi Pico itself is an astonishing £3.90 or £4.80 for the H variant, i.e. with headers (pins) attached), which includes
a Pi Pico H and a range of additional bits - breadboard, wires, buttons, sensors, lights, a basic display, etc. I got this working with
the SHT30 very quickly, reading and displaying the humidity and temperature, so now all we need is to control the power!

The Pi is a low power device, so it won't be *supplying* power to the humidifer; all we want to do is turn a swich on or off - what we
need is a *relay*. Since we can monitor humidity *and* temperature, we might want to control multiple devices independently; I really
like the look of [this Pico Relay Board](https://thepihut.com/products/raspberry-pi-pico-relay-board), since it has 4 relays *and* mirrors
the GPIO pins so that I can easily connect the sensor (via the "male" pins just outside the socket for the Pico), but that is out of stock
currently; instead, I picked up a [Dual Channel Relay HAT](https://thepihut.com/products/dual-channel-relay-hat-for-raspberry-pi-pico) - but *that*
doesn't mirror the pins (boo!), so I'm using a [Pico Omnibus Dual Expander](https://thepihut.com/products/pico-omnibus-dual-expander) - with the
relay on one side, and the GPIO pins mirrored on the other.

In addition to the essentials, I also have a few ideas for using bits from the advent calendar kit:

- the display can show the current humidity, temperature and other information
- there are inbuilt status lights on the relay kit, and a user-controllable light on the Pico, but I could use additional pins to control custom status LEDs
- since we have a speaker, maybe we might want an audible alarm for out-of-range conditions (significantly too humid, dry, hot, cold)
- it might be nice to have some basic control for changing the target humidity via push-buttons

(note that some more advanced displays are available at reasonable prices with buttons built-in; this might be worth exploring)

Finally, we will want to enclose the device - even if we limit ourselves to low DC voltages, we don't want random debris falling on either the relays
or the Pico pins. Since I don't have a 3D printer, I'm looking at [things like this](https://www.switchelectronics.co.uk/pages/search-results-page?q=enclosure),
but I need to see the final size before I order anything.

## Additional hardware considerations

I did not put a lot of thought into the choice of microcontroller; Pi Pico is *readily available*, well known, cheap, and seems a popular choice for hobbyists, but
mostly it was simply "I've used Pi before, I have reasonable confidence that this will be accessible to a microcontroller n00b". A *wide range* of similar
devices are available, in particular competing with the Arduino range. I haven't used Arduino (again: n00b), so perhaps
[check thoughts like this](https://www.tomshardware.com/features/raspberry-pi-pico-vs-arduino). To emphasize, my personal decision making process was more
"ooh, that looks like fun and something that might work, I'll get one of those", when I saw the advent calendar pack.

The Pico H is not network enabled; that's fine for now, but if we want better reporting: the Pico WH has the same form-factor and pinout,
but with 802.11 b/g/n WiFi and Bluetooth 5.2. Running at 133Mhz by default (overclockable) with two ARM Cortex-M0+ cores and 2MB flash memory, it is
*more than* powerful enough to drive most typical controller scenarios. With 40 IO pins (26 usable for GPIO), we have lots of options for controlling devices -
and if we need even more, the RP2040-PICO30 has the same form-factor and makes 30 pins usable for GPIO (sacrificing some redundant ground pins), and up to
16MB flash memory (the maximum addressable via XIP on the device) - but since I2C allows multiple devices to share the same bus (and pins) by having
different addresses, this usually isn't necessary. Different I2C device categories (sensors, displays, etc) usually have different default addresses
(defined by the hardware), and some allow the address to be tweaked by shorting (jumper, etc) at the device.

In theory multiple SHT30 sensors could be used to monitor multiple environments:

- multiple identical sensors can *theoretically* share an I2C bus by changing the address, but not all SHT30 devices support this option (especially the
  enclosed variants)
- we can use separate sets of GPIO pins for independent I2C buses
- we can use an [I2C Multiplexer](https://thepihut.com/products/adafruit-tca9548a-i2c-multiplexer) to indepndently access multiple I2C devices
  *with the same address* on a single bus

I'll keep this option up my sleeve, but it doesn't seem useful unless I'm using [a lot more relays](https://www.amazon.com/dp/B084BR4TDH),
and the length of the wire on most sensors makes it impractical (and prone to cable hell). Given the price of the components, in all honesty if I wanted that I'd probably just go with multiple
entire Pico+sensor+relay setups.

## The software

tl;dr: MicroPython

Next, we need to actually code the logic. The Pico is a controller chip, not a full computer. I'm normally a .NET person, but I don't know
enough about [.NET Micro Framework](https://en.wikipedia.org/wiki/.NET_Micro_Framework) or the availability of drivers to make that my first choice.
The *lingua franca* for hobbyists on the Pico seems to be MicroPython via [Thonny](https://thonny.org/):

- a wide range of drivers for devices are readily available
- there is an active community of hobbyist users
- Python is easy enough for beginners, and more than sufficient for our needs
- Thonny can prepare the device for us, flashing the firmware to install the Python interpreter and our files

MicroPython is a subset of Python intended for this constrained category of device; it seems to work fine; I *did* have some problems with
prebuilt SHT30 drivers, but [found workarounds on maker forums](https://forum.micropython.org/viewtopic.php?f=21&t=12900&sid=cea18d6e14c53784f6e70ef1f50837c7&start=10#p70260).

You can see the status of this in [/src](https://github.com/mgravell/pigrostat/blob/main/src/)

Thonny allows you to run arbitrary .py files on the device directly via the play button; to have a script run automatically when the controller boots,
we simply save it as `main.py`.

Right now the code is ... "functional" - which is to say: it mostly works, but it isn't elegant or well structured. When I know what it needs
to actually *do*, I'll consider tidying it up some more, honest! Considering that I've never really been a Python person, "it mostly works"
is not a bad place to start.