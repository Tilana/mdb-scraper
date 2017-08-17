# -*- coding: utf-8 -*-
import sys
import json
from datetime import datetime
from normality import slugify
from hashlib import sha1
import requests
from lxml import etree
import pdb
from bs4 import BeautifulSoup as soup
# from pprint import pprint

URL = "https://www.bundestag.de/"
MDB_INDEX_URL = URL + "xml/mdb/index.xml"
AUSSCHUSS_INDEX_URL = URL + "xml/ausschuesse/index.xml"
AUSSCHUSS_PATTERN = URL + "bundestag/ausschuesse17/%s/index.jsp"
GENDERS = {
    'Weiblich': 'female',
    u'Männlich': 'male'
}


def open_xml(url):
    res = requests.get(url)
    return etree.fromstring(res.content)


def parse_date(text):
    try:
        return datetime.strptime(text, '%d.%m.%Y').date().isoformat()
    except:
        return text


def make_id(group, id):
    id = slugify(unicode(id), sep='-')
    return 'de.bundestag.data:%s:%s' % (group, id)


def make_link_id(lid, rid):
    link = '%s:%s' % (lid, rid)
    return sha1(link).hexdigest()


def make_name(data):
    name = data['academic_prefix'], data['given_name'], data['honorific_prefix'], \
        data['family_name']
    name = ' '.join([n for n in name if len(n.strip())])
    if len(data['location']):
        name += ' (%s)' % data['location']
    return name


def add_to_gremium(node, person_id, role, orgs):
    id = node.get('id') or 'aeltestenrat'
    if id not in orgs:
        orgs[id] = {
            'id': make_id('gremium', id),
            'name': node.findtext('gremiumName'),
            'links': [{
                'note': 'Bundestag.de',
                'url': node.findtext('gremiumURL')
            }],
            'identifiers': [{
                'identifier': node.get('id'),
                'scheme': 'bundestag'
            }],
            'parent_id': orgs['bt']['id'],
            'classification': 'sonstiges'
        }
    membership_data = {
        'id': make_link_id(person_id, orgs[id]['id']),
        'person_id': person_id,
        'organization_id': orgs[id]['id'],
        'role': role,
        'label': '%s, %s' % (role, orgs[id]['name'])
    }
    return membership_data


def scrape_gremium(url, orgs):
    doc = open_xml(url)
    id = doc.findtext('./ausschussId')
    org_data = {
        'id': make_id('gremium', id),
        'name': doc.findtext('./ausschussName'),
        'classification': 'ausschuss',
        'description': doc.findtext('./ausschussAufgabe'),
        'image': doc.findtext('.//ausschussBildURL'),
        # 'image_copyright': doc.findtext('./ausschussCopyright'),
        'links': [
            {
                'note': 'Bundestag.de',
                'url': doc.findtext('.//ausschussSourceURL'),
            },
            {
                'note': 'Bundestag XML',
                'url': url
            }
        ],
        'parent_id': orgs['bt']['id'],
        'identifiers': [{
            'identifier': id,
            'scheme': 'bundestag'
        }]
    }
    if doc.findtext('.//ausschussKontakt'):
        org_data['contact_details'] = [{
            'type': 'address',
            'label': 'Anschrift',
            'value': doc.findtext('.//ausschussKontakt')
        }]
    print 'Scraping org:', org_data['id']
    orgs[id] = org_data


def scrape_index(out_file):
    orgs = {
        'bt': {
            'id': 'de.bundestag.data/bundestag',
            'name': 'Deutscher Bundestag',
            'links': [{
                'note': 'Bundestag.de',
                'url': 'https://www.bundestag.de'
            }],
            'classification': 'legislature'
        }
    }
    #doc = open_xml(AUSSCHUSS_INDEX_URL)
    #for info_url in doc.findall(".//ausschussDetailXML"):
    #    scrape_gremium(info_url.text.strip(), orgs)

    persons = []
    doc = open_xml(MDB_INDEX_URL)
    c = 0
    for info_url in doc.findall(".//mdbInfoXMLURL"):
        person = scrape_mdb(info_url.text, orgs)
        # pprint(person)
        persons.append(person)
        c += 1
        if c==15:
            pdb.set_trace()

    store_json(out_file, persons, orgs.values())


def store_json(out_file, persons, organizations):
    with open(out_file, 'w') as fh:
        json.dump({
            'organizations': organizations,
            'persons': persons
        }, fh, indent=2)


def process_interests(interests):
    html = soup(interests)
    interestList = html.find_all('ul', class_='voa_list bt-liste')
    return [interest.text for interest in interestList]

def extract_salary(interests):
    #TODO: separate diffente salary classes
    salaries = [position for position in interest if position.find('Stufe')!=-1]
    salaries = [salary.replace(u'\xa0', ' ') for salary in salaries]


def scrape_mdb(url, orgs):
    doc = open_xml(url)
    if not doc.findtext('.//mdbID'):
        print 'FAILED', url
        return
    id = int(doc.findtext('.//mdbID'))
    interests =  doc.findtext('.//mdbVeroeffentlichungspflichtigeAngaben')
    person_data = {
        'id': make_id('mdb', id),
        'given_name': doc.findtext('.//mdbVorname'),
        'family_name': doc.findtext('.//mdbZuname'),
        'honorific_prefix': doc.findtext('.//mdbAdelstitel'),
        'academic_prefix': doc.findtext('.//mdbAkademischerTitel'),
        'location': doc.findtext('.//mdbOrtszusatz'),
        'birth_date': parse_date(doc.findtext('.//mdbGeburtsdatum')),
        'religion': doc.findtext('.//mdbReligionKonfession'),
        'profession': doc.findtext('.//mdbBeruf'),
        'profession_group': doc.find('.//mdbBeruf').get('berufsfeld'),
        'graduate_education': doc.findtext('.//mdbHochschulbildung'),
        'gender': GENDERS[doc.findtext('.//mdbGeschlecht')],
        'children': doc.findtext('.//mdbAnzahlKinder'),
        'state': doc.findtext('.//mdbLand'),
        'trivia': doc.findtext('.//mdbWissenswertes'),
        'interests': interests,  
        'procInterests': process_interests(interests),
        'marital_status': doc.findtext('.//mdbFamilienstand'),
        'summary': doc.findtext('.//mdbBiografischeInformationen'),
        'image': doc.findtext('.//mdbFotoURL'),
        'image_copyright': doc.findtext('.//mdbFotoCopyright'),
        'links': [
            {
                'note': 'Bundestag bio page',
                'url': doc.findtext('.//mdbBioURL'),
            },
            {
                'note': 'Bundestag XML data',
                'url': url
            },
            {
                'note': 'Speeches in plenary',
                'url': doc.findtext('.//mdbRedenVorPlenumURL')
            },
            {
                'note': 'Speeches in plenary (RSS)',
                'url': doc.findtext('.//mdbRedenVorPlenumRSS')
            }
        ],
        'identifiers': [{
            'identifier': unicode(id),
            'scheme': 'bundestag'
        }],
        'contact_details': [
            {
                'type': 'phone',
                'label': 'Telefon',
                'value': doc.findtext('.//mdbTelefon')
            }
        ],
        'memberships': []
    }

    if doc.findtext('.//mdbHomepageURL'):
        person_data['links'].append({
            'note': 'Homepage',
            'url': doc.findtext('.//mdbHomepageURL')
        })

    for website in doc.findall('.//mdbSonstigeWebsite'):
        person_data['links'].append({
            'note': website.findtext('./mdbSonstigeWebsiteTitel'),
            'url': website.findtext('./mdbSonstigeWebsiteURL')
        })

    person_data['name'] = make_name(person_data)
    print 'Scraping person:', person_data['id']

    for key, value in person_data.items():
        if isinstance(value, basestring) and not len(value.strip()):
            del person_data[key]

    #
    # Membership role for the party.
    #
    party = doc.findtext('.//mdbPartei')
    if party not in orgs:
        orgs[party] = {
            'id': make_id('partei', party),
            'name': party,
            'classification': 'party'
        }

    party_membership = {
        'person_id': person_data['id'],
        'organization_id': orgs[party]['id'],
        'id': make_link_id(person_data['id'], orgs[party]['id']),
        'role': 'Mitglied',
        'label': u'Mitglied %s' % party
    }
    person_data['memberships'].append(party_membership)

    #
    # Membership role for the parliament.
    #
    mdb_membership = {
        'person_id': person_data['id'],
        'organization_id': orgs['bt']['id'],
        'id': make_link_id(person_data['id'], orgs['bt']['id']),
        'role': 'Mitglied des Bundestages',
        'status': doc.find('.//mdbID').get('status'),
        'mandate_type': doc.findtext('.//mdbGewaehlt'),
        'faction': doc.findtext('.//mdbFraktion'),
        'on_behalf_of_id': orgs[party]['id'],
        'legislative_period_id': make_id('wahlperiode', 18)
    }

    wk = doc.findtext('.//mdbWahlkreisNummer')
    if wk:
        mdb_membership['area'] = {
            'name': doc.findtext('.//mdbWahlkreisName'),
            'id': make_id('wahlkreis', wk),
            'constituency': wk,
            'url': doc.findtext('.//mdbWahlkreisURL'),
            'classification': 'wahlkreis',
            'parent_id': make_id('land', doc.findtext('.//mdbLand'))
        }
    else:
        mdb_membership['area'] = {
            'name': doc.findtext('.//mdbLand'),
            'id': make_id('land', doc.findtext('.//mdbLand')),
            'classification': 'bundesland'
        }

    end = doc.findtext('.//mdbAustrittsdatum')
    if end:
        mdb_membership['end_date'] = parse_date(end)

    if doc.findtext('.//mdbBundestagsvizepraesident'):
        mdb_membership['role'] = u'Bundestagsvizepräsident'
    if doc.findtext('.//mdbBundestagspraesident'):
        mdb_membership['role'] = u'Bundestagspräsident'

    mdb_membership['label'] = '%s, %s' % (person_data['name'],
                                          mdb_membership['role'])
    person_data['memberships'].append(mdb_membership)

    #
    # Memberships in committees.
    #
    for role_el in doc.find('.//mdbMitgliedschaften'):
        role = role_el.get('title')
        for cmte_el in role_el:
            mem = add_to_gremium(cmte_el, person_data['id'], role, orgs)
            person_data['memberships'].append(mem)

    return person_data


if __name__ == '__main__':
    #scrape_index(sys.argv[1])
    scrape_index('test')

