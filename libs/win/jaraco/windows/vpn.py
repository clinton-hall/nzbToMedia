import os
from path import Path


def install_pptp(name, param_lines):
    """ """
    # or consider using the API:
    # http://msdn.microsoft.com/en-us/library/aa446739%28v=VS.85%29.aspx
    pbk_path = (
        Path(os.environ['PROGRAMDATA'])
        / 'Microsoft'
        / 'Network'
        / 'Connections'
        / 'pbk'
        / 'rasphone.pbk'
    )
    pbk_path.dirname().makedirs_p()
    with open(pbk_path, 'a') as pbk:
        pbk.write('[{name}]\n'.format(name=name))
        pbk.writelines(param_lines)
        pbk.write('\n')
