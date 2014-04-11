from nzbtomedia.nzbToMediaConfig import config

print config().findsection('tv').isenabled()
print
print config().sections
print
sections = ("CouchPotato", "SickBeard", "NzbDrone", "HeadPhones", "Mylar", "Gamez")
print config()[sections].subsections
print config()['SickBeard'].subsections
print
print config()[sections].sections
print config()['SickBeard'].sections
print
print config()['SickBeard','NzbDrone']
print config()['SickBeard']
print
print config()['SickBeard','NzbDrone','CouchPotato'].issubsection('tv', True)
print config()['SickBeard'].issubsection('tv', True)
print
print config()['SickBeard','NzbDrone'].isenabled('tv')
print config()['SickBeard'].isenabled('tv')