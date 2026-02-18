# Airport OSM
Airport OSM is a tool that provides taxi instructions for aircrafts at any airport around the world. 

# Installation

`pip install airport-osm`

or

`uv add airport-osm`

# Usage

```python
>>>from airport_osm import AirportOSM
>>>airport = AirportOSM(icao_code="YMML")
>>>instructions = airport.taxi_from_gate_to_runway(gate="13", runway="16")
Taxi via, Golf, Sierra, Uniform, Alpha, Bravo, hold short runway 16
```

# Notes
- This tool is intended to work with LLM based applications and therefore has a string output. But this can be turned off by setting the `turn_instructions=False`
- It uses OSMnx API but requires no API token/authentication. However, airport data is cached locally, which can be deleted if latest data is required.

# Contributions
Contributions are welcome. Feel free to create an issue or raise a PR