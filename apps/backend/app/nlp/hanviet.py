"""Combine Vietnamese readings without adding Unihan-only readings to KANJIDIC2."""


def combined_readings(members, kanjidic, unihan):
    result = {}
    for char in sorted(members):
        values = list(kanjidic.get(char, []))
        if not values:
            if char in unihan:
                result[char] = unihan[char]
            continue
        shared = next((v for v in unihan.get(char, ([], None))[0] if v in values), None)
        if shared is not None:
            values.remove(shared)
            values.insert(0, shared)
        result[char] = (values, "kanjidic2_unihan" if shared is not None else "kanjidic2")
    return result
