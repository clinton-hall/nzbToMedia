import nzbtomedia
from nzbtomedia.nzbToMediaUtil import extractFiles

# Initialize the config
nzbtomedia.initialize()

inputDirectory = "Z:\complete\movie\lego movie"
inputName = "lego movie"

extractFiles(inputDirectory)