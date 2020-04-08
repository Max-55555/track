import json
import struct
import zlib
import pickle
import sqlite3


class GPEncode(json.JSONEncoder):
    def default(self, o):  # pylint: disable=E0202
        def has_dict(o):
            try:
                o.__dict__
                return True
            except AttributeError:
                return False

        if has_dict(o):
            t = o.__dict__
            for key in t:
                if isinstance(t[key], str):
                    try:
                        t[key].decode('utf8')
                    except:
                        try:
                            t[key] = t[key].decode('MacCyrillic')
                        except:
                            try:
                                t[key] = t[key].encode('hex')
                            except:
                                pass
            return o.__dict__


print('Opening "Gameparams.data".')
data = []
with open('GameParams.data', 'rb') as f:
    byte = f.read(1)
    while byte:
        data.append(byte[0])
        byte = f.read(1)
print('Deflating data.')
deflate = struct.pack('B' * len(data), *data[::-1])
print('Decompressing data.')
decompressed = zlib.decompress(deflate)
pickle_data = pickle.loads(decompressed, encoding='MacCyrillic')
print('Converting to dict.')
raw = json.loads(json.dumps(pickle_data, cls=GPEncode, sort_keys=True, indent=4, separators=(',', ': ')))
print('Getting entity types.')
entity_types = []
for key in raw:
    entity_type = raw[key]['typeinfo']['type']
    if entity_type not in entity_types:
        entity_types.append(entity_type)
print('Filtering entities into db.')
with sqlite3.connect('../../assets/private/GameParams.db') as conn:
    for entity_type in entity_types:
        c = conn.cursor()
        c.execute(f'DROP TABLE IF EXISTS {entity_type}')
        c.execute(f'CREATE TABLE {entity_type}(id TEXT PRIMARY KEY, value TEXT)')
        entities = {}
        for key in raw:
            entity = raw[key]
            if entity_type == entity['typeinfo']['type']:
                c.execute(f'INSERT INTO {entity_type} VALUES (?, ?)', [key, json.dumps(entity)])
