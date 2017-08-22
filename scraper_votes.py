import sys
import requests
from ast import literal_eval
from bs4 import BeautifulSoup as soup
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


def printProgress(num, onePercent, count, errors):
    print '====> {0:3d} Percent Processed <===='.format(num/onePercent)
    print '{0:4d} profiles scanned:'.format(num) 
    print '   - {0:3d} MdBs found'.format(count)
    print '   - {0:3d} MdB requests failed'.format(errors)
    print ''


def saveData(data, path):
    data.to_csv(path, encoding='utf8')



def scrapeVotes(output):

    data = pd.DataFrame()
    
    print 'Load MdB Profiles'
    jsonProfiles = getJSON(URL_PROFILES)
    profiles = jsonProfiles['profiles']
    
    onePercent = len(profiles)/100
    
    count = 0
    errors = 0
    
    print 'Start Processing'
    for num, profile in enumerate(profiles):
        if num % onePercent == 0 and num != 0:
            printProgress(num, onePercent, count, errors)
            saveData(data, output)
    
        personalData = profile['personal']
        profilePage =  profile['meta']['url']
        htmlPage = getHtml(profilePage)
    
        isInBundestag = htmlPage.find('option', text=BUNDESTAG)
        
        if isInBundestag:
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
    
    saveData(data, output)


if __name__ == '__main__':
    scrapeVotes(sys.argv[1])
