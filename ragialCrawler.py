# -------------------- 0. INFORMATION
"""
RagialCrawler is a small Python (3.5.2) script which automatically
access Ragial, on a specified server, and uses the Search System, mainly
for Costumes queries, and gather useful economic information.

The original purpose of this script is to summarize all pertinent information
about iRO costume economics, bringing a extra facility to people who are actively
participating on the Ragnarok Costumes market.
"""
# -------------------- 1. IMPORT SECTION

from urllib.request import Request, urlopen  # Necessary to communicate with Ragial
from operator import itemgetter  # To sort the information get
from colorama import init, Fore  # For good terminal print aesthetics
from enum import IntEnum  # To keep the code more organized
import time  # Time, to put this daemon to sleep after a refresh
import re  # Regular expressions, to find interesting information
from datetime import datetime

# -------------------- END OF SECTION (1)

# -------------------- 2. CONFIGURATION SECTION

# These values can be modified to adopt the script to another personal interest.
# Please note that this is a facilitie, but the script itself was not originally
# thinked to be this dynamic. This means that deeper modifications on this script
# can be necessary, depending on the parameters set on this section.

ragialSearchLink = 'http://ragial.org/search/'  # Link to Ragial search section WITH A ENDING SLASH ('/')
ragialItemMarketLink = 'http://ragial.org/item/'  # Link of Ragial item shops info WITH A ENDING SLASH
serverName = 'iRO-Renewal'  # Server name
query = 'costume'  # Query to search for. Default is 'costume', but can be any query like 'card', 'box' etc.
myCustomHeader = {'User-Agent': 'Mozilla/5.0'}
dataRefreshTime = 300  # This time should be in seconds
requestDelay = 4.0  # Delay, in seconds, of a delay between each request on Ragial.
# IMPORTANT: low values (< 4.0s) tend to NOT work, resulting on a (Too many requests) 429 error.
maxRagialSearchPages = 3  # Max number of search result pages that script must goes into. Numbers smaller than 1 is nonsense.
interestThreshold = -0.2  # Threshold of proportion, in order to print shop information alongside the item if prop is smaller than it
removeQueryOnItemName = True  # Remove the query at the item name, in order to output be more clean
appendFullLink = False  # Should the entire item URL be appended on the table, or just the ID code?
maxShopNameDisplay = 30  # Helps mantaining the output order against unnecessary long shop names
colNames = [
    'P', 'Name', 'Best Price', 'Avg (7D)', 'Link', 'Coord', 'Shop Name'
]  # Output column names

# -------------------- END OF SECTION (2)

# -------------------- 3. CLASSES


# 3.1 This enumerator reflects the sequence of the information gatehered by the
# 'RegexFindItemPrice' when used on the Ragial HTML Source Page of a specific item.
class RagialValueOrder(IntEnum):
    # 'Short' is a seven (7) days analysis
    MIN_SHORT_PERIOD = 0  # Minimum item price on a (7) days analysis
    MAX_SHORT_PERIOD = 1  # Maximum item price on a (7) days analysis
    AVG_SHORT_PERIOD = 2  # Average item price on a (7) days analysis
    STDEV_SHORT = 3  # Standard Devitation of the item price on a (7) days analysis

    # 'Long' is a twenty eight (28) days analysis
    MIN_LONG_PERIOD = 4  # Minimum item price on a (28) days analysis
    MAX_LONG_PERIOD = 5  # Maximum item price on a (28) days analysis
    AVG_LONG_PERIOD = 6  # Average item price on a (28) days analysis
    STDEV_LONG = 7  # Standard Devitation of the item price on a (28) days analysis

    # From here, comes the available players prices
    MINIMAL_PRICE = 8  # The best price found on Ragial
    # The next values is the remaining prices, but they aren't useful for this scrip purpose.


# 3.2 This enumerator indicates the order of the columns used on dataframe to
# print the colected relevant data.
class scriptInfoOrder(IntEnum):
    PROPORTION = 0  # Proportion calculus is (CurrentBestPrice/ShortAveragePrice - 1)
    ITEM_NAME = 1  # Self explanatory
    MIN_CURRENT_PRICE = 2  # Current item best price detected on Ragial
    AVG_SHORT = 3  # Average item price on a seven (7) days analysis
    ITEM_LINK = 4  # Ragial correspondent item link
    # Parameters valid only for items with proportion below interestThreshold
    SHOP_COORD = 5
    SHOP_NAME = 6
    SHOP_URL = 7


