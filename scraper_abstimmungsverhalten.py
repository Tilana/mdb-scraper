import requests
from ast import literal_eval
from bs4 import BeautifulSoup as soup
import json
import pdb
import pandas as pd

URL = 'https://www.abgeordnetenwatch.de'
URL_PROFILES = URL + '/api/parliament/bundestag/profiles.json'
BUNDESTAG = 'Bundestag 2013-2017'


def getJSON(url):
    return requests.get(url).json()

def getHtml(url):
    res = requests.get(url)
    return soup(res.content)

def setPersonalData(db, ind, personalData):
    keys = ['first_name', 'last_name', 'gender', 'profession', 'birthyear', 'education']
    for key in keys:
        db.loc[ind, key] = personalData[key]
    db.loc[ind, 'county'] = personalData['location']['county']
    return db


data = pd.DataFrame()

print 'Load Data'
jsonProfiles = getJSON(URL_PROFILES)
profiles = jsonProfiles['profiles']

count = 0
errors = 0

for profile in profiles:
    personalData = profile['personal']
    metaData = profile['meta']
    print personalData['first_name'] + ' ' + personalData['last_name']
    profilePage = metaData['url']
    htmlPage = getHtml(profilePage)

    isInBundestag = htmlPage.find('option', text=BUNDESTAG)
    
    if isInBundestag:
        print 'Bundestagsabgeordnete(r)'
        bundestagLink = isInBundestag['value']

        setPersonalData(data, count, personalData)
        data.loc[count, 'party'] = profile['party']

        bundestagProfile = getHtml(URL + bundestagLink)

        try:
            excerpt = bundestagProfile.findAll('script', type='text/javascript')[8]
            splits = excerpt.text.split('},')
            for ind, abstimmung in enumerate(splits):
                if ind==0:
                    abstimmung = literal_eval('{' + abstimmung.split('{')[1] + '}')
                elif ind==len(splits)-1:
                    abstimmung = literal_eval(abstimmung.split(']')[0])
                else:
                    abstimmung = literal_eval(abstimmung + '}')
                data.loc[count, abstimmung['title']] = abstimmung['vote']
            count += 1
        except:
            'Error: Processing failed'
            errors += 1

    print ''


print count
pdb.set_trace()

print 'End'

