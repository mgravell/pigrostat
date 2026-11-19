# pigrostat

A basic hygrostat implementation for Pi Pico, SHT30 and relay HAT, using MicroPython

See [Journey.md](https://github.com/mgravell/pigrostat/tree/main/docs/Journey.md) for the full story!


## Configuration

Files in `src/pigrostat` (copy to the device alongside the `.py` files):

- `config.json` - sensor, relays, display, thresholds and schedules
- `network.json` - **not checked in**; copy `network.example.json` and add your WiFi details. Optional: without it
  (or on a non-W Pico) there is no time of day, and each value just uses its default `on`/`off`

### Time-of-day schedules

Each sensor value can have a `schedule` of daily zones that override its default `on`/`off`. A zone applies from
its `from` time until the next zone starts, wrapping past midnight; anything a zone omits is inherited from the
defaults. The defaults also apply whenever the time is unknown (e.g. before the first NTP sync).

```json
"on": 60, "off": 65,
"schedule": [
  { "from": "07:00", "on": 70, "off": 75 },
  { "from": "21:30", "on": 55 }
]
```

Times are local, per `clock` in `config.json`: `utc_offset` (hours) and `dst` (`"eu"` for UK/EU summer time, or
`"none"`). Time comes from NTP over WiFi at boot and every `sync_hours` (see `network.example.json`); WiFi is
switched off between syncs unless `stay_connected` is set.
