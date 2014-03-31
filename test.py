import copy

from autoProcess.autoSickBeardFork import autoFork

fork, params = autoFork()
print fork

failed = True
for param in copy.copy(params):
    if param is "failed":
        params["failed"] = failed

    if param is "dirName":
        params["dirName"] = "dirName"

    if param is "dir":
        params["dir"] = "dirName"

    if param is "process_method":
        del param

params['nzbName'] = "test"

print params