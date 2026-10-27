"""Player name aliases: nickname -> 1986 card name."""
ALIASES = {
    'Goose Gossage': 'Rich Gossage',
    # Add more as discovered
}

def resolve(name):
    return ALIASES.get(name, name)
