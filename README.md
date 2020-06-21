

# xiaomi_vacuum
custom component for Vacuum 1C STYTJ01ZHM (dreame.vacuum.mc1808).
Rough around the edges, not all the commands work, not all attributes set up.
Needs a clean up
Using https://github.com/rytilahti/python-miio for the protocol.

add to custom components folder and 
```
vacuum:
  - platform: xiaomi_vacuum
    host: <ip>
    token: "<token>"
    name: <name>
```
works with https://github.com/denysdovhan/vacuum-card
