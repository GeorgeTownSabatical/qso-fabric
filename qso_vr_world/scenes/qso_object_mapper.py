def map_qsos_to_world(qso_uris, city_coords):
    keys = list(city_coords.keys())
    return {uri: city_coords[keys[i % len(keys)]] for i, uri in enumerate(qso_uris)}
