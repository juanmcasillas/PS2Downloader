#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ############################################################################
#
# ps2lists.py
# 04/12/2024 (c) Juan M. Casillas <juanm.casillas@gmail.com>
#
# Generate a class to manage the ps2 lists, with some funky filters
# to select the things online.
#
# ############################################################################

import os
import argparse
import requests
import re
import pathlib
import pycountry        # https://pypi.org/project/pycountry/
import pickle
import argparse

class Enviroment:
    REGIONS = [
        'europe',
        'usa',
        'australia',
        'korea',
        'russia'
    ]
    TO_REMOVE = [
    # remove titles
    # if startwith this in lowercase, remove it
        'Dengeki PS2 PlayStation',
        'Jampack Demo Disc Volume',
        'Bonus Demo',
        'Demo Disc',
        'Kiosk Demo',
        'Magazine Ufficiale Playstation 2',
        'Official Playstation 2 Magazine',
        'Official U.S. PlayStation Magazine',
        'Offizielle PlayStation 2 Magazin',
        'PS2 Bonus Demo',
        'Playstation 2 Demo Disc',
        'Playstation 2 Official Demo Disc',
        'Online Start-Up Disc',
        'Official PlayStation 2 Magazine-UK',
        'PlayStation 2 Magazine Ufficiale',
        'DESR-7000-DESR-5000',
        'DVD Player Version',
        'DVD Region X ',
        'EGBrowser',
        'GamePro Action Disc',
        'GameShark 2 - Video Game Enhancer',
        'GameShark',
        'HDD Utility Disc',
        'Linux (for PlayStation 2)',
        'Network Access Disc',
        'Play-Pre 2 Volume',
        'Play-Pre Plus',
        'PlayOnline',
        'PlayStation 2 Cheats',
        'PlayStation 2 Christmas Special 2003 (Europe).zip',
        'PlayStation 2 Demo Disc Version 2.3 (USA).zip',
        'PlayStation BB Navigator ',
        'PlayStation Experience (Europe)',
        'PlayStation Index',
        'PlayStation Seizou Kensa-you',
        'PlayStation Underground',
        'Playable Cheats',
        'Spielbare Cheats Volume',
        'Swap Magic',
        'Ultimate Codes',
        'Utility Disc',
        'Action Replay'
    ]

class Entry:
    def __init__(self, title, url, size):
        
        self.title = title
        self.url = url
        self.size = size

        self.langs = []
        self.region = []
        self.version = []
        self.demo = False
        self.beta = False

        # generate a title without notes in ()
        # so we can do some check. Convert it also to lowercase
        # matches are done to full title.
        # remove also the extension, if found.
        # trailing spaces are maintaned.
        self.basetitle = pathlib.Path(re.sub('\(.+\)','',self.title).lower()).stem
        self.extract_tags(self.title)
        
        try:
            self.size = float(self.size)
        except Exception as e:
            pass
    def extract_tags(self, data):
        self.langs = []
        self.zones = []
        self.version = 0.0
        self.demo = False
        self.beta = False
        self.multidisk = False

        self.rawtags = re.findall('\(.+?\)',self.title)
        for tag in self.rawtags:
            tag = re.sub('[\(\)]','',tag)

            if tag.lower().startswith('disc') or tag.lower().startswith('disk'):
                # skip multi disk entries
                self.multidisk = True
        

            if tag.lower() == "demo":
                self.demo = True
                continue

            if tag.lower() == "beta":
                self.beta = True
                continue


            if tag.find(".") >= 0:
                # version found.
                version = re.sub('[vV]','',tag)
                try:
                    version = float(version)
                except Exception as e:
                    pass
                self.version = version
                continue

            if tag.find(",") >= 0:
                # multi lang found.
                # also, can be multi region
                #
                langs_raw = list(map(lambda x: x.strip(), tag.split(',')))
    
                for item in langs_raw:
                    real_lang = pycountry.languages.get(alpha_2=item.lower())
                    if real_lang:
                        self.langs.append(real_lang.name.lower())

                # check for countries / zones
                for item in langs_raw:
                    real_country = pycountry.countries.get(name=item.lower())
                    if real_country:
                        self.zones.append(real_country.name.lower())

                # maybe they are regions
                for item in langs_raw:
                    if item.lower() in Enviroment.REGIONS and not item.lower() in self.zones:
                        self.zones.append(item.lower())

                continue
                # end the multiline field (langs, zones)

            if tag.lower() in Enviroment.REGIONS:
                self.zones.append(tag.lower())
            else:
                # no more data. check if country (slow)
                try:
                    real_country = pycountry.countries.search_fuzzy(tag.lower())
                except Exception as e:
                    real_country = []

                if len(real_country) > 0:
                    self.zones.append(real_country[0].name.lower())
                

    def __repr__(self):
        s = "title: %s, basetitle: %s, url: %s, size: %3.2f GiB, langs: %s, zones: %s version: %s, isBeta(%s) isDemo(%s) isMultiDisk(%s)" % (
                self.title, self.basetitle, self.url, self.size, 
                self.langs,
                self.zones,
                self.version,
                self.beta,
                self.demo,
                self.multidisk
                )
        return s
            

