import subprocess


default_components = [
    'Microsoft.VisualStudio.Component.CoreEditor',
    'Microsoft.VisualStudio.Workload.CoreEditor',
    'Microsoft.VisualStudio.Component.Roslyn.Compiler',
    'Microsoft.Component.MSBuild',
    'Microsoft.VisualStudio.Component.TextTemplating',
    'Microsoft.VisualStudio.Component.VC.CoreIde',
    'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
    'Microsoft.VisualStudio.Component.VC.Tools.ARM64',
    'Microsoft.VisualStudio.Component.Windows10SDK.19041',
    'Microsoft.VisualStudio.Component.VC.Redist.14.Latest',
    'Microsoft.VisualStudio.ComponentGroup.NativeDesktop.Core',
    'Microsoft.VisualStudio.Workload.NativeDesktop',
]


def install(components=default_components):
    cmd = [
        'vs_buildtools',
        '--quiet',
        '--wait',
        '--norestart',
        '--nocache',
        '--installPath',
        'C:\\BuildTools',
    ]
    for component in components:
        cmd += ['--add', component]
    res = subprocess.Popen(cmd).wait()
    if res != 3010:
        raise SystemExit(res)


__name__ == '__main__' and install()
