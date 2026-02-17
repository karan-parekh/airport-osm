from geopandas import GeoDataFrame
from typing_extensions import LiteralString


class BearingNotFoundError(Exception):
    pass


def generate_turn_instructions(route_gdf: GeoDataFrame) -> str:
    """
    Returns turn by turn instructions for the route.
    """
    gdf = route_gdf.fillna(value=0)
    instructions = ["Taxi via"]
    gdf_len = gdf.shape[0]

    # Start with edge at index 1, as the aircraft is expected to be at 0th index.
    for i in range(1, gdf_len):
        prev_edge = gdf.iloc[i - 1]
        curr_edge = gdf.iloc[i]

        prev_ref = prev_edge.get("ref", None)
        curr_ref = curr_edge.get("ref", None)
        if not isinstance(curr_ref, str):
            continue

        if curr_ref == prev_ref:
            continue

        taxiway = to_phonetic(curr_ref)
        if taxiway == instructions[-1]:
            continue

        instructions.append(taxiway)

    return ", ".join(instructions).strip()


def get_next_move(prev_edge, curr_edge):
    b1 = prev_edge.get("bearing")
    b2 = curr_edge.get("bearing")
    if b1 is None or b2 is None:
        raise BearingNotFoundError(
            f"Bearing not found for either {prev_edge['ref']} or {curr_edge['ref']}"
        )

    angle_change = (float(b2) - float(b1) + 180) % 360 - 180
    move = "continue"
    if angle_change > 3:
        move = "turn right"
    if angle_change < -3:
        move = "turn left"

    return move


def to_phonetic(word: str) -> LiteralString:
    """
    Convert a single alphabet letter to its ICAO aviation phonetic equivalent.

    Example:
        to_phonetic("A") -> "Alpha"
        to_phonetic("A1") -> "Alpha 1"
    """
    phonetic_map = {
        "A": "Alpha",
        "B": "Bravo",
        "C": "Charlie",
        "D": "Delta",
        "E": "Echo",
        "F": "Foxtrot",
        "G": "Golf",
        "H": "Hotel",
        "I": "India",
        "J": "Juliett",
        "K": "Kilo",
        "L": "Lima",
        "M": "Mike",
        "N": "November",
        "O": "Oscar",
        "P": "Papa",
        "Q": "Quebec",
        "R": "Romeo",
        "S": "Sierra",
        "T": "Tango",
        "U": "Uniform",
        "V": "Victor",
        "W": "Whiskey",
        "X": "X-ray",
        "Y": "Yankee",
        "Z": "Zulu",
    }

    phonetic = []
    for letter in word:
        if not letter.isalpha():
            phonetic.append(letter)
        else:
            phonetic.append(phonetic_map[letter.upper()])

    return " ".join(phonetic)