# -------------------- END OF SECTION (3)

# -------------------- 4. REGULAR EXPRESSIONS

# 4.0 Get item URL and it's status (tagged as 'activate_tr' by Ragial for items currently on market)
RegexFindItemUrlWithStatus = re.compile(
    r'(?<=<a href="' + ragialItemMarketLink + serverName +
    r'/)([^"]+)"\s*class\s*=\s*"([^"]+)"\s*>')
# 4.1 Regex to search for all the item links, active or not on the market
RegexFindItemURLAndBestPrice = re.compile(r'<a href="' + ragialItemMarketLink +
                                          serverName +
                                          r'/([^"]+)">([0-9,]+)z</a>')
# 4.2 Regex to search for item's title/name
RegexFindItemTitle = re.compile(r'<title>\s*Ragial\s*-\s*([^-]+)\s*-\s*' +
                                serverName + r'\s*</title>')
# 4.3 Regex to search for item prices/standard devitations/related values
RegexFindItemPrice = re.compile(r'([0-9,]+)z')
# 4.4 Regex to detect for Ragial's next page link on search HTML source code (capturing the exact
# link is unnecessary, because these follows a very simple predictable pattern).
RegexFindNextPage = re.compile(r'<a href="' + ragialSearchLink + serverName +
                               '/' + query + '/' + r'\w">Next</a>')
# 4.5 Detect everything that is not a base 10 number
RegexOnlyAllowNumbers = re.compile(r'[^0-9]')
# 4.6 Get item best price shop url
RegexGetItemShopLink = re.compile(
    r'<tr\s*class="odd">\s*<td[^>]*>\s*<a\s*href="([^"]+)">Vending Now</a>'
)
RegexGetItemShopName = re.compile(
    r'<h2><img\s*src="http://ragial\.org/res/shop_vend\.png"[^/]*/>([^<]+)</h2>'
)
RegexGetItemShopCoord = re.compile(
    r'<dd>Location:</dd><dt><input.*value="([^"]+)"></dt>'
)

# -------------------- END OF SECTION (4)

# -------------------- 5. SOURCE SECTION


# Applies a Regex to find the item name on a given Raw HTML source code.
# It does return 'UnknownItemName' if Regex fails.
def getItemName(itemRawPageSource):
    regMatch = RegexFindItemTitle.search(itemRawPageSource)
    if regMatch:
        itemName = regMatch.group(1)
        return re.sub(
            query, '', itemName,
            flags=re.IGNORECASE) if removeQueryOnItemName else itemName
    return '<unknown>'


# Proportion of the Item Best Price and the Average Price (7 days analysis). Lower values (< 0)
# represent best opportunities, while higher (> 0) represent overpriced/price inflated items.
def calcProportion(bestPrice, avgPrice):
    return int(RegexOnlyAllowNumbers.sub('', bestPrice)) / int(
        RegexOnlyAllowNumbers.sub('', avgPrice)) - 1


# Get all economic relevant information on a raw HTML Item source page.
def parseNewItem(itemTitle, itemRawPageSource):
    # Seach for all relevant (zeny-based) information on the page HTML source code
    values = RegexFindItemPrice.findall(itemRawPageSource)
    if values:
        proportion = calcProportion(values[RagialValueOrder.MINIMAL_PRICE],
                                    values[RagialValueOrder.AVG_SHORT_PERIOD])
        return [
            proportion, itemTitle, values[RagialValueOrder.MINIMAL_PRICE],
            values[RagialValueOrder.AVG_SHORT_PERIOD]
        ]
    return []


# Produce a combination of Ragial Server's search link + query (costume, by default) + pageIndex
def _mountQueryLink(pageIndex):
    return ragialSearchLink + serverName + '/' + query + '/' + str(pageIndex)


