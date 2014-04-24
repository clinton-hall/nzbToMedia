import os
import datetime
import nzbtomedia
from nzbtomedia import nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import get_downloadInfo

# Initialize the config
nzbtomedia.initialize()

inputDirectory = 'Z:/complete/music/B.O.A.T.S. II_ Me Time [2013]'
outputDestination = 'Z:\\test\\music\\B.O.A.T.S. II_ Me Time [2013]'
outputDestinationMaster = outputDestination  # Save the original, so we can change this within the loop below, and reset afterwards.

now = datetime.datetime.now()
for dirpath, dirnames, filenames in os.walk(inputDirectory):
    for file in filenames:

        filePath = os.path.join(dirpath, file)
        fileName, fileExtension = os.path.splitext(file)
        newDir = dirpath  # find the full path
        newDir = newDir.replace(inputDirectory, "")  #find the extra-depth directory
        if len(newDir) > 0 and newDir[0] == "/":
            newDir = newDir[1:]  # remove leading "/" to enable join to work.
        outputDestination = os.path.join(outputDestinationMaster, newDir)  # join this extra directory to output.

        targetDirectory = os.path.join(outputDestination, file)

outputDestination = outputDestinationMaster
nzbtomedia.flatten(outputDestination)