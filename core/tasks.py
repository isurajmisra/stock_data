import json
from .views import get_option_data
import datetime
from django.core.cache import cache
import pandas as pd
from celery import shared_task
from .models import *


@shared_task
def save_stock_data():
    symbol = cache.get('symbol')
    print(symbol)
    try:
        i = True
        max_retry = 100
        j = 1
        while (i):
            page = get_option_data(symbol)
            if page.status_code == 200:
                i = False
            elif j <= max_retry:
                i = True
                print(f"Trying to connect - {j}")
                j += 1
            else:
                raise Exception

    except Exception as e:
        print(e)
        return
    dajs = json.loads(page.text)
    expiry_dt = dajs['records']['expiryDates'][0]

    ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt]

    pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt]

    ce_df = pd.DataFrame(ce_values, columns=['changeinOpenInterest', 'strikePrice'])
    pe_df = pd.DataFrame(pe_values, columns=['changeinOpenInterest', 'strikePrice'])

    ce_df['strikePrice'] = ce_df['strikePrice'].astype(int)
    index_quote_lastPrice = int(dajs['records']['underlyingValue'])
    ce_df_sort = ce_df.iloc[(ce_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
    pe_df_sort = pe_df.iloc[(pe_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
    cr1 = ce_df_sort[0] - 7
    cr2 = ce_df_sort[0] + 8
    pr1 = pe_df_sort[0] - 7
    pr2 = pe_df_sort[0] + 8
    ce_dt = ce_df[cr1:cr2]
    pe_dt = pe_df[pr1:pr2]

    ce_dt['changeinOpenInterest'] = ce_dt['changeinOpenInterest'].astype(int) * 25
    pe_dt['changeinOpenInterest'] = pe_dt['changeinOpenInterest'].astype(int) * 25
    ce_dt['strikePrice'] = ce_dt['strikePrice'].astype(int)
    pe_dt['strikePrice'] = pe_dt['strikePrice'].astype(int)
    ce_changeInOpenInterest_sum = ce_dt['changeinOpenInterest'].sum()
    pe_changeInOpenInterest_sum = pe_dt['changeinOpenInterest'].sum()
    diff_changeinOpenInterest = pe_changeInOpenInterest_sum - ce_changeInOpenInterest_sum

    if diff_changeinOpenInterest > 1000000:
        call = "Buy Call Option"
    elif diff_changeinOpenInterest < -1000000:
        call = "Buy Put Option"
    else:
        call = "Neutral"

    print(dajs['records']['timestamp'])
    date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
    ce_dt['timestamp'] = date_time_obj
    pe_dt['timestamp'] = date_time_obj

    intraday_data = IntradayData.objects.create(call=ce_changeInOpenInterest_sum, put=pe_changeInOpenInterest_sum, diff=diff_changeinOpenInterest, time=date_time_obj, signal=call)
    intraday_data.save()
    return "Taks Completed"

