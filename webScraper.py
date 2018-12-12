''' This program will gather necessary documents, based on user's need, on
    https://www.sec.gov/edgar/searchedgar/companysearch.html, by providing the
    CIK. The design will allow the user to specify the type of document and date
    range.

    Current document that can be scraped are 10-K and 10-Q.

    Name:   Norlan Prudente
    Date:   08/13/2018
'''

# Libraries needed to run the program.
import requests
from time import time, sleep
import traceback
import requests.packages.urllib3
from bs4 import BeautifulSoup
from itertools import cycle
from lxml.html import fromstring
import json
import csv

def getCIKs():
    """ This function will get all the CIKs in a file.

        Required:   None
        Return:     List of CIKs
    """
    # Open the file containing CIKs
    cikFile = open("CIKs.txt", "r")

    # Put it in a list
    cikList = cikFile.readlines()

    return cikList

def getDateRangeAndDocumentType():
    ''' This function will be used to get the date range and the type of
        document(s) the user need.

        Required:   None
        Return:     starting date, ending date, and types of document
    '''
    isCorrect  = False
    startDate  = input('Enter the date before the starting date in ' +
                       'YYYYMMDD format(ex. 20010101 for jan 1 2001): ')
    endDate    = input('Enter the date before the end date in YYYYMMDD ' +
                       'format(ex. 20010101 for jan 1 2001): ')
    docType    = input('Enter the document type, 10-K, 10-Q, or Both' +
                       '(case sensitive): ')


    while not (isCorrect):
        if (docType == '10-K' or docType == '10-Q' or docType == 'Both'):
            isCorrect = True
        else:
            print('That is not one of the choices.')
            docType = input('Enter the document type, 10-K, 10-Q, or Both' +
                            '(case sensitive): ')

    return startDate, endDate, docType

def getProxies():
    """ Get proxies from free-proxy-list.nte.

        Required:   None
        Return:     Proxies
    """
    numberOfProxies = 1000

    print("Getting proxies...")
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:numberOfProxies]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            #Grabbing IP and corresponding PORT
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    print(proxies)
    return proxies

def testProxies(proxies, workingProxies):
    print("Testing proxies...")
    """ Pick all the proxies that can connect to  the website.

        Required:   List to put all the working proxies in.
        Return:     List of all the working proxies.
    """
    proxiesToUse        = 10
    maxConnectionTime   = 5

    # Clearing proxies
    del workingProxies[:]

    # Create a pool of proxy
    proxy_pool = cycle(proxies)

    url = 'https://www.sec.gov/'

    for i in range(0,len(proxies)):
        #Get a proxy from the pool
        proxy = next(proxy_pool)
        print("Testing proxy #" + str(i) + " " + proxy)
        try:
            timeStart = time()
            response = requests.get(url, proxies={"http": proxy,
                                                  "https": proxy}, timeout=5)
            timeEnd = time()

            if str(response.status_code) == '200' and \
               timeEnd - timeStart < maxConnectionTime:
                workingProxies.append(proxy)

                if len(workingProxies) == proxiesToUse:
                    break
        except:
            continue

def pickProxytoUse(lastProxyIndex, workingProxies):
    """ Pick a proxy to use from a list of proxy.

        Required:   Previous proxy.
        Return:     New proxy.
    """
    # if we reach the last proxy, reset
    if lastProxyIndex >= len(workingProxies):
        lastProxyIndex = 0

    proxy = workingProxies[lastProxyIndex]
    print("Changing proxy to", proxy)

    return proxy, lastProxyIndex

def getLinks(startDate, endDate, docType, CIK, kLinks, qLinks, proxy,
             lastProxyIndex, workingProxies, count):
    ''' This function will get all the links that are needed to fetch
        all the documents that the user required.

        Required:   startDate, endDate, docType, CIK, kLinks, and qLinks
        Return:     List of links for either 10-K's, 10-Q's, or both
    '''
    #used to show which item are we starting with. It's important because some
    #document goes beyond 100 and only 100 are displayed per page.
    startIndex = 0
    #how many item are displayed in a page. Max item 100.
    count = 100
    #list to store all the links
    links = []
    # Boolean to check if there's more pages with links
    isNextPageAvailable = True

    # While there are still links to fetch
    while (isNextPageAvailable):

        # Generate the necessary URL based on the data given
        kUrl = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=' \
             + str(CIK) + '&type=10-K' + '&dateb=' + startDate + '&datea=' \
             + endDate + '&owner=exclude&start=' + str(startIndex) + '&count=' \
             + str(count)

        qUrl = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=' \
             + str(CIK) + '&type=10-Q' + '&dateb=' + startDate + '&datea=' \
             + endDate + '&owner=exclude&start=' + str(startIndex) + '&count=' \
             + str(count)

        # print("CIK:" + str(CIK) + " forms page " + str(int(startIndex / 100) + 1) + ": " + url)

        isConnected     = False
        connectionError = 0

        # Get the content from the URL passed above
        while not (isConnected):
            try:
                if docType == '10-K':
                    r = requests.get(kUrl, proxies={"http": proxy, "https": proxy}, timeout=5)

                    if str(r.status_code) == '200':
                        isConnected = True
                elif docType == '10-Q':
                    r = requests.get(qUrl, proxies={"http": proxy, "https": proxy}, timeout=5)

                    if str(r.status_code) == '200':
                        isConnected = True
                elif docType == 'Both':
                    r0 = requests.get(kUrl, proxies={"http": proxy, "https": proxy}, timeout=5)
                    r1 = requests.get(qUrl, proxies={"http": proxy, "https": proxy}, timeout=5)

                    if str(r0.status_code) == '200' and str(r1.status_code) == '200':
                        isConnected = True
            except Exception as e:
                print(e)
                connectionError += 1

                # Change the pool of proxies when all of them can't connect
                if connectionError >= 10:
                    print("Getting new set of proxies")
                    proxies = getProxies()
                    testProxies(proxies, workingProxies)
                    print(workingProxies)
                    proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
                    lastProxyIndex += 1
                    count = 0
                else:
                    proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
                    lastProxyIndex += 1
                    count = 0

        if docType == 'Both':
            # Using the parser to clean the content from website
            soup0 = BeautifulSoup(r0.content, 'html.parser')
            soup1 = BeautifulSoup(r1.content, 'html.parser')

            # Check if CIK is valid
            noMatchSoup = soup0.find_all('p')

            if len(noMatchSoup) > 0:
                if 'No matching CIK' in str(noMatchSoup[0]):
                    isNextPageAvailable = False
                    break

            # Get all the tags with <td nowrap="nowrap">
            tdSoup = soup0.find_all('td', {'nowrap' : 'nowrap'})
            if len(tdSoup) > 0:
                isNextPageAvailable = True
                # Get all the links
                for i in range(0, len(tdSoup), 3):
                    try:
                        kLinks.append('https://www.sec.gov' + str(tdSoup[i+1]).split('"')[3])
                    except:
                        continue
            # If there is no more links, then exit out of the loop
            else:
                isNextPageAvailable = False
                continue

            noMatchSoup = soup1.find_all('p')

            if len(noMatchSoup) > 0:
                if 'No matching CIK' in str(noMatchSoup[0]):
                    isNextPageAvailable = False
                    break

            tdSoup = soup1.find_all('td', {'nowrap' : 'nowrap'})
            if len(tdSoup) > 0:
                isNextPageAvailable = True
                for i in range(0, len(tdSoup), 3):
                    try:
                        qLinks.append('https://www.sec.gov' + str(tdSoup[i+1]).split('"')[3])
                    except:
                        continue
            else:
                isNextPageAvailable = False
                continue
        else:
            soup = BeautifulSoup(r.content, 'html.parser')
            tdSoup = soup.find_all('td', {'nowrap' : 'nowrap'})

            if len(tdSoup) > 0:
                isNextPageAvailable = True
                if docType == '10-K':
                    for i in range(0, len(tdSoup), 3):
                        try:
                            kLinks.append('https://www.sec.gov' + str(tdSoup[i+1]).split('"')[3])
                        except:
                            continue
                elif docType == '10-Q':
                    for i in range(0, len(tdSoup), 3):
                        try:
                            qLinks.append('https://www.sec.gov' + str(tdSoup[i+1]).split('"')[3])
                        except:
                            continue
            else:
                isNextPageAvailable = False
                continue

        # go to the next page
        startIndex += 100

    return lastProxyIndex, count

