"""Career spans for 24-pitcher stress test (for era normalization)."""
# Format: name -> (start_year, end_year)
CAREER_SPANS = {
    'Pedro Martinez': (1992, 2009),
    'Randy Johnson': (1988, 2009),
    'Greg Maddux': (1986, 2008),
    'Nolan Ryan': (1966, 1993),
    'Walter Johnson': (1907, 1927),
    'Christy Mathewson': (1900, 1916),
    'Lefty Grove': (1925, 1941),
    'Sandy Koufax': (1955, 1966),
    'Bob Gibson': (1959, 1975),
    'Roger Clemens': (1984, 2007),
    'Cy Young': (1890, 1911),
    'Pete Alexander': (1911, 1930),
    'Mariano Rivera': (1995, 2013),
    'Billy Wagner': (1995, 2010),
    'Dennis Eckersley': (1975, 1998),
    'Rich Gossage': (1972, 1994),
    'Trevor Hoffman': (1993, 2010),
    'Rollie Fingers': (1968, 1985),
    'Bruce Sutter': (1976, 1988),
    'Hoyt Wilhelm': (1952, 1972),
    'Jonathan Papelbon': (2005, 2016),
    'Kazuhiro Sasaki': (2000, 2003),
    'Dan Quisenberry': (1979, 1990),
    'Kent Tekulve': (1974, 1989),
}

def get_mid_year(name):
    if name in CAREER_SPANS:
        s, e = CAREER_SPANS[name]
        return (s + e) // 2
    return 2000  # fallback
