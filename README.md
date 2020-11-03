## JACL - Jack's Application Config Language

`JACL` (pronounced Jackal) is an experimental new configuration language.

It is intended to be more expressive than TOML, more minimal than YAML, and more readable than JSON.

### Structures and Concepts

The core data-structure behind JACL is the ordered hash table. This structure can be used in two forms, as a table (notated with square brackets) or as an object (notated with curly braces).

A table can only store objects, as shown below:

```
my_table = [
    {
        desc = "An anonymous object, the first in the table"
    }

    wren {
        desc = "An object with a key for convinient access"
    }

    # An object with just a key and no data
    mallard

    (swan, cygnet) {
        desc = "Two objects defined with the same data"
    }

    mallard {
        desc = "An object patched with additional data"
    }
]
```

An iteration through this table would yield first the anonymous object, then `wren`, then `mallard`, then `swan`, then `cygnet`.

Objects are a strict superset of tables. They encapsulate an ordered hash table of objects, just as tables do. However, they also support bindings of properties to data, and can be marked with a tag that is unique within their immediate scope.

```
my_object = {
    robin {
        desc = "Just as with tables, objects can store objects"
    }

    best_bird = lapwing {
        desc = "However, they can also map data to paramaters"
    }

    my_data = (100, false, (12.8, true, robin), "Basingstoke")

    {
        desc = "Object declarations and property bindings can coexist"
    }
}
```

The top-level of a JACL document is implicitly an object.

It is important to note that the source of truth for an object is its declaration and thus its location in the ordered hash table of its containing scope (be that another object or a table). Bindings only truly hold keywise references to objects, not the objects themselves, and such objects are required to inhabit the same scope.

The datatypes in JACL are:
* String
* Integer
* Float
* Boolean
* Key
* Tuple
* Table
* Object


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