# Set Price Proportions (BestPrice/AveragePrice - 1) output readable fomart
def _propToPercent(prop=0.0):
    return ('+' if prop >= 0 else '') + '{0:.2f}%'.format(prop * 100)


# Align output data do the right (pandas-style)
def _rightAlign(maxVal, text, sep=0):
    return '{m: <{fill}}'.format(m='', fill=sep + maxVal - len(text)) + text


# Set color to the proportion values (green only if < 0, red otherwise)
def _setPropColor(val, text):
    return ('\033[0;32m' if val < 0 else '\033[0;31m') + text + '\033[0m'


# Print all gathered data
def printTable(data, colnames, sep=2):
    maxLens = [0] * len(scriptInfoOrder)

    for d in data:
        for i in range(len(scriptInfoOrder)):
            if i != scriptInfoOrder.PROPORTION:
                maxLens[i] = max(maxLens[i], len(str(d[i])))
            else:
                maxLens[i] = max(maxLens[i],
                                 1 + len(str(round(d[i] * 100, 2))))

    maxLens[scriptInfoOrder.SHOP_NAME] = min(
        maxLens[scriptInfoOrder.SHOP_NAME], maxShopNameDisplay)

    lenColNum = len(str(len(data)))

    for i in range(len(colnames)):
        maxLens[i] = max(maxLens[i], len(colnames[i]))

    data.sort(key=itemgetter(scriptInfoOrder.PROPORTION), reverse=True)
    counter = 0
    for d in data:
        print(
            _rightAlign(lenColNum, str(counter)),
            _setPropColor(
                d[scriptInfoOrder.PROPORTION],
                _rightAlign(maxLens[scriptInfoOrder.PROPORTION],
                            _propToPercent(d[scriptInfoOrder.PROPORTION]),
                            sep)),
            _rightAlign(maxLens[scriptInfoOrder.ITEM_NAME],
                        d[scriptInfoOrder.ITEM_NAME], sep),
            _rightAlign(maxLens[scriptInfoOrder.MIN_CURRENT_PRICE],
                        d[scriptInfoOrder.MIN_CURRENT_PRICE], sep),
            _rightAlign(maxLens[scriptInfoOrder.AVG_SHORT],
                        d[scriptInfoOrder.AVG_SHORT], sep),
            _rightAlign(maxLens[scriptInfoOrder.ITEM_LINK],
                        d[scriptInfoOrder.ITEM_LINK], sep),
            _rightAlign(maxLens[scriptInfoOrder.SHOP_COORD],
                        d[scriptInfoOrder.SHOP_COORD], sep),
            Fore.MAGENTA + _rightAlign(
                maxLens[scriptInfoOrder.SHOP_NAME],
                d[scriptInfoOrder.SHOP_NAME][:(1 + maxShopNameDisplay)], sep) +
            Fore.RESET)
        counter += 1

    print('{text: <{fill}}'.format(text='', fill=lenColNum - 1), end='# ')
    for i in range(len(colnames)):
        print(_rightAlign(maxLens[i], colnames[i], sep), end=' ')
    print()


# Request a specific item's best sale coordinates, shop name and URL
def _requestItemCoordinates(item):
    errorValues = [(Fore.RED + i + ' not Found' + Fore.RESET)
                   for i in ['URL', 'Shop', 'Coord']]
    print(
        Fore.YELLOW + '\r[!] Requesting \'' + item + '\' shop details...',
        end=' ')

    # Safe request delay
    time.sleep(requestDelay)

    try:
        fullItemLink = ragialItemMarketLink + serverName + '/' + item

        request = Request(fullItemLink, headers=myCustomHeader)
        itemPageContent = urlopen(request).read().decode('utf-8')

        bestPriceShopLink = RegexGetItemShopLink.search(itemPageContent).group(1)

        shopRequest = Request(bestPriceShopLink, headers=myCustomHeader)
        shopPageContent = urlopen(shopRequest).read().decode('utf-8')

        bestPriceShopName = RegexGetItemShopName.search(shopPageContent).group(1)
        bestPriceShopCoord = RegexGetItemShopCoord.search(shopPageContent).group(1)

        return [
            bestPriceShopCoord,
            bestPriceShopName,
            bestPriceShopLink,
        ]

    except:
        return errorValues


def getItemCoord(item, prop):
    return (['---'] * 3
            if prop >= interestThreshold else _requestItemCoordinates(item))


# Main method of the script.
def main():
    # Init colorama
    init(autoreset=True)

    # Welcome text
    print(
        Fore.BLUE +
        'Welcome! I\'m RagialCrawler. First, I\'ll try to collect everything I can from Ragial, if possible. '
        +
        'I\'m supposed to work by myself and take care of everything alone while I\'m still active. '
        + 'So, from now and so on, you can just chill! ;)')
    print(Fore.YELLOW + 'Selected search query: \'' + query + '\'')

    # Memoization base, used to speed up things later.
    memoizationData = {}

    # Outter loop to keep program running 'forever', daemon-like application (1)
    while True:
        # -------------------- 5.1 VARIABLE SETUP (MODIFY ONLY IF YOU ARE SURE WHAT IS GOING ON)
        pageIndex = 0
        hasNextPage = True
        gatheredInfo = []
        # -------------------- END OF SUBSECTION (5.1)

        # Inner Loop here, while it has a 'next' page to search up to (2)
        while hasNextPage:
            hasNextPage = None
            rawPageSource = str()
            pageIndex += 1

            # -------------------- 5.2 REQUEST RAGIAL HTML SOURCE
            try:
                # Requesting Ragial Search HTML source
                request = Request(
                    _mountQueryLink(pageIndex), headers=myCustomHeader)

                rawPageSource = str(urlopen(request).read())

            except BaseException as exc:
                print(
                    Fore.RED +
                    'Fatal: could not get the source page from Ragial. (error: '
                    + repr(exc) + ')')
            # -------------------- END OF SUBSECTION (5.2)

            if rawPageSource:
                print(
                    Fore.YELLOW + 'New Ragial item page found (index: ' +
                    str(pageIndex) + ').',
                    end=' ')
                # Find the item links and best Prices (return should be a list of tuples on the format (URL, BestPrice))
                getSearchResultInfo = RegexFindItemURLAndBestPrice.findall(
                    rawPageSource)

                # Get item status (Ragial mark items current on market as 'activate_tr')
                getItemStatus = dict(
                    RegexFindItemUrlWithStatus.findall(rawPageSource))

                # Get only items current on sale
                getSearchResultInfo = [
                    i for i in getSearchResultInfo if i[0] in getItemStatus
                ]

                # How many active items found on current search page
                totalItemsFound = len(getSearchResultInfo)

                if totalItemsFound <= 0:
                    # Ragial put inactive items to later pages. If no item was found on current page, then
                    # no item will be found on next pages, if they even exists.
                    print(
                        Fore.YELLOW +
                        'No active items found on this page. Finishing the search process sooner.'
                    )
                else:
                    print(Fore.YELLOW + 'Total of ' + str(totalItemsFound) +
                          ' items in market on this page.')
                    # Rebase the information in order to work with then easier
                    itemLinkID = [i[0] for i in getSearchResultInfo]
                    itemBestPrice = dict(
                        zip(itemLinkID, [i[1] for i in getSearchResultInfo]))

                    # Interface counter
                    currentItemCounter = 0
                    # -------------------- 5.3 GET ITEM ECONOMIC DATA
                    try:
                        for item in itemLinkID:
                            currentItemCounter += 1
                            if item in memoizationData:
                                print(
                                    Fore.YELLOW + 'Updating \'' + item +
                                    '\' item cache (' + str(currentItemCounter)
                                    + '/' + str(totalItemsFound) + ')...',
                                    end=' ')
                                # Item is already on the memoization data structure, don't need to do another page request
                                # Fisrt, get the old data
                                memoItemData = memoizationData[item]

                                # Now need just to update the following parameters:
                                #	- a. Best price
                                # 	- b. Proportion
                                memoItemData[
                                    scriptInfoOrder.
                                    MIN_CURRENT_PRICE] = itemBestPrice[item]
                                memoItemData[scriptInfoOrder.
                                             PROPORTION] = calcProportion(
                                                 itemBestPrice[item],
                                                 memoItemData[scriptInfoOrder.
                                                              AVG_SHORT])

                                # If proportion accuses a relevant offer, request current item coordinates/shop indo
                                coordInfo = getItemCoord(
                                    item,
                                    memoItemData[scriptInfoOrder.PROPORTION])
                                for i in range(len(coordInfo)):
                                    memoItemData[i + len(scriptInfoOrder) -
                                                 len(coordInfo)] = coordInfo[i]

                                # Append the updated info on the gathered data list
                                gatheredInfo.append(memoItemData)

                                # Print confirmation that everything works fine
                                print(Fore.YELLOW + '\t[ok]')

                            else:
                                # Item is not on the memoization data structure, then request item's HTML source page
                                print(
                                    Fore.YELLOW + 'Requesting \'' + item +
                                    '\' item data (' + str(currentItemCounter)
                                    + '/' + str(totalItemsFound) + ')...',
                                    end=' ')
                                time.sleep(requestDelay)
                                itemRawPageSource = str()

                                try:
                                    # Mount full item link and make a requisition to Ragial server
                                    fullItemLink = ragialItemMarketLink + serverName + '/' + item
                                    itemRequest = Request(
                                        fullItemLink, headers=myCustomHeader)

                                    # Get page HTML source code
                                    itemRawPageSource = str(
                                        urlopen(itemRequest).read())

                                    # Search for the item name on the page HTML source code
                                    itemTitle = getItemName(itemRawPageSource)

                                    # Get new item information as a list
                                    newItemParsed = parseNewItem(
                                        itemTitle, itemRawPageSource)

                                    # Append the item link too, for user offer checkup facility
                                    newItemParsed.append(
                                        fullItemLink
                                        if appendFullLink else item)

                                    # If proportion accuses a interesting offer, get best sale shop coords/map/url
                                    newItemParsed += getItemCoord(
                                        item, newItemParsed[scriptInfoOrder.
                                                            PROPORTION])

                                    # Append a new information pack about a item
                                    gatheredInfo.append(newItemParsed)

                                    # Update the memoization structure in order to make things faster in the next iteration
                                    memoizationData.update({
                                        item: newItemParsed
                                    })

                                    # Print confirmation that everything works fine
                                    print(Fore.YELLOW + '\t[ok]')

                                except BaseException as exc:
                                    print(
                                        Fore.RED + 'Error on getting',
                                        ragialItemLink + serverName +
                                        '/' + item + '\' (error: ' + repr(exc)
                                        + ') data.')

                        # Move to the next page, and repeat inner loop (2), if the index max was not still reached
                        if pageIndex < maxRagialSearchPages:
                            # Check if there's a search next page
                            hasNextPage = RegexFindNextPage.search(
                                rawPageSource)

                            # Delay to now overflow Ragial with requests
                            time.sleep(requestDelay)
                        else:
                            # Force script inner loop to break
                            print(Fore.YELLOW + 'Search page limit reached (' +
                                  str(pageIndex) + ').')

                    except BaseException as exc:
                        print(Fore.RED + 'Error: ' + repr(exc))
                    # -------------------- END OF SUBSECTION (5.3)
        # -------------------- 5.4 PRINT ALL GATHERED INFORMATION
        # Remove all null data from the gathered info (probably all empty lists)
        gatheredInfo = [item for item in gatheredInfo if item]
        # Check if there is at least a single valid information
        if gatheredInfo:
            # Print all gathered data
            printTable(gatheredInfo, colNames)
        else:
            print(Fore.YELLOW + 'Warning: no data gathered at all.')
        # -------------------- END OF SUBSECTION (5.4)

        # Make the program 'sleep' for some minutes, to wait Ragial update it's info
        print(Fore.BLUE + 'Time til next data refresh: ' +
              str(dataRefreshTime) + 's (last update: ' + 'system: ' +
              datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\tUTF: ' +
              datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + ')')
        time.sleep(dataRefreshTime)
        print(Fore.YELLOW + 'Started to get brand-new information...')


# SCRIPT START
if __name__ == '__main__':
    main()

# -------------------- END OF SECTION (5)
