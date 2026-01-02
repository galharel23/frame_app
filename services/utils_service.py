def get_float(tag_name, tags, default=0.0):
    val = tags.get(tag_name)
    if val:
        try:
            return float(str(val))
        except Exception:
            pass
    return default

def to_float_rounded(val, digits=4):
            try:
                return round(float(val), digits)
            except:
                return 0.0

def to_float(v):
    try:
        return float(str(v).replace("+", "").strip())
    except Exception:
        return None