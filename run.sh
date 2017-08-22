#!/bin/bash

ARCHIVE=./data/
MDB=$ARCHIVE/mdb-`date +%Y%m%d`.json
VOTES=$ARCHIVE/votes-`date +%Y%m%d`.csv

mkdir -p $ARCHIVE

echo Scrape MdBs 
python scraper.py $MDB

echo Scrape Votes
python scraper_votes.py $VOTES