def getFormLinks(docType, formLinks, links, proxy, lastProxyIndex, workingProxies, pageVisited):
    """ This function will get the document's link, which contain the
        document that will be parsed later.

        Required:   links and formLinks
        Return:     List of links that contains the forms
    """
    # get all the links to the 10-K form
    for i in range(0, len(links)):
        print(links[i])
        # print("pageVisited", str(pageVisited))
        isConnected = False

        # get the content of the page
        while not (isConnected):
            try:
                r = requests.get(links[i], proxies={"http": proxy, "https": proxy})

                if str(r.status_code) == '200':
                    isConnected = True
                    # print("connected")
                else:
                    proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
                    lastProxyIndex += 1
            except Exception as e:
                print(e)
                proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
                lastProxyIndex += 1

        # Using the parser to clean the content from website
        soup = BeautifulSoup(r.content, 'html.parser')

        # Get all the tags with <div div class="info">
        tdSoup = soup.find_all('div', {'class' : 'info'})

        # get the year of the form
        try:
            year = str(tdSoup[0].text)[:4]
            print(year)
            if not (year in formLinks):
                formLinks[year] = []
        except:
            year = 'No Year'
            print(year)
            if not (year in formLinks):
                formLinks[year] = []

        # Get all the tags with <td scope="row">
        tdSoup = soup.find_all('td', {'scope' : 'row'})

        # Get the links and break after finding it, there should only be one
        # form per address
        for i in range(0, len(tdSoup)):
            if docType == tdSoup[i].text or (docType + '405') == tdSoup[i].text:
                # print (tdSoup[i].text)
                if '.htm' in tdSoup[i-1].text or '.txt' in tdSoup[i-1].text:
                    try:
                        formLinks[year].append('https://www.sec.gov' + str(tdSoup[i-1]).split('"')[3])
                        break
                    except:
                        continue
            elif 'Complete submission text file' == tdSoup[i].text:
                try:
                    formLinks[year].append('https://www.sec.gov' + str(tdSoup[i+1]).split('"')[3])
                    break
                except:
                    continue

        pageVisited += 1

        if pageVisited % 100 == 0:
            proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
            lastProxyIndex += 1

    return pageVisited, lastProxyIndex

    # print('==========================================================')
    # for k in links:
    #     print(k)
    # print('==========================================================')
    # for link in formLinks:
    #     print(link)

def getSentimentalValue(line, totalScore, scores):
    ''' Get the sentimental value of each word, if available.

        Required:   line or sentence, totalScore, and dictionary
                    with words and scores
        Return:     totalScore
    '''
    lines = [word.strip() for word in line.split()]

    if len(lines) > 0:
        for word in lines:
            if word.lower() in scores:
                totalScore += scores[word.lower()]

    return totalScore

def extractMDAFCRO(docType, dataNeeded, formLinks, proxy, lastProxyIndex,
                   workingProxies, pageVisited, scores):
    """ This function will extract, raw data, a section from a form, which
        is item 7 (10-K) or item 2(10-Q), Management’s Discussion and Analysis
        of Financial Condition and Results of Operations.

        Required:   Links to the form (kFormLinks, qFormLinks or both)
        Return:     Item 7
    """
    charactersToRemove = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                          ",", ".", ")", "(", "&", "!", ":", ";", "%", "$"]
    totalScore = 0

    # Visit each link and get item 7 from the form.
    for year in formLinks:
        for link in formLinks[year]:
            # print("pageVisited", str(pageVisited))
            print(year, link)
            isConnected = False

            # get the content of the page
            while not (isConnected):
                try:
                    r = requests.get(link, proxies={"http": proxy, "https": proxy})

                    if str(r.status_code) == '200':
                        isConnected = True
                        # print("connected")
                    else:
                        proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex,
                                                               workingProxies)
                        lastProxyIndex += 1
                except Exception as e:
                    print(e)
                    proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex,
                                                           workingProxies)
                    lastProxyIndex += 1

            if len(dataNeeded[len(dataNeeded) - 1]) > 1:
                dataNeeded.append([dataNeeded[len(dataNeeded) - 1][0]])

            dataNeeded[len(dataNeeded) - 1].append(year)

            # Using the parser to clean the content from website
            soup = BeautifulSoup(r.content, 'html.parser')

            # Get the whole forms text
            formText = soup.getText().encode('ascii', 'ignore').decode('ascii').lower()

#--------------------------------------Item7/2----------------------------------
            # Get the section needed
            if docType == '10-K':
                startString = "item7."
                endString = "item7a."

            elif docType == '10-Q':
                startString = "item2."
                endString = "item3."

            # Determine when to copy
            copyFlag = False

            for line in formText.split("\n"):
                if endString in line.replace(" ", ""):
                    copyFlag = False

                if startString in line.replace(" ", ""):
                    copyFlag = True

                if copyFlag:
                    # clean raw data
                    for char in charactersToRemove:
                        line = line.replace(char, "")
                        totalScore = getSentimentalValue(line, totalScore, scores)

            dataNeeded[len(dataNeeded) - 1].append(totalScore)
            totalScore = 0
            print(dataNeeded[len(dataNeeded) - 1])

            pageVisited += 1

            if pageVisited % 100 == 0:
                proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex,
                                                       workingProxies)
                lastProxyIndex += 1

    return pageVisited, lastProxyIndex

def save(CIK, dataStructure, type):
    ''' This function will save the last known CIK and the links that was
        gathered.

        Required:   last known CIK and links that was gathered.
        Return:     None.
    '''
    if type == 'links':
        f = open('Data/lastKnownIndex.txt', 'w')
    elif type =='forms':
        f = open('Data/lastKnownFormIndex.txt', 'w')
    elif type == 'item7' or type == 'item2':
        f = open('Data/lastKnownCSVIndex.txt', 'w')

    if not (type == 'modifiedItem7' or type == 'modifiedItem2'):
        f.write(str(CIK))
        f.close

    if type == 'item7':
        csvFile = open('item7.csv', 'w')
    elif type == 'item2':
        csvFile = open('item2.csv', 'w')
    elif type == 'modifiedItem7':
        csvFile = open('modifiedItem7.csv', 'w')
    elif type == 'modifiedItem2':
        csvFile = open('modifiedItem2.csv', 'w')
    elif type == 'links':
        f = open('Data/links.json', 'w')
    elif type =='forms':
        f = open('Data/formLinks.json', 'w')

    if type == 'links' or type == 'forms':
        json.dump(dataStructure, f)
        f.close
    else:
        # create a header
        header = ['CIK', 'Year', 'Sentimental Score']

        # add header at the beginning
        dataStructure = [header] + dataStructure

        writer = csv.writer(csvFile)
        writer.writerows(dataStructure)
        csvFile.close()


def load(type):
    ''' Get the last known CIK and all the links that was previously gathered.

        Required:   a dictionary to load the data.
        Return:     last known CIK and links that was previously gathered.
    '''
    try:
        if type == 'links':
            f = open('Data/lastKnownIndex.txt', 'r')
        elif type =='forms':
            f = open('Data/lastKnownFormIndex.txt', 'r')
        elif type == 'item7' or type == 'item2':
            f = open('Data/lastKnownCSVIndex.txt', 'r')

        lastKnownCIK = f.read()
        f.close
    except:
        lastKnownCIK = 0

    try:
        if type == 'item7':
            csvFile = open('item7.csv', 'r')
        elif type == 'item2':
            csvFile = open('item2.csv', 'r')
        elif type == 'links':
            f = open('Data/links.json', 'r')
        elif type =='forms':
            f = open('Data/formLinks.json', 'r')

        if type == 'links' or type == 'forms':
            dataStructure = json.load(f)
            f.close
        else:
            reader = csv.reader(csvFile)
            dataStructure = list(reader)
            csvFile.close()

            # remove the header
            dataStructure.pop(0)
    except Exception as e:
        print(e)
        print('No existing file exist. Do you want to continue? Press enter' +
              ' to continue')
        input()
        if type == 'links' or type == 'forms':
            dataStructure = {}
        else:
            dataStructure = []

    return lastKnownCIK, dataStructure

