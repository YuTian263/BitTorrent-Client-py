class Bencode: 
    @staticmethod
    def decode(data):
        def decode_next(data, index): 
            if data[index: index + 1] == b'i':
                end = data.find(b'e', index)
                if end == -1:
                    raise ValueError(f"invalid integer at index {index}")
                return int(data[index+1:end]), end + 1
            elif data[index:index+1] == b'l': 
                result = [] 
                index += 1 
                while data[index:index + 1] != b'e': 
                    item, index = decode_next(data, index)
                    result.append(item)
                return result, index + 1 
            elif data[index:index+1] == b'd':
                result = {}
                index += 1 
                while data[index:index+1] != b'e': 
                    key, index = decode_next(data, index)
                    value, index = decode_next(data, index)
                    result[key.decode()] = value
                return result, index + 1 
            elif data[index:index+1].isdigit(): 
                colon = data.find(b':', index)
                if colon == -1:
                    raise ValueError(f"invalid string at index {index}")
                length = int(data[index:colon])
                return data[colon + 1: colon + 1 + length], colon + 1 + length
            else: 
                raise ValueError(f"invalid bencode at index {index}")
        result, _ = decode_next(data, 0)
        return result
    
    @staticmethod
    def encode(obj): 
        if isinstance(obj, int): 
            return f'i{obj}e'.encode() 
        elif isinstance(obj, bytes): 
            return f'{len(obj)}:'.encode() + obj 
        elif isinstance(obj, str): 
            obj_bytes = obj.encode('utf-8')
            return f'{len(obj_bytes)}:'.encode() + obj_bytes
        elif isinstance(obj, list): 
            return b'l' + b''.join(Bencode.encode(item) for item in obj) + b'e'
        elif isinstance(obj, dict): 
            items = [] 
            for k, v in sorted(obj.items()): 
                items.append(Bencode.encode(k))
                items.append(Bencode.encode(v))
            return b'd' + b''.join(items) + b'e'
        else: 
            raise ValueError(f"cannot encode type {type(obj)}")
        

