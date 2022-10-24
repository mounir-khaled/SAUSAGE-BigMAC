import requests, os, time, subprocess
from bs4 import BeautifulSoup

# Global Lists
googleLinks = []
mediafireLinks = []
androidfilehostLinks = []
sharepointLinks = []
adhLinks = []
other = []

def adhDL(vendor):
    # Probably just Android Data Host
    for dl in other:
        opage = requests.get(dl)
        osoup = BeautifulSoup(opage.content, "html.parser")
        oresults = osoup.find(class_="download2")
        olink = str(oresults).split('"')[3]
        os.system('%s %s "%s"' % ('wget -P', vendor, olink))

def sharepointDL(vendor):
    for sp in sharepointLinks:
        # SharePoint forbids downloads, need some workaround
        #proc = subprocess.Popen(["curl -Ls -o /dev/null -w %{url_effective}", sp], stdout=subprocess.PIPE, shell=True)
        #(out, err) = proc.communicate()
        term = "curl -Ls -o /dev/null -w %{url_effective} " + sp
        out = os.popen(term).read()
        termOut = str(out)
        #print(termOut)
        #termOut = os.system("%s %s" % ("curl -Ls -o /dev/null -w %{url_effective}", sp))
        lnk = termOut.split("onedrive.aspx?id=")
        sdownload = lnk[0]+"download.aspx?SourceUrl="+lnk[1]
        print(sp)
        os.system('%s %s "%s"' % ('wget -P', vendor, sdownload))

def googleDL(vendor):
    # Mostly stable but there are times that for whatever reason the file does not redirect and wget ends up downloading the html web-page instead of the zip file
    # Would want to look into it to increase stability, but seems to be good for now
    print("Downloading GoogleDrive Firmware for " + vendor)
    for drive in googleLinks:
        FILEID = drive.split('/')[-2]
        gURL = f"https://drive.google.com/u/0/uc?id={FILEID}&export=download"
        gpage = requests.get(gURL)
        gsoup = BeautifulSoup(gpage.content, "html.parser")
        try:
            gresults = gsoup.find(id="uc-text")
            gfiltered = gresults.find_all("span", class_="uc-name-size")
        except AttributeError:
            print("This page is empty")
            continue
        try:
            FILENAME = str(gfiltered).split('<')[-3].split('>')[1]
        except IndexError:
            print("Drive link is blocked")
            continue
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
        #afhDL()
        print("No support for AndroidFileHost yet")
    if len(sharepointLinks) != 0:
        sharepointDL(vendor)
    if len(adhLinks) != 0:
        adhDL(vendor)
    if len(other) != 0:
        other(vendor)

def cleanupLists():
    googleLinks.clear()
    mediafireLinks.clear()
    androidfilehostLinks.clear()
    sharepointLinks.clear()
    adhLinks.clear()
    other.clear()

def printLists():
    print("---MediaFire---")
    print(mediafireLinks)
    print("---Google---")
    print(googleLinks)
    print("---AndroidFileHost---")
    print(androidfilehostLinks)
    print("---SharePoint---")
    print(sharepointLinks)
    print("---AndroidDataHost---")
    print(adhLinks)
    print("---Other---")
    print(other)

def versionExtractor(fileName):
    if fileName.endswith(".zip"):
        fileName = fileName[:-4]
    if fileName.endswith(".zip/file"):
        fileName = fileName[:-9]
    findNum = fileName.split('_')
    findLargestVersion = False
    tmpCounter = 0
    intSearch = []
    finalVersion = ''
    
    # Finds for part of filename that goes x.x.x
    for part in findNum:
        # Kind of flaw since it looks at the first instance
        # and not each instance of a x.x.x number but it works for now
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

