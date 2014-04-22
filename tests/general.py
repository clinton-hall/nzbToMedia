import nzbtomedia
from nzbtomedia.nzbToMediaUtil import extractFiles, append_downloadID

# Initialize the config
nzbtomedia.initialize()

inputDirectory = "Z:\complete\tv\Game.of.Thrones.S04E03.HDTV.XviD-RARBG"
inputName = "Game of Thrones - S04E03 - Breaker of Chains"
inputHash = 'wdfc8fdn09w1wn908ede0820d8berd434213'

outputDestination = append_downloadID(inputDirectory, inputHash)
print outputDestination