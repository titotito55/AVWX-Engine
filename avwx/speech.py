"""
Contains functions for converting translations into a speech string
Currently only supports METAR
"""

# stdlib
from copy import deepcopy
# module
from avwx import core, translate
from avwx.static import SPOKEN_UNITS, NUMBER_REPL, FRACTIONS
from avwx.structs import MetarData, Units


def numbers(num: str) -> str:
    """
    Returns the spoken version of a number

    Ex: 1.2 -> one point two
    """
    if num in FRACTIONS:
        return FRACTIONS[num]
    return ' '.join([NUMBER_REPL[char] for char in num if char in NUMBER_REPL])


def remove_leading_zeros(num: str) -> str:
    """
    Strips zeros while handling -, M, and empty strings
    """
    if not num:
        return num
    if num.startswith('M'):
        ret = 'M' + num[1:].lstrip('0')
    elif num.startswith('-'):
        ret = '-' + num[1:].lstrip('0')
    else:
        ret = num.lstrip('0')
    return '0' if ret in ('', 'M', '-') else ret


def wind(wdir: str, wspd: str, wgst: str, wvar: [str] = None, unit: str = 'kt') -> str:
    """
    Format wind details into a spoken word string
    """
    unit = SPOKEN_UNITS.get(unit, unit)
    if wdir not in ('000', 'VRB'):
        wdir = numbers(wdir)
    wvar = wvar or []
    for i, val in enumerate(wvar):
        wvar[i] = numbers(val)
    val = translate.wind(wdir, remove_leading_zeros(wspd),
                         remove_leading_zeros(wgst), wvar,
                         unit, cardinals=False)
    return 'Winds ' + (val or 'unknown')


def temperature(header: str, temp: str, unit: str = 'C') -> str:
    """
    Format temperature details into a spoken word string
    """
    if core.is_unknown(temp):
        return header + ' unknown'
    if unit in SPOKEN_UNITS:
        unit = SPOKEN_UNITS[unit]
    temp = numbers(remove_leading_zeros(temp))
    use_s = '' if temp in ('one', 'minus one') else 's'
    return ' '.join((header, temp, 'degree' + use_s, unit))


def visibility(vis: str, unit: str = 'm') -> str:
    """
    Format visibility details into a spoken word string
    """
    if core.is_unknown(vis):
        return 'Visibility unknown'
    elif vis.startswith('M'):
        vis = 'less than ' + numbers(remove_leading_zeros(vis[1:]))
    elif vis.startswith('P'):
        vis = 'greater than ' + numbers(remove_leading_zeros(vis[1:]))
    elif '/' in vis:
        vis = core.unpack_fraction(vis)
        vis = ' and '.join([numbers(remove_leading_zeros(n)) for n in vis.split(' ')])
    else:
        vis = translate.visibility(vis, unit=unit)
        if unit == 'm':
            unit = 'km'
        vis = vis[:vis.find(' (')].lower().replace(unit, '').strip()
        vis = numbers(remove_leading_zeros(vis))
    ret = 'Visibility ' + vis
    if unit in SPOKEN_UNITS:
        ret += ' ' + SPOKEN_UNITS[unit]
        if not (('one half' in vis and ' and ' not in vis) or 'of a' in vis):
            ret += 's'
    else:
        ret += unit
    return ret


def altimeter(alt: str, unit: str = 'inHg') -> str:
    """
    Format altimeter details into a spoken word string
    """
    ret = 'Altimeter '
    if core.is_unknown(alt):
        ret += 'unknown'
    elif unit == 'inHg':
        ret += numbers(alt[:2]) + ' point ' + numbers(alt[2:])
    elif unit == 'hPa':
        ret += numbers(alt)
    return ret


def other(wxcodes: [str]) -> str:
    """
    Format wx codes into a spoken word string
    """
    ret = []
    for item in wxcodes:
        item = translate.wxcode(item)
        if item.startswith('Vicinity'):
            item = item.lstrip('Vicinity ') + ' in the Vicinity'
        ret.append(item)
    return '. '.join(ret)


def metar(wxdata: MetarData, units: Units) -> str:
    """
    Convert wxdata into a string for text-to-speech
    """
    # We make copies here because the functions may change the original values
    _data = deepcopy(wxdata)
    units = deepcopy(units)
    speech = []
    if _data.wind_direction and _data.wind_speed:
        speech.append(wind(_data.wind_direction, _data.wind_speed,
                           _data.wind_gust, _data.wind_variable_direction,
                           units.wind_speed))
    if _data.visibility:
        speech.append(visibility(_data.visibility, units.visibility))
    if _data.temperature:
        speech.append(temperature('Temperature', _data.temperature, units.temperature))
    if _data.dewpoint:
        speech.append(temperature('Dew point', _data.dewpoint, units.temperature))
    if _data.altimeter:
        speech.append(altimeter(_data.altimeter, units.altimeter))
    if _data.other:
        speech.append(other(_data.other))
    speech.append(translate.clouds(_data.clouds,
                                   units.altitude).replace(' - Reported AGL', ''))
    return ('. '.join([l for l in speech if l])).replace(',', '.')