def getFinalLinks(filteredLinks):
    # Get the link for the 20 second wait page, aka each unique firmware link
    for l in filteredLinks:
        lpage = requests.get(l)
        lsoup = BeautifulSoup(lpage.content, "html.parser")
        lresults = lsoup.find(id="pagelist")
        try:
            lfiltered = lresults.find_all("blockquote")
        except:
            continue

        getLinkIndicator = []
        get = False
        for c in lfiltered[0].find_all('p'):
            # The Android OS Version is not available so we infer it from the file name
            if "File Name" in str(c) and get == False:
                version = versionExtractor(str(c).split()[2].split('<')[0])
                if len(version.strip()) == 0:
                    continue
                elif int(version.split('.')[0]) > 7:
                    #print(f"Version is {version} so we will download it") # Here for debugging purposes
                    get = True
                    continue
            
            if get:
                if "Mirror 1 (GDrive)" in str(c) and "Mirror 2 (Mediafire)" in str(c):
                    googleLinks.append(str(c).split('"')[3])
                    mediafireLinks.append(str(c).split('"')[11])
                    get = False
                elif "Mirror 1 (GDrive)" in str(c) and "Mirror 2 (AFH)" in str(c):
                    googleLinks.append(str(c).split('"')[3])
                    androidfilehostLinks.append(str(c).split('"')[11])
                    get = False
                elif "Mirror 1 (GDrive)" in str(c) and "Mirror 2 (GDrive)" in str(c):
                    googleLinks.append(str(c).split('"')[3])
                    googleLinks.append(str(c).split('"')[11])
                    get = False
                elif "Mirror 1 (OneDrive)" in str(c) and "Mirror 2 (GDrive)" in str(c):
                    # <p><a class="zip-one" href="https://firmwarefile-my.sharepoint.com/:u:/p/support/ERE6FHV2gV1Eh886RpBHphUBFliJ8a-_6RI9ifPOYPQZtg?e=oviYSI" rel="noopener noreferrer" target="_blank">Mirror 1 (OneDrive)</a><a class="zip-two" href="https://drive.google.com/file/d/1RCD-wB1v1QU3OcJM5xz5Be7hu_-g3XyI/view" rel="noopener noreferrer" target="_blank">Mirror 2 (GDrive)</a></p>
                    sharepointLinks.append(str(c).split('"')[3])
                    googleLinks.append(str(c).split('"')[11])
                    get = False
                elif "Mirror 1 (Mediafire)" in str(c) and "Mirror 2 (AFH)" in str(c):
                    # <p><a class="zip-one" href="https://www.mediafire.com/file/jv2zxoot3xlp5jz/Xiaomi_Redmi_Note_5_Pro_8.7.12_20180712.0000.00_Global_8.1_XFT.zip/file" rel="noopener noreferrer" target="_blank">Mirror 1 (Mediafire)</a><a class="zip-two" href="https://androidfilehost.com/?fid=14943124697586377114" rel="noopener noreferrer" target="_blank">Mirror 2 (AFH)</a></p>
                    mediafireLinks.append(str(c).split('"')[3])
                    androidfilehostLinks.append(str(c).split('"')[11])
                    get = False
                elif "gappug" in str(c):
                    site = str(c).split('"')[3]
                    if "mediafire.com" in site:
                        #print("MediaFire Link: ", site)
                        mediafireLinks.append(site)
                    elif "drive.google.com":
                        #print("Google Link: ", site)
                        googleLinks.append(site)
                    elif "androidfilehost.com" in site:
                        #print("AndroidFileHost Link:" , site)
                        androidfilehostLinks.append(site)
                    elif "androiddatahost.com" in site:
                        adhLinks.append(site)
                    else:
                        print("Uh Oh, no support for this yet, gappug")
                        print(str(c))
                    get = False
                else:
                    print("Uh Oh, no support for this yet, Two Mirros")
                    print(str(c))
                    get = False

# Remove any redundant links or unnecessary links from list
def cleanupURLS(vendor, linksList):
    filteredLinks = []
    for i in linksList:
        tmp1 = "https://firmwarefile.com"
        tmp2 = "https://firmwarefile.com/category/" + vendor
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
        nresults = nsoup.find(class_="frontleft")
        for a in nresults.find_all('a', href=True):
            linksList.append(a['href'])
    return linksList

def getPages(linksList, traverse):
    tmp = []
    for i in linksList:
        if "page/" in i:
            tmp.append(int(i.split('/')[-1]))
    try:
        pages = int(max(tmp))
    except ValueError:
        # It is either one page or the vendor does not exist
        traverse = False
        return traverse
    return pages

def start(vendor):
    print("Starting extraction for " + vendor)
    baseURL = "https://firmwarefile.com/category/"
    linksList = []
    URL = baseURL + str(vendor) + '/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find(class_="frontleft")
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
    print("Obtaining Final Links")
    getFinalLinks(filteredLinks)

def main():
    s = time.time()
    vendors = list(map(str,input("Vendors: ").strip().split()))
    #vendors = ["huawei"]
    for vendor in vendors:
        os.system(f"mkdir {vendor}") # If you already have the directory it'll just fail so no worries
        start(vendor)
        print("---BAG SECURED---")
        printLists()
        download(vendor) # Can comment out for testing purposes
        cleanupLists()
        print("---" + vendor + " Done---")
    e = time.time()
    print(f"Runtime of the program is {e - s}")

main()

"""
STATUS:
Scrapes all the links for a desired vendor
It gets both the mirror links and tries both, you can remove duplicates with Linux commands
Reasoning is the Google drive links are scraped often so they can return errors
Works and handles everything you can see so far on firmwarefile but measures in place in case new issue arises
Downloads MediaFire, GoogleDrive, SharePoint, and AndroidDataHost
*OTA and duplicates should be removed with bash commands since it's quick and easy

TODOs:
x Get Android File Host working
"""