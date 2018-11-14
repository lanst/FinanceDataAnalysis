import xlsxwriter
import xlrd
import requests
import time
from bs4 import BeautifulSoup
from time import time, sleep


def main():
    totalStart = time()
    # Open the file containing CIKs
    cikFile = open("CIKs.txt", "r")  # The file CIKs.txt contains the list of CIKs to iterate over
    cikList = cikFile.readlines()

    KFullFileResults = []
    QFullFileResults = []
    kmdaResults = []
    qmdaResults = []

    criticalWords, wordIndices, words = getCriticalWords()
    columnHeaderWords = []

    # create a list of words that will be used as the column headers in the excel file written at the end
    for key in criticalWords:
        if criticalWords[key] == "Negative":
            columnHeaderWords.append(key)
    columnHeaderWords.sort()
    # print(columnHeaderWords)

    # iterate over each CIK in the list of CIKs
    for CIK in cikList:
        rnum = int(CIK.strip("\n")) % 10
        sleep(rnum)  # for debugging, there is still an issue with long runs of the program. It ends
        # up making so many requests so fast that the DDOS defense mechanisms of the SEC
        # site are triggered. Adding sleep will mitigate this problem but slow it down tremendously

        if int(CIK.strip("\n")) % 100 == 0:  # sleep 2 minutes every 200 CIKS
            sleep(120)
        print("-----------------------------------------------")

        print("\n===== " + CIK.strip("\n") + " ===== 	" + str(cikList.index(CIK) + 1) + "/" + str(len(cikList)))
        cikStart = time()
        CIK = CIK.strip("\n")

        myResults = {}
        allFilingsReferences, SIC = getFilingsLinks(
            CIK)  # call the function to get all of the document links available(see function comments)
#        print(allFilingsReferences)
        fileCount = 0
        cikStop = time()
        # for each file types in the dictionary of links
        for fileType in allFilingsReferences:
            # if fileType == "10-K" or fileType == "10-K405" or fileType == "10-Q" : #check that the filetype is in line with research paramters
            if fileType == "10-K" or fileType == "10-K405":
                print(str(fileType))
                for reportFile in allFilingsReferences[fileType]:  # for each individual file of the allowed types
                    myResults = {}
                    #print(allFilingsReferences[fileType])
                    if int(reportFile["Filing Date"].split("-")[0]) >= 1988:
                       # sleep(3)
                        finalFormLink = getFormLink(reportFile["link"],
                                                    fileType)  # get the final link from the file page
                        fileCount = fileCount + 1
                        print("\t" + str(fileCount) + ". Document link: " + str(finalFormLink))

                        mdaText, MDAsubsectionFlag, allText = extractItem7Text(finalFormLink)  # see function comments
                        positive, negative, xlsList, MDAwordCount = goodBadWordCounts(mdaText, criticalWords,
                                                                                      wordIndices)
                        #print(mdaText)
                        #print("DEBUG mda: " + str(positive))
                        #print("DEBUG mda: " + str(negative))

                        # organize data into the temporary dict myResults
                        myResults["Total # words"] = MDAwordCount
                        # myResults["End of Quarter Date"] #should be in there for 10qs
                        myResults["SIC"] = SIC
                        myResults["CIK"] = CIK
                        myResults["Report Date"] = reportFile["Filing Date"]
                        myResults["MD&A subsection"] = str(MDAsubsectionFlag)
                        myResults["Positive words"] = positive
                        myResults["Negative words"] = negative
                        myResults.update(xlsList)

                        # dump dict to list of result dictionaries
                        if fileType == "10-K" or fileType == "10-K405":
                            kmdaResults.append(dict(myResults))
                        elif fileType == "10-Q":
                        	qmdaResults.append(dict(myResults))

                        positive, negative, xlsList, TotalWordCount = 0, 0, 0, 0  # reset values
                        positive, negative, xlsList, TotalWordCount = goodBadWordCounts(allText, criticalWords,
                                                                                        wordIndices)  # see function comments
                        myResults["Total # words"] = TotalWordCount
                        myResults["Positive words"] = positive
                        myResults["Negative words"] = negative
                        #print("DEBUG full: " + str(positive))
                        #print("DEBUG full: " + str(negative))

                        myResults.update(xlsList)

                        # dump dict to list of result dictionaries
                        if fileType == "10-K" or fileType == "10-K405":
                            KFullFileResults.append(dict(myResults))
                        elif fileType == "10-Q":
                            QFullFileResults.append(dict(myResults))

                        cikStop = time()
        print("CIK:" + CIK + " Execution time: " + str(round(cikStop - cikStart, 2)))

    # send results to xls file
    dataColumnHeadersK = ["CIK", "SIC", "Report Date", "MD&A subsection", "Positive words", "Negative words",
                          "Total # words"]
    dataColumnHeadersQ= ["CIK", "End of Quarter Date", "SIC", "Report Date", "MD&A subsection", "Positive words", "Negative words", "Total # words"]
    writeToXls(KFullFileResults, columnHeaderWords, "Full 10-K", dataColumnHeadersK)
    writeToXls(QFullFileResults, columnHeaderWords, "Full 10-Q", dataColumnHeadersQ)
    writeToXls(kmdaResults, columnHeaderWords, "10-K MD&A", dataColumnHeadersK)
    writeToXls(qmdaResults, columnHeaderWords, "10-Q MD&A", dataColumnHeadersQ)

    totalStop = time()
    print("Grand total runtime: " + str(round(totalStop - totalStart, 2)))


