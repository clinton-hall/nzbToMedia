import core


def configure_plex(config):
    core.PLEX_SSL = int(config['Plex']['plex_ssl'])
    core.PLEX_HOST = config['Plex']['plex_host']
    core.PLEX_PORT = config['Plex']['plex_port']
    core.PLEX_TOKEN = config['Plex']['plex_token']
    plex_section = config['Plex']['plex_sections'] or []

    if plex_section:
        if isinstance(plex_section, list):
            plex_section = ','.join(plex_section)  # fix in case this imported as list.
        plex_section = [
            tuple(item.split(','))
            for item in plex_section.split('|')
        ]

    core.PLEX_SECTION = plex_section