def getWordScores(afinnFileLocation):
    ''' Use AFINN to determine the score of words.

        Required:   AFINN file location/path
        Return:     Dictionary with words as key and score of the word as value.
    '''
    scores = {}

    with open(afinnFileLocation) as file:
        #one line at a time
        for line in file:
            #store the word and score
            word, score = line.split('\t')
            scores[word] = int(score)
        #close file
        file.close()

    return scores
def finalCleanup(item7, item2):
    ''' Clean up data structure by adding sentimental values of the same cik
        and year.

        Required:   item7 and item2
        Return:     None
    '''
    modifiedItem7 = []
    modifiedItem2 = []

    currentItem = []
    currentItem.append(item7[1][0])
    currentItem.append(item7[1][1])
    currentItem.append(item7[1][2])

    for i in range(1, len(item7)):
        if currentItem[0] == item7[i][0] and currentItem[1] == item7[i][1]:
            currentItem[2] = int(currentItem[2]) + int(item7[i][2])
        else:
            if len(currentItem) == 3:
                modifiedItem7.append(currentItem)
            currentItem = item7[i]

    save(20, modifiedItem7, 'modifiedItem7')

    currentItem = []
    currentItem.append(item2[1][0])
    currentItem.append(item2[1][1])
    currentItem.append(item2[1][2])

    for i in range(1, len(item2)):
        if currentItem[0] == item2[i][0] and currentItem[1] == item2[i][1]:
            currentItem[2] = int(currentItem[2]) + int(item2[i][2])
        else:
            if len(currentItem) == 3:
                modifiedItem2.append(currentItem)
            currentItem = item2[i]

    save(20, modifiedItem2, 'modifiedItem2')

def main():
    cikCount        = 0
    count           = 0
    pageVisited     = 0
    lastProxyIndex  = 0
    item2           = []
    item7           = []
    formLinks       = {}
    links           = {}
    qFormLinks      = []
    workingProxies  = []

    # Get all the CIK from a file
    CIKs = getCIKs()

    # Get the date range and document(s) type
    startDate, endDate, docType  = getDateRangeAndDocumentType()

    # Get proxies
    while(len(workingProxies) < 5):
        proxies = getProxies()
        testProxies(proxies, workingProxies)
    print(workingProxies)

    # Pick initial proxy to use
    proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
    lastProxyIndex += 1

    lastKnownCIK, links = load('links')

    if len(links) < 1:
        links['klinks'] = {}
        links['qlinks'] = {}

    # lastProxyIndex, count = getLinks(startDate, endDate, docType, 68649,
    # kLinks, qLinks, proxy, lastProxyIndex, workingProxies)
    # Get all the links for the requested documents
    for CIK in CIKs:
        CIK = CIK[:len(CIK)-1]

        if int(lastKnownCIK) >= int(CIK):
            continue

        print(CIK)

        links['klinks'][str(CIK)] = []
        links['qlinks'][str(CIK)] = []
        lastProxyIndex, count = getLinks(startDate, endDate, docType, CIK,
                                         links['klinks'][str(CIK)],
                                         links['qlinks'][str(CIK)], proxy,
                                         lastProxyIndex, workingProxies, count)
        count += 1
        cikCount += 1

        # Change proxy every 100 CIK
        if count % 100 == 0:
            proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
            lastProxyIndex += 1

        # save, every 5 ciks
        if cikCount % 5 == 0:
            print('saving')
            save(CIK, links, 'links')

    lastKnownFormCIK, formLinks = load('forms')

    if len(formLinks) < 1:
        formLinks['kForms'] = {}
        formLinks['qForms'] = {}

    count = 0
    cikCount = 0

