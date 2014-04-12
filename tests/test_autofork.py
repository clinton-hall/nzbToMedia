import nzbtomedia
from nzbtomedia.versionCheck import CheckVersion
from nzbtomedia import logger

# Initialize the config
nzbtomedia.initialize()

print nzbtomedia.CFG.findsection('tv')
print
print nzbtomedia.CFG.sections
print
sections = ("CouchPotato", "SickBeard", "NzbDrone", "HeadPhones", "Mylar", "Gamez")
print nzbtomedia.CFG[sections].subsections
print nzbtomedia.CFG['SickBeard'].subsections
print
print nzbtomedia.CFG[sections].sections
print nzbtomedia.CFG['SickBeard'].sections
print
print nzbtomedia.CFG['SickBeard','NzbDrone']
print nzbtomedia.CFG['SickBeard']
print
print nzbtomedia.CFG['SickBeard','NzbDrone','CouchPotato'].issubsection('tv', True)
print nzbtomedia.CFG['SickBeard'].issubsection('tv', True)
print
print nzbtomedia.CFG['SickBeard','NzbDrone'].isenabled('tv')
print nzbtomedia.CFG['SickBeard'].isenabled('tv')