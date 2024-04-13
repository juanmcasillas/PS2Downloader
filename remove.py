import argparse
import sys
import os
import re

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Show data about file and processing", action="count", default=0)
    parser.add_argument("all", help="All the files")
    parser.add_argument("downloaded", help="Files already donwloaded")
    

    args = parser.parse_args()

    downloaded = []
    all = []
    result =[]

    with open(args.all,"r", encoding="utf-16") as fd:
        for l in fd.readlines():
            all.append(l.strip())

    with open(args.downloaded,"r", encoding="utf-8") as fd:
        for l in fd.readlines():
            downloaded.append(l.strip())
    
    for x in all:
        f = False
        for item in downloaded:
            if x.find(item) >= 0:
                f = True
        if not f:
            result.append(x)
    print("\n".join(result))
