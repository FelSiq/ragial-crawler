# RagialCrawler
RagialCrawler is a simple Python (version 3.5) script which automatically search all costumes-like items on Ragial default to on iRO-Renewal server (but has easy support to all other Ragial supported servers), and get all relevant economic data from each found item. Then, at the end, it does print all the found items sorted by the proportion of Best Current Price Found and Short (7D) Average Item Price.

The code is absolutely garbage. I've made it a couple years ago, and since the last update I don't even play Ragnarok anymore. If you are planning just to run the script, then you will probably do fine. However, if you're planning to make big changes in the script, then I wish you the best of the lucks.

# Dependencies
- Python 3.5 or a greater version
- 'colorama' library
- Other libraries should not be a problem.

# Run
First, install the dependencies using pip:
```
pip install -Ur requirements.txt
```

Then, to run the script, type on your terminal/console which follows:
```
python ragialCrawler.py
```

# Functionallity
- The program does not need any input. 
- It is supposed to run until the user stops it manually (Ctrl+C or killing the process). 
- If the user ends the program, all memoized data will be lost, and must be regathered on the next session. This will not be 'fixed', as it prevents outdated memoized information.
- It does update every 5 mins (300 seconds), in order to follow the Ragial update delay and to do not overcharge Ragial server with requests.
- It does check all Ragial search pages, and get information only about items currently active on market.
- It has a delay of fours (4) seconds between each item data request, to avoid (Too Many Requests) 429 error. This delay occurs only on new items not memoized on the current section. If the item is already on the memoization table (i.e already found on previous iterations), it does not need a additional request, and the script only update it's best price and the proportion in relation of average price (7 days analysis), and proceed to the next item without delay.
- It has a four (4) seconds delay between each next page search request, in order to avoid (Too Many Requests) 429 error on the scenario when all items of the current page are already on the memoization structure.

# Output
<img src="/images/output_sample.png" width="800" height="800"/>

The output is a Data Frame, which column order follows the specified order:
- Proportion: calculated by ((Best Ragial Price)/(Average Item Price (7 day analysis)) - 1.0) * 100.0
- Item name
- Best Ragial price at moment
- Average Price on a seven (7) days analysis
- Ragial item link
