import requests, os, time
from bs4 import BeautifulSoup

# Global Lists
googleLinks = []
mediafireLinks = []
androidfilehostLinks = []
other = []

def googleDL(vendor):
    # Mostly stable but there are times that for whatever reason the file does not redirect and wget ends up downloading the html web-page instead of the zip file
    # Would want to look into it to increase stability, but seems to be good for now
    print("Downloading GoogleDrive Firmware for " + vendor)
    for drive in googleLinks:
        FILEID = drive.split('/')[-2]
        gURL = f"https://drive.google.com/u/0/uc?id={FILEID}&export=download"
        gpage = requests.get(gURL)
        gsoup = BeautifulSoup(gpage.content, "html.parser")
        gresults = gsoup.find(id="uc-text")
        gfiltered = gresults.find_all("span", class_="uc-name-size")
        FILENAME = str(gfiltered).split('<')[-3].split('>')[1]
        wgetLoadCookies = "wget --load-cookies /tmp/cookies.txt"
        weirdStuff = f"https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id={FILEID}' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\\1\\n/p')&id={FILEID}"
        fileSave = f"-O {FILENAME}"
        cleanCookiesDirSave = f"&& rm -rf /tmp/cookies.txt && mv {FILENAME} {vendor}/"
        # Sauce: https://bcrf.biochem.wisc.edu/2021/02/05/download-google-drive-files-using-wget/
        os.system('%s "%s" %s %s' % (wgetLoadCookies, weirdStuff, fileSave, cleanCookiesDirSave))

def mediafireDL(vendor):
    # Original file name is necessary so using spaghetti code
    print("Downloading MediaFire Firmware for " + vendor)
    for file in mediafireLinks:
        dpage = requests.get(file)
        dsoup = BeautifulSoup(dpage.content, "html.parser")
        dresults = dsoup.find(id="downloadButton")
        dlink = str(dresults).split('\"')[5]
        #print(dlink) # Here for debugging purposes
        os.system('%s %s "%s"' % ('wget -P', vendor, dlink))

def download(vendor):
    if len(mediafireLinks) != 0:
        mediafireDL(vendor)
    if len(googleLinks) != 0:
        googleDL(vendor)
    if len(androidfilehostLinks) != 0:
    #    afhDL()
        print("No support for AndroidFileHost yet")

def cleanupLists():
    googleLinks.clear()
    mediafireLinks.clear()
    androidfilehostLinks.clear()
    other.clear()

def printLists():
    print("---MediaFire---")
    print(mediafireLinks)
    print("---Google---")
    print(googleLinks)
    print("---AndroidFileHost---")
    print(androidfilehostLinks)
    print("---Other---")
    print(other)

def getFinalLinks(waitingLinks):
    for w in waitingLinks:
        wpage = requests.get(w)
        wsoup = BeautifulSoup(wpage.content, "html.parser")
        wresults = wsoup.find(class_="site-inner")
        wfiltered = wresults.find_all("a", class_="btn btn-success fp-download-link")
        
        #print("Currently on " + str(wfiltered)) # Here for debugging purposes
        if len(wfiltered) == 0:
            continue
        
        wlink = str(wfiltered).split()[5].split('\'')[1]
        if "mediafire" in wlink:
            mediafireLinks.append(wlink)
        elif "drive.google" in wlink:
            googleLinks.append(wlink)
        elif "androidfilehost" in wlink:
            androidfilehostLinks.append(wlink)
        else:
            other.append(wlink)

def versionExtractor(fileName):
    if fileName.endswith(".zip"):
        fileName = fileName[:-4]
    findNum = fileName.split('_')
    findLargestVersion = False
    tmpCounter = 0
    intSearch = []
    finalVersion = ''
    
    # Finds for part of filename that goes x.x.x
    for part in findNum:
        if '.' in str(part) and part[0].isnumeric():
            findLargestVersion = False
            finalVersion = part
        elif part.isnumeric():
            findLargestVersion = True
            tmpCounter = tmpCounter + 1
            intSearch.append(part)
    
    # At times the Android version is just a single digit
    if tmpCounter > 1 and findLargestVersion:
        for i in intSearch:
            if int(i) > 11 or int(i) < 7:
                continue
            else:
                return i

    return finalVersion

def getWaitingLinks(filteredLinks):
    # Get the link for the 20 second wait page, aka each unique firmware link
    waitingLinks = []
    for l in filteredLinks:
        lpage = requests.get(l)
        lsoup = BeautifulSoup(lpage.content, "html.parser")
        lresults = lsoup.find(id="genesis-content")
        lfiltered = lresults.find_all("div", class_="fp-download-section")

        counter = 0
        getLinkIndicator = []
        for c in lfiltered[0].find_all('p'):
            # Only works on pages that have the Android OS Version available
            # Usually when the Android OS Version is not there it is old but this needs fixing
            if "Android OS Version" in str(c):
                counter = counter + 1
                #print("Currently at ", c) # Here for debugging purposes
                try:
                    # The OS Version is NA
                    if "NA" in str(c) or "N/A" in str(c):
                        continue
                    elif int(str(c).split(':')[1].strip()[0]) >= 7:
                        #print(c) # Print the Android OS Version it found for debugging purposes
                        getLinkIndicator.append(counter)
                except ValueError:
                    # The OS Version string is malformatted
                    if (str(c).split(':')[1].strip()) == '</p>':
                        continue
                    elif int(str(c).split('>')[3].split('.')[0]) >= 7:
                        #print(c) # Print the Android OS Version it found for debugging purposes
                        getLinkIndicator.append(counter)
            # The Android OS Version is not available so we infer it from the file name
            elif "File Name" in str(c):
                counter = counter + 1
                version = versionExtractor(str(c).split()[2].split('<')[0])
                if len(version.strip()) == 0:
                    continue
                elif int(version.split('.')[0]) >= 7:
                    getLinkIndicator.append(counter)

        tempCounter = 0
        for d in lfiltered[0].find_all('a', href=True):
            tempCounter = tempCounter + 1
            if tempCounter in getLinkIndicator:
                # Sometimes there are links to flashers instead of firmware
                # Removing the links we don't want Note: This means that just
                # because you saw Android 7.0 was detected, doesn't mean it will
                # be downloaded
                if "https://firmwarepanda.com" not in d['href']:
                    #print("https://firmwarepanda.com" + d['href']) # Here for debugging purposes
                    waitingLinks.append("https://firmwarepanda.com" + d['href'])
    return waitingLinks

# Remove any redundant links or unnecessary links from list
def cleanupURLS(vendor, linksList):
    filteredLinks = []
    for i in linksList:
        tmp1 = "https://firmwarepanda.com/"
        tmp2 = "https://firmwarepanda.com/device/" + vendor + "/"
        if i == tmp1 or "/page/" in i or i == tmp2:
            continue
        if i not in filteredLinks:
            filteredLinks.append(i)
    return filteredLinks

# Traverese every page, starting from the last page going back
def traversePages(pages, pageURL, linksList):
    for n in range(pages, 1, -1):
        npage = requests.get(pageURL + str(n) + '/')
        nsoup = BeautifulSoup(npage.content, "html.parser")
        nresults = nsoup.find(id="genesis-content")
        for a in nresults.find_all('a', href=True):
            linksList.append(a['href'])
    return linksList

def getPages(linksList, traverse):
    tmp = []
    for i in linksList:
        if "page/" in i:
            tmp.append(i.split('/')[-2])
    try:
        pages = int(max(tmp))
    except ValueError:
        # It is either one page or the vendor does not exist
        traverse = False
        return traverse
    return pages

def start(vendor):
    print("Starting extraction for " + vendor)
    baseURL = "https://firmwarepanda.com/device/"
    linksList = []
    URL = baseURL + str(vendor) + '/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find(id="genesis-content")
    pageURL = URL + "page/"

    # Get all the a href that are found on the first page
    for a in results.find_all('a', href=True):
        linksList.append(a['href'])

    traverse = True
    print("Getting Pages")
    pages = getPages(linksList, traverse)
    if pages:
        print("Traversing Pages")
        linksList = traversePages(pages, pageURL, linksList)
    print("Cleaning up URLS")
    filteredLinks = cleanupURLS(vendor, linksList)
    print("Obtaining Panda Links")
    waitingLinks = getWaitingLinks(filteredLinks)
    print("Getting Final List")
    getFinalLinks(waitingLinks)

def main():
    s = time.time()
    vendors = list(map(str,input("Vendors: ").strip().split()))
    for vendor in vendors:
        os.system(f"mkdir {vendor}") # If you already have the directory it'll just fail so no worries
        start(vendor)
        print("---BAG SECURED---")
        printLists()
        #download(vendor) # Can comment out for testing purposes
        cleanupLists()
        print("---" + vendor + " Done---")
    e = time.time()
    print(f"Runtime of the program is {e - s}")

main()

"""
STATUS:
The scraper extracts all the links that are on FirmwarePanda for any given vendor
It will specifically look for links to images that are equal to or greater than Android 7
It currently is capable of downloading MediaFire and GoogleDrive links
It can also infer the Android OS Version based off the file name if the OS Version is not provided
Preliminary tests conducted verifying all necessary URLs are extracted and downloads are successful

TODOs:
x Get Android File Host working
x Remove OTA (I think should just be done later)
x Leave running on Frank
x Start trying to get it to work on FirmwareFile.com
"""