def getFilingsLinks(CIK):
    # this function makes a continuosly loads new pages with the list of all file and their respective links
    # and dumps them into a dictionary. The dictionary will have a link for every document page available for
    # the given CIK. This allows for expandability later if other files need to be analysed the links will already be available

    startIndex = 0
    count = 100
    filingsData = {}
    linkcount = 0
    while True:  # while the newly generated webpage still contains new links
        newLinkFlag = False
        # Generate the necessary URL based on the CIK number
        url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=" + str(
            CIK) + "&type=&dateb=&owner=exclude&start=" + str(startIndex) + "&count=" + str(count)
        print("CIK:" + str(CIK) + " forms page " + str(int(startIndex / 100) + 1) + ": " + url)

        # Get the content from the URL passed above
        r = requests.get(url)

        # Using the parser to clean the content from website
        soup = BeautifulSoup(r.content, "html.parser")

        # get all of the corresponding title fields
        indexCounter = 0
        tdSoup = soup.find_all("td")
        for title in tdSoup:  # dump file name, file date, and link to file into a dictionary
            if "Documents" in title.text in title.text:
                newLinkFlag = True
                link = "https://www.sec.gov" + str(tdSoup[indexCounter]).split('"')[3]
                if ".txt" in link or ".htm" in link:

                    if tdSoup[indexCounter - 1].text not in filingsData:
                        filingsData[tdSoup[indexCounter - 1].text] = [
                            {"Filing Date": tdSoup[indexCounter + 2].text, "link": link}]
                    else:
                        filingsData[tdSoup[indexCounter - 1].text].append(
                            {"Filing Date": tdSoup[indexCounter + 2].text, "link": link})
            indexCounter += 1

        if newLinkFlag:
            startIndex += count
            linkcount += indexCounter
        else:
            break

    print("\tNumber of filing links: " + str(linkcount))
    print("\tSize of filingsData: " + str(len(filingsData)))

    SIC = "Not Available"
    filteredSoup = soup.find_all("div")
    for line in filteredSoup:
        temp = line.text
        if "SIC: " in temp:
            SIC = temp.split("SIC: ")[1].split(" ")[0]
            break

    return filingsData, SIC  # returning dict of links and SIC here to reduce the number of requests the are needed per file/CIK


def getFormLink(filingUrl, formName):
    # this function pulls the final link out of the page that contains the target form

    formName = "FORM " + formName
    r = requests.get(filingUrl)

    # parse web page content
    soup = BeautifulSoup(r.content, "html.parser")
    filteredSoup = soup.find_all("td")

    for object in filteredSoup:  # if there is a link to the specific form then that will come up first, otherwise the complete submission will be used which occurs last
        if formName in object or "Complete submission text file" in object:
            link = "https://www.sec.gov/" + str(filteredSoup[filteredSoup.index(object) + 1]).split('"')[3]
            if ".txt" in link or ".htm" in link:
                return link

    # if that fails
    formName = formName.strip("FORM ")
    filteredSoup = soup.find_all("tr")
    for object in filteredSoup:
        if formName in str(object):
            rawHtml = str(object).split(">")
            for subString in rawHtml:
                if "href=" in subString:
                    finalLinkString = "https://www.sec.gov/"
                    finalLinkString += subString.strip('a href="').strip('"').strip("<a href=").strip('"')
                    return finalLinkString


def extractItem7Text(Url):
    # download form and parse to standard ascii text
    downloadStart = time()
    r = requests.get(Url)
    soup = BeautifulSoup(r.content, "html.parser")
    # [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
    formText = soup.getText().encode('ascii', 'ignore').decode('ascii').lower()

    #print(str(formText))
    print("Trace Extract Item 7")
    print(Url)

    downloadStop = time()
    print("\tForm download time: " + str(round(downloadStop - downloadStart, 3)) + " seconds")

    # Cut out portion of text between startString and endString
    startString = "item7."
    endString = "item7a."
    MDAflag = "0"

    copyFlag = False
    item7Only = []
    for line in formText.split("\n"):
        if endString in line.replace(" ", ""):
            copyFlag = False
        if startString in line.replace(" ", ""):
            copyFlag = True
            MDAflag = "1"
        if copyFlag:
            item7Only.append(line)

    # Change file to lower case and clean punctuation, scrub text
    start = time()
    charactersToRemove = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", ",", ".", ")", "(", "&", "!", ":", ";", "%",
                          "$"]
    temp = []
    for line in item7Only:
        line = line.lower()
        for char in charactersToRemove:
            line = line.replace(char, "")
        temp.append(line)
    item7Only = list(temp)
    stop = time()
    print ("\tPreprocessing time: " + str(round(stop - start, 4)))

    with open("Item7data/CIK20.txt", "w+") as saveFile:
        for line in item7Only:
            saveFile.write(line + "\n")

    cleanedFormText = []
    for line in formText.split("\n"):
        line = line.lower()
        for char in charactersToRemove:
            line = line.replace(char, "")
        if line != "":
            cleanedFormText.append(line)

    # print(item7Only)
    # print(cleanedFormText)
    return item7Only, MDAflag, cleanedFormText


def wordFrequencyAnalysis(text, CIK):
    ####################################################################################
    # This is the section of the program where the word occurrences are counted up.
    # Previously, the dictionary file was being scanned through word by word and for each
    # word in the dictionary the text was being read through and the program counted up
    # the number of times each word came up. Now, the dictionary file is no longer needed.
    # the text is scanned through and each time a word comes up it is added to a dictionary
    # (the data structure) or the value associated with the word in the dictionary is incremented.
    # Count total number of words in MD&A subsection simultaniously

    wordCount = 0
    start = time()
    occurrencesDict = {}
    for line in text:
        for word in line.split(" "):
            if word != "":
                wordCount += 1
                word = word.lower().replace("\n", "")
                if word in occurrencesDict:
                    occurrencesDict[word] += 1
                else:
                    occurrencesDict[word] = 1

    print("Total word count: " + str(wordCount))

    with open("wordFrequencies/CIK" + str(CIK), "w+") as frequencyFile:
        for word in occurrencesDict:
            frequencyFile.write(word + "\n" + str(occurrencesDict[word]) + "\n")
    stop = time()
    print("Analysis time: " + str(round(stop - start, 3)))


def writeToXls(results, allWords, sheetName, dataColumnHeaders):
    workbook = xlsxwriter.Workbook(sheetName + ".xlsx")
    myWorksheet = workbook.add_worksheet("Results")
    columnHeaders = list(dataColumnHeaders)
    columnHeaders.extend(list(allWords))

    for index in range(len(columnHeaders)):
        myWorksheet.write(0, index, columnHeaders[index])
    #print(results)
    for company in range(0, len(results)):
        for key in columnHeaders:
            try:
                myWorksheet.write(company + 1, columnHeaders.index(key), results[company][key])
            except KeyError as e:
                myWorksheet.write(company + 1, columnHeaders.index(key), 0)

    workbook.close()


def getCriticalWords():
    # read in list of positive and negative words

    print("Reading in critical word list file")
    start = time()
    xl_wordbook = xlrd.open_workbook("requestfortonedata.xlsx")
    wordSheet = xl_wordbook.sheet_by_name("word list")
    criticalWords = {}
    wordIndicies = {}
    allWords = []  # this list holds all words with either positive or negative implications, used to create header in the xlsx file
    count = 0
    while True:
        try:
            c = wordSheet.row(count)
            wordIndicies[str(c[0]).replace("text:'", "").strip("'").lower()] = count
            if str(c[1]) == "number:1.0":
                criticalWords[str(c[0]).replace("text:'", "").strip("'").lower()] = "Negative"
                allWords.append(str(c[0]).replace("text:'", "").strip("'").lower())
            elif str(c[2]) == "number:1.0":
                criticalWords[str(c[0]).replace("text:'", "").strip("'").lower()] = "Positive"
                allWords.append(str(c[0]).replace("text:'", "").strip("'").lower())
            count += 1
        except IndexError as e:
            break
        except Exception as e:
            print("UNKNOWN ERROR READING CRITICAL WORDS: " + str(e))
    stop = time()
    print("Critical word file (xlsx) read time: " + str(round(stop - start, 3)))

    # criticalWords is a dictionary which contains all of the words with a positive or negaitive meaning,
    #	# the words are the keys and the value is 'positive' or 'negative'
    # allwords is a list with the positive or negative words
    # word indices is a dict with words as keys and their index in the list of words used for outputing to the xls file
    #	# this was done for efficiency in other places of the program

    return criticalWords, wordIndicies, allWords


def goodBadWordCounts(text, criticalWords, wordIndices):
    positiveWordCount = 0
    negativeWordCount = 0
    totalMDAwordCount = 0
    wordCountDict = {}
    for line in text:
        for word in line.split(" "):
            if word != "":
                totalMDAwordCount += 1
                if word in criticalWords:
                    if criticalWords[word] == "Positive":
                        positiveWordCount += 1
                    elif criticalWords[word] == "Negative":
                        negativeWordCount += 1
                    # print(str(negativeWordCount) + ": " + repr(word))
                    else:
                        print("ERROR ----------------------")

                if word in wordCountDict:
                    wordCountDict[word] += 1
                else:
                    wordCountDict[word] = 1
    return positiveWordCount, negativeWordCount, wordCountDict, totalMDAwordCount


# wordCountDict is a dict with every word present in the file as a key and the number of occurances as the value



if __name__ == "__main__":
    main()