# ------------------------------------------------------------------------------
    # get all the links of forms
    for CIK in CIKs:
        CIK = CIK[:len(CIK)-1]

        if int(CIK) <= int(lastKnownFormCIK):
            continue

        # for short cut
        # if int(CIK) >= 713002:
        #     break

        formLinks['kForms'][str(CIK)] = {}
        formLinks['qForms'][str(CIK)] = {}

        if docType == '10-K':
            print("Getting links to for the 10-K forms")
            pageVisited, lastProxyIndex = getFormLinks(docType,
                                                       formLinks['kForms'][str(CIK)],
                                                       links['klinks'][str(CIK)],
                                                       proxy, lastProxyIndex,
                                                       workingProxies, pageVisited)
        elif docType == '10-Q':
            print("Getting links to for the 10-Q forms")
            pageVisited, lastProxyIndex = getFormLinks(docType,
                                                       formLinks['qForms'][str(CIK)],
                                                       links['qlinks'][str(CIK)],
                                                       proxy, lastProxyIndex,
                                                       workingProxies, pageVisited)
        elif docType == 'Both':
            print("Getting links for the 10-K forms")
            pageVisited, lastProxyIndex = getFormLinks('10-K',
                                                       formLinks['kForms'][str(CIK)],
                                                       links['klinks'][str(CIK)],
                                                       proxy, lastProxyIndex,
                                                       workingProxies, pageVisited)
            print("Getting links for the 10-Q forms")
            pageVisited, lastProxyIndex = getFormLinks('10-Q',
                                                       formLinks['qForms'][str(CIK)],
                                                       links['qlinks'][str(CIK)],
                                                       proxy, lastProxyIndex,
                                                       workingProxies, pageVisited)

        count += 1
        cikCount += 1

        # Change proxy every 100 CIK
        if count % 100 == 0:
            proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
            lastProxyIndex += 1

        # save each loop
        if cikCount % 1 == 0:
            print('saving')
            save(CIK, formLinks, 'forms')

# ------------------------------------------------------------------------------
    lastKnownCSVCIK, item7 = load('item7')
    lastKnownCSVCIK, item2 = load('item2')

    count = 0
    cikCount = 0
    scores = getWordScores('AFINN-111.txt')

    # get all the links of forms
    for CIK in CIKs:
        CIK = CIK[:len(CIK)-1]

        if int(CIK) <= int(lastKnownCSVCIK):
            continue

        # if int(CIK) >= 30625:
        #     break

        if docType == '10-K':
            print("Fetching item 7")
            item7.append([CIK])
            pageVisited, lastProxyIndex = extractMDAFCRO(docType, item7,
                                                formLinks['kForms'][str(CIK)],
                                                proxy, lastProxyIndex,
                                                workingProxies, pageVisited,
                                                scores)
        elif docType == '10-Q':
            print("Fetching item 2")
            item2.append([CIK])
            pageVisited, lastProxyIndex = extractMDAFCRO(docType, item2,
                                                formLinks['qForms'][str(CIK)],
                                                proxy, lastProxyIndex,
                                                workingProxies, pageVisited,
                                                scores)
        elif docType == 'Both':
            print("Fetching item 7 from 10-K forms")
            item7.append([CIK])
            pageVisited, lastProxyIndex = extractMDAFCRO('10-K', item7,
                                                 formLinks['kForms'][str(CIK)],
                                                 proxy, lastProxyIndex,
                                                 workingProxies, pageVisited,
                                                 scores)
            print("Fetching item 2 from 10-Q forms")
            item2.append([CIK])
            pageVisited, lastProxyIndex = extractMDAFCRO('10-Q', item2,
                                                 formLinks['qForms'][str(CIK)],
                                                 proxy, lastProxyIndex,
                                                 workingProxies, pageVisited,
                                                 scores)

        count += 1
        cikCount += 1

        # Change proxy every 100 CIK
        if count % 100 == 0:
            proxy, lastProxyIndex = pickProxytoUse(lastProxyIndex, workingProxies)
            lastProxyIndex += 1

        # save each loop
        if cikCount % 1 == 0:
            print('saving')
            save(CIK, item7, 'item7')
            save(CIK, item2, 'item2')

    finalCleanup(item7, item2)

if __name__ == '__main__':
    main()
