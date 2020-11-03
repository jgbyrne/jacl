## JACL - Jack's Application Config Language

`JACL` (pronounced Jackal) is an experimental new configuration language.

It is intended to be more expressive than TOML, more minimal than YAML, and more readable than JSON.

### Example

#### Config

```JACL
stations = {
    r4 {
        name = "Radio 4"
	freq = ("FM", 93)
    }

    r6 {
	name = "Radio 6 Music"
	freq = ("DAB", "12B")
    }

    (r4, r6) {
	broadcaster = "BBC"
        website = "https://www.bbc.co.uk/sounds/"
    }

    p6 {
	broadcaster = "DR"
	name = "P6 Beat"
	freq = false
	website = "https://www.dr.dk/radio/p6beat/"
    }

    weekdays = r4
    weekends = p6
}

alarms = [
    {
        days = "weekends"; time = "09:55"
	alarm = "skylarks"; volume = 3.7
    }

    {
        days = "weekdays"; time = "06:55"
	alarm = "pulsar"; volume = 5.9 
    }
]

```

#### Code

```Python
from jacl import Jacl

config = Jacl.from_file("radio.jacl")

print("My Stations:")
for s in config.stations:
    print("* {} ({}): {}".format(s.key, s.broadcaster, s.name))

print("\nWeekday Frequency: {1} {0}"
      .format(*config.stations.weekdays.freq))

print("\nAlarm Times: {}".format([a.time for a in config.alarms]))
```

#### Output

```
My Stations:
* r4 (BBC): Radio 4
* r6 (BBC): Radio 6 Music
* p6 (DR): P6 Beat

Weekday Frequency: 93 FM

Alarm Times: ['09:55', '06:55']
```