class PS2Lists:
    def __init__(self, verbose=False, use_serialized=True):
        self.verbose = verbose
        self.urls = {}
        self.urls["myrient"] = "https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%202/"
        self.default_url = self.urls["myrient"]
        self.data = []
        self.sorted = {}
        self.selected = {}

        # to speedup the development (avoid parsing and retrieving the data)
        self.use_serialized = use_serialized

    def abs_url(self, a):
        bar = "" if self.default_url.endswith("/") else "/"
        return "%s%s%s" % (self.default_url, bar, a)

    def get_data(self):

        if self.use_serialized:
            with open('data.pickle', 'rb') as handle:
                self.data = pickle.load(handle)
            with open('sorted.pickle', 'rb') as handle:
                self.sorted = pickle.load(handle)
            return

        r = requests.get(self.default_url)
        
        # scrap it
        # <tr><td class="link"><a href="kill.switch%20%28USA%29.zip" title="kill.switch (USA).zip">kill.switch (USA).zip</a></td><td class="size">2.1 GiB</td><td class="date">03-Mar-2024 15:12</td></tr>
        # reg <tr><td class="link"><a href="()" title="()"</a><td class="size">() GiB*</td></tr>

        regex = '^<tr><td class="link"><a href="(.+?)" title="(.+?)">.*?</a></td><td class="size">(.+) GiB</td>.*</td></tr>$'
        all_data = re.findall(regex, r.text,flags=re.M | re.I)
        for i in all_data:
            if len(i) == 3:
                i = self.do_exclusions(i)
                if i:
                    self.data.append( Entry( i[1],self.abs_url(i[0]), i[2]) )
        
        self.sort_data()
        if not self.use_serialized:
            with open('data.pickle', 'wb') as handle:
                pickle.dump(self.data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            with open('sorted.pickle', 'wb') as handle:
                pickle.dump(self.sorted, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def do_exclusions(self, item):
        url = self.abs_url(item[0]).lower()
        title = item[1].lower()
        for ex in Enviroment.TO_REMOVE:
            if title.startswith(ex.lower()):
                return None
        return item

    def get_size(self):
        sz = 0.0
        for i in self.data:
            sz += i.size
        return sz


    def sort_data(self):
        self.sorted = {}

        "generate dict with the base title, and all of its versions"
        for item in self.data:
            key = item.basetitle.lower()
            if key in self.sorted.keys():
                self.sorted[key].append(item)
            else:
                self.sorted[key] = [item]





    def filter(self):

        # get the files.
        # priorities
        # if only one version, pick it
        # prefer spain over europe,
        # prefer spanish over english
        # if not language, asume EN.

        self.selected  = {}

        for key in self.sorted.keys():
            if len(self.sorted[key]) == 1:
                self.selected[key] = [self.sorted[key][0]]
            else:
                # do the magic here.
                item = self.do_selection(self.sorted[key])
                if item:
                    self.selected[key] = item



    def do_initial_filter(self, items):
        r = []
        
        for i in items:
            if i.demo or i.beta:
                continue
            r.append(i)

        max_version = 0.0
        x = None
        # get the greatest version.
        for i in r:
            if i.version > 0.0 and i.version > max_version:
                max_version = i.version
                x = i
        
        ret = []
        for i in r:
            if i.version <= 0.0:
                ret.append(i)
        if x:
            ret.append(x)
        return ret


    def do_selection_zone(self, items, zone="spain"):
    
        r = []
        for i in items:
            if zone.lower() in i.zones:
                r.append(i)
    
        if len(r) == 0:
            return None
        return r
    
    def do_selection_lang(self, items, lang="spanish"):
    
        r = []
        for i in items:
            if lang.lower() in i.langs:
                r.append(i)

        if len(r) == 0:
            return None
        return r    

    def do_selection(self, items):
        r = None
        litems = self.do_initial_filter(items)
        r = self.do_selection_zone(litems,zone="Spain")
        if r: 
            return r
        r = self.do_selection_lang(litems,lang="spanish")
        if r: 
            return r

        #
        # not found. start doing some magic
        # first, check zones, then langs, then default one.
        #
        for zone in [ "europe", "usa", "australia", "japan" ]:
            r = self.do_selection_zone(litems, zone=zone)
            if r:
                return r
            
        # no zone here.
        for lang in [ "english", "portuguese", "italian", "french", "japanese" ]:
            r = self.do_selection_lang(litems, lang=lang)
            if r:
                return r

        return items


    
    def print_list(self, sorted=False):
        if not sorted:
            for i in self.data:
                print(i)
        else:
            sz = 0.0
            count = 0
            for key in self.sorted.keys():
                checked_title = "[_]"
                checked_file = "[_]"
                if key in self.selected:
                    checked_title = "[YES]"
                if len(self.sorted[key]) == 1:
                    if key in self.selected.keys() and self.sorted[key][0].title == self.selected[key][0].title:
                        checked_file = "[YES]"
                        sz += self.selected[key][0].size
                        count += 1
                    print("%s %s" % (checked_title, self.sorted[key][0]))
                else:
                    print("%s %s" % (checked_title, key))
                    for i in self.sorted[key]:
                        checked_file = "[_]"
                        for selected_item in  self.selected[key]:
                            if key in self.selected.keys() and i.title == selected_item.title:
                                checked_file = "[YES]"
                                sz += selected_item.size
                                count += 1
                        print(" * %s %s" % (checked_file,i))
                    

        print("%d elements, %3.2f Gib" % (count,sz))

    def print_missing(self, sorted=False):

        count = 0
        for key in self.sorted.keys():
            if not key in self.selected:
                if len(self.sorted[key]) == 1:
                    print("%s" % self.sorted[key][0])
                    count += 1
                else:
                    print("%s" % key)
                    for i in self.sorted[key]:
                        print(" * %s" % i)
                        count += 1
                    

        print("%d elements" % count)

                    

        print("%d elements, %3.2f Gib" % (len(self.data),self.get_size()))


    def read_exclusions_from_file(self, fname):
        self.exclusions = []
        with open(fname,"r", encoding="utf-8") as fd:
            for l in fd.readlines():
                self.exclusions.append(l.strip())

    def print_download_list(self, fname):
        sz = 0
        count = 0
        with open(fname,"w", encoding="utf-8") as fd:
            for i in self.selected.values():
                for x in i:
                    if not x.url in self.exclusions:
                        sz += x.size
                        count +=1 
                        fd.write("%s\n" % x.url)

        print("%d elements, %3.2f Gib" % (count,sz))
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Show data about file and processing", action="count", default=0)
    parser.add_argument("-u","--url-remove", help="Urls to remove")
    parser.add_argument("-s","--no_serialize", help="Don't the cache",action="store_false",default=True)
    parser.add_argument("-o","--output", help="Url list to download")

    args = parser.parse_args()


    # use_serialized = False -> stores the config
    # use_serialized = True -> reads from cache
    ps2lists = PS2Lists(verbose=True, use_serialized=args.no_serialize)
    ps2lists.read_exclusions_from_file(args.url_remove)
    ps2lists.get_data()
    ps2lists.filter()
    ps2lists.print_list(sorted=True)
    ps2lists.print_missing()
    ps2lists.print_download_list(args.output)

