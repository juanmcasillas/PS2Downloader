import argparse
import sys
import os
import re

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Show data about file and processing", action="count", default=0)
    parser.add_argument("-i", "--html", help="generate html index", action="store_true", default=False)
    parser.add_argument("all", help="All the files")
    parser.add_argument("downloaded", help="Files already donwloaded")
    parser.add_argument("index", help="index.html file (with names)")


    args = parser.parse_args()

    downloaded = []
    all = []
    result = []
    index = []
    result_index = []

    with open(args.downloaded) as fd:
        for l in fd.readlines():
            downloaded.append(l.strip())
    
    with open(args.all) as fd:
        for l in fd.readlines():
            all.append(l.strip())

    if args.html:
        with open(args.index) as fd:
            for l in fd.readlines():
                
                if l.startswith('<tr><td class="link"><a href="https://myrient.erista.me/files/Redump/Sony'):
                    l = l.strip()
                    l = l.replace('<tr><td class="link">','')
                    l = re.sub('</td><td class="size">.*','',l)
                    index.append(l)

      
    # check for files in downloaded not in all
    # for item in downloaded:
    #     if item not in all:
    #         result.append(item)

    # check for files in all not downloaded
    for item in all:
        if item not in downloaded:
            result.append(item)

    # generate index
    if args.html:
        for item in result:
            for x in index:
                if x.find(item) > -1:
                    result_index.append(x)

    if not args.html:
        print("\n".join(result))
    else:
        print("</br>\n".join(result_index))
