''' This program will just format data to be graph in excel.

    Name:   Norlan Prudente
    Date:   12/10/2018
'''
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
def getData(lastI, item7, CIK):
    year = 2019
    cikData = []

    for i in range(lastI, len(item7)):
        lastI = i
        if not (CIK == int(item7[i][0])):
            for i in range(year, 1960, -1):
                # print(year)
                if year == 1960:
                    break
                cikData = [''] + cikData
                year -= 1

            cikData = [CIK] + cikData

            return lastI, cikData
        else:
            while not (year == int(item7[i][1])):
                # print(year, int(item7[i][1]))
                if year == 1960:
                    break
                cikData = [''] + cikData
                year -= 1

            if year == int(item7[i][1]):
                # print(year, int(item7[i][1]))
                cikData = [item7[i][2]] + cikData
                year -= 1

    for i in range(year, 1960, -1):
        # print(year)
        if year == 1960:
            break
        cikData = [''] + cikData
        year -= 1

    cikData = [CIK] + cikData

    return lastI, cikData

try:
    csvFile = open('USEconomy.csv', 'r')

    reader = csv.reader(csvFile)
    dataStructure = list(reader)
    csvFile.close()

    csvFile = open('modifiedItem7.csv', 'r')

    reader = csv.reader(csvFile)
    item7 = list(reader)
    csvFile.close()

    csvFile = open('modifiedItem2.csv', 'r')

    reader = csv.reader(csvFile)
    item2 = list(reader)
    csvFile.close()

except Exception as e:
    print(e)
    print('No existing file exist. Do you want to continue? Press enter' +
          ' to continue')

# item7
data = []
year = ['year']
GDP = ['GDP']
CIKs = getCIKs()

for i in range(1961, 2020):
    year.append(i)

data.append(year)

for i in range(5, len(dataStructure[0])):
    GDP.append(dataStructure[0][i])

data.append(GDP)
cikData = []
lastI = 1

for CIK in CIKs:
    CIK = int(CIK[:len(CIK)-1])

    lastI, cikData = getData(lastI, item7, CIK)
    data.append(cikData)

csvFile = open('item7Graph.csv', 'w')

writer = csv.writer(csvFile)
writer.writerows(data)
csvFile.close()

# item2
data = []
data.append(year)
data.append(GDP)
cikData = []
lastI = 1

for CIK in CIKs:
    CIK = int(CIK[:len(CIK)-1])

    lastI, cikData = getData(lastI, item2, CIK)
    data.append(cikData)

csvFile = open('item2Graph.csv', 'w')

writer = csv.writer(csvFile)
writer.writerows(data)
csvFile.close()
