from __future__ import absolute_import, unicode_literals
import datetime
import json
import time
from django.core.cache import cache
import requests
from django.db.models import Q
from django.shortcuts import render, redirect
from requests.adapters import HTTPAdapter
from django.http import JsonResponse
import pandas as pd
from urllib3 import Retry
from .models import IntradayData, StrikeData
from datetime import timedelta
import socket
import schedule
from urllib3.connection import HTTPConnection
HTTPConnection.default_socket_options = ( 
            HTTPConnection.default_socket_options + [
            (socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000), #1MB in byte
            (socket.SOL_SOCKET, socket.SO_RCVBUF, 1000000)
        ])

def home(request):
    IntradayData.objects.filter(time__lte=datetime.datetime.now() - datetime.timedelta(days=1)).delete()
    print("data deleted.")
    return render(request, 'stockData.html')


def update_starike_data(request,page):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    strike_price = request.GET.get('strike_price')
    today = datetime.date.today()
    # page = get_option_data(symbol)

    try:
        dajs = json.loads(page.text)
        expiry_dt = dajs['records']['expiryDates'][0]

        ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt and data['strikePrice']== int(strike_price)]

        pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt and data['strikePrice']== int(strike_price)]

        ce_df = pd.DataFrame(ce_values, columns=['strikePrice', 'changeinOpenInterest', 'totalTradedVolume', 'impliedVolatility', 'totalBuyQuantity', 'totalSellQuantity'])
        pe_df = pd.DataFrame(pe_values, columns=['strikePrice', 'changeinOpenInterest', 'totalTradedVolume', 'impliedVolatility', 'totalBuyQuantity', 'totalSellQuantity'])
        ce_df['strikePrice'] = ce_df['strikePrice'].astype(int)
        index_quote_lastPrice = int(dajs['records']['underlyingValue'])
        ce_df_sort = ce_df.iloc[(ce_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
        pe_df_sort = pe_df.iloc[(pe_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
        cr1 = ce_df_sort[0] - 3
        cr2 = ce_df_sort[0] + 3
        pr1 = pe_df_sort[0] - 3
        pr2 = pe_df_sort[0] + 3
        ce_dt = ce_df[cr1:cr2]
        pe_dt = pe_df[pr1:pr2]
        date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
        
        filtered_ce = [item for item in ce_values if item['strikePrice'] in ce_dt['strikePrice'].values]
        filtered_pe = [item for item in pe_values if item['strikePrice'] in pe_dt['strikePrice'].values]
        date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
        combined_filtered_list = []

        for i in filtered_ce:
            combined_filtered_list.append([i,filtered_pe[filtered_ce.index(i)]])

        for data in combined_filtered_list:
            
            if StrikeData.objects.filter(time=date_time_obj,strikePrice=combined_filtered_list[0]['strikePrice'],symbol=symbol).first() is None:
                strike_data = StrikeData.objects.create(symbol=symbol,time=date_time_obj, strikePrice=data, ce_coi=combined_filtered_list[0]["changeinOpenInterest"], ce_volume=combined_filtered_list[0]["totalTradedVolume"], ce_iv=combined_filtered_list[0]["impliedVolatility"], ce_tbq=combined_filtered_list[0]["totalBuyQuantity"], ce_tsq=combined_filtered_list[0]["totalSellQuantity"], pe_coi=combined_filtered_list[1]["changeinOpenInterest"], pe_volume=combined_filtered_list[1]["totalTradedVolume"], pe_iv=combined_filtered_list[1]["impliedVolatility"], pe_tbq=combined_filtered_list[1]["totalBuyQuantity"], pe_tsq=combined_filtered_list[1]["totalSellQuantity"])
                strike_data.save()
       
    except Exception as e:
        print(e)

    
def get_chart(request):
    strike_price_list = get_strike_price_list(request)
    # schedule.every(2).minutes.do(update_starike_data(request))
    return render(request, 'optionChart.html',{'strike_price_list': strike_price_list})
def get_strike(request):
    strike_price_list = get_strike_price_list(request)
    return JsonResponse(strike_price_list, safe=False)

url_oc      = "https://www.nseindia.com/option-chain"
url_bnf     = 'https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY'
url_nf      = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
url_indices = "https://www.nseindia.com/api/allIndices"

# Headers
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'}

sess = requests.Session()
cookies = dict()

# Local methods
def set_cookie():
    request = sess.get(url_oc, headers=headers, timeout=5)
    cookies = dict(request.cookies)


def get_option_data(symbol):
    
    print("-------------In get option data fnc-----------------------")
    set_cookie()
    if symbol=="NIFTY":
        response = sess.get(url_nf, headers=headers, timeout=5, cookies=cookies)
        if(response.status_code==401):
            set_cookie()
            response = sess.get(url_nf, headers=headers, timeout=5, cookies=cookies)
    else:
        response = sess.get(url_bnf, headers=headers, timeout=5, cookies=cookies)
        if(response.status_code==401):
            set_cookie()
            response = sess.get(url_bnf, headers=headers, timeout=5, cookies=cookies)
    return response

def save_option_data(request,page):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    today = datetime.date.today()
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday' ]
    day_name = datetime.date.today().strftime("%A")
    try:
        ti = datetime.datetime.now().strftime("%H:%M")
        
        if request.META['HTTP_HOST'] != '127.0.0.1:8000':
            request.META['HTTP_HOST'] = '127.0.0.1:8000'
            ti = datetime.datetime.now() + timedelta(hours=5, minutes=30)
        print(f"TI: {ti}")
        # if  ti > "09:30" and ti  < "16:30" and day_name in days_list:
        #     page = get_option_data(symbol)

    except Exception as e:
        print(e)
        context = {}
        # return JsonResponse(context, safe=False)
    try:
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
        cr1 = ce_df_sort[0] - 3
        cr2 = ce_df_sort[0] + 3
        pr1 = pe_df_sort[0] - 3
        pr2 = pe_df_sort[0] + 3
        ce_dt = ce_df[cr1:cr2]
        pe_dt = pe_df[pr1:pr2]
        if symbol == 'BANKNIFTY':
            multiplier = 15
        elif symbol == 'NIFTY':
            multiplier = 50
            
        print(f"CE Option Chain :\n {ce_dt}")
        print("-----------------------------------------------------")
        print(f"PE Option Chain :\n {pe_dt}")
        
        ce_dt['changeinOpenInterest'] = ce_dt['changeinOpenInterest'].astype(int) * multiplier
        pe_dt['changeinOpenInterest'] = pe_dt['changeinOpenInterest'].astype(int) * multiplier
        ce_dt['strikePrice'] = ce_dt['strikePrice'].astype(int)
        pe_dt['strikePrice'] = pe_dt['strikePrice'].astype(int)
        ce_changeInOpenInterest_sum = ce_dt['changeinOpenInterest'].sum()
        pe_changeInOpenInterest_sum = pe_dt['changeinOpenInterest'].sum()
        diff_changeinOpenInterest = pe_changeInOpenInterest_sum - ce_changeInOpenInterest_sum

        if diff_changeinOpenInterest > 2000000:
            call = "Buy Call Option"
        elif diff_changeinOpenInterest < -2000000:
            call = "Buy Put Option"
        else:
            call = "Neutral"

        date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
        ce_dt['timestamp'] = date_time_obj
        pe_dt['timestamp'] = date_time_obj
        dat_time_date = date_time_obj.date()

        if today == dat_time_date:
            if IntradayData.objects.filter(Q(time=date_time_obj)|Q(call=ce_changeInOpenInterest_sum, put=pe_changeInOpenInterest_sum, diff=diff_changeinOpenInterest)).first() is None:
                intraday_data = IntradayData.objects.create(symbol=symbol, call=ce_changeInOpenInterest_sum,
                                                            put=pe_changeInOpenInterest_sum,
                                                            diff=diff_changeinOpenInterest, time=date_time_obj,
                                                            signal=call)
                intraday_data.save()
    except Exception as e:
        print(e)


def api_get_data(request):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    print(symbol)
    today = datetime.date.today()
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday' ]
    day_name = datetime.date.today().strftime("%A")
    page = get_option_data(symbol)
    save_option_data(request,page)
    update_starike_data(request,page)
    # try:
    #     ti = datetime.datetime.now().strftime("%H:%M")
        
    #     if request.META['HTTP_HOST'] != '127.0.0.1:8000':
    #         request.META['HTTP_HOST'] = '127.0.0.1:8000'
    #         ti = datetime.datetime.now() + timedelta(hours=5, minutes=30)
    #     print(f"TI: {ti}")
    #     # if  ti > "09:30" and ti  < "16:30" and day_name in days_list:
    #     #     page = get_option_data(symbol)

    # except Exception as e:
    #     print(e)
    #     context = {}
    #     # return JsonResponse(context, safe=False)
    # try:
    #     dajs = json.loads(page.text)
    #     expiry_dt = dajs['records']['expiryDates'][0]

    #     ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt]

    #     pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt]

    #     ce_df = pd.DataFrame(ce_values, columns=['changeinOpenInterest', 'strikePrice'])
    #     pe_df = pd.DataFrame(pe_values, columns=['changeinOpenInterest', 'strikePrice'])


    #     ce_df['strikePrice'] = ce_df['strikePrice'].astype(int)
    #     index_quote_lastPrice = int(dajs['records']['underlyingValue'])
    #     ce_df_sort = ce_df.iloc[(ce_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
    #     pe_df_sort = pe_df.iloc[(pe_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
    #     cr1 = ce_df_sort[0] - 3
    #     cr2 = ce_df_sort[0] + 3
    #     pr1 = pe_df_sort[0] - 3
    #     pr2 = pe_df_sort[0] + 3
    #     ce_dt = ce_df[cr1:cr2]
    #     pe_dt = pe_df[pr1:pr2]
    #     if symbol == 'BANKNIFTY':
    #         multiplier = 15
    #     elif symbol == 'NIFTY':
    #         multiplier = 50
            
    #     print(f"CE Option Chain :\n {ce_dt}")
    #     print("-----------------------------------------------------")
    #     print(f"PE Option Chain :\n {pe_dt}")
        
    #     ce_dt['changeinOpenInterest'] = ce_dt['changeinOpenInterest'].astype(int) * multiplier
    #     pe_dt['changeinOpenInterest'] = pe_dt['changeinOpenInterest'].astype(int) * multiplier
    #     ce_dt['strikePrice'] = ce_dt['strikePrice'].astype(int)
    #     pe_dt['strikePrice'] = pe_dt['strikePrice'].astype(int)
    #     ce_changeInOpenInterest_sum = ce_dt['changeinOpenInterest'].sum()
    #     pe_changeInOpenInterest_sum = pe_dt['changeinOpenInterest'].sum()
    #     diff_changeinOpenInterest = pe_changeInOpenInterest_sum - ce_changeInOpenInterest_sum

    #     if diff_changeinOpenInterest > 2000000:
    #         call = "Buy Call Option"
    #     elif diff_changeinOpenInterest < -2000000:
    #         call = "Buy Put Option"
    #     else:
    #         call = "Neutral"

    #     date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
    #     ce_dt['timestamp'] = date_time_obj
    #     pe_dt['timestamp'] = date_time_obj
    #     dat_time_date = date_time_obj.date()

    #     if today == dat_time_date:
    #         if IntradayData.objects.filter(Q(time=date_time_obj)|Q(call=ce_changeInOpenInterest_sum, put=pe_changeInOpenInterest_sum, diff=diff_changeinOpenInterest)).first() is None:
    #             intraday_data = IntradayData.objects.create(symbol=symbol, call=ce_changeInOpenInterest_sum,
    #                                                         put=pe_changeInOpenInterest_sum,
    #                                                         diff=diff_changeinOpenInterest, time=date_time_obj,
    #                                                         signal=call)
    #             intraday_data.save()
    # except Exception as e:
    #     print(e)

    result = []
    intraday_data = IntradayData.objects.filter(symbol=symbol, time__date=today)
    for data in intraday_data:
        result.append({"symbol": data.symbol, "signal": data.signal,
               "diff": str(data.diff),
               "call": str(data.call),
               "put": str(data.put),
               "time": data.time
               })


    return JsonResponse(result, safe=False)

def get_strikePrice_data(request):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    strike_price = request.GET.get('strike_price')
    today = datetime.date.today()
    print(today)
    result = []
    strike_data = StrikeData.objects.filter(symbol=symbol,strikePrice=strike_price).order_by('-id')[:10][::-1]
    for data in strike_data:
        result.append({'time':data.time, 'strike':strike_price, 'ce_coi':str(data.ce_coi), 'ce_volume':str(data.ce_volume), 'ce_iv':str(data.ce_iv), 'ce_tbq':str(data.ce_tbq), 'ce_tsq':str(data.ce_tsq), 'pe_coi':str(data.pe_coi), 'pe_volume':str(data.pe_volume), 'pe_iv':str(data.pe_iv), 'pe_tbq':str(data.pe_tbq), 'pe_tsq':str(data.pe_tsq)})

    return result

def get_intraday_data(request):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    today = datetime.date.today()
    print(today)
    result = []
    intraday_data = IntradayData.objects.filter(symbol=symbol, time__date=today).order_by('-id')[:10][::-1]
    for data in intraday_data:
        result.append({'diff':data.diff,'time':data.time})

    return JsonResponse(result, safe=False)




#pe_values[0]['totalTradedVolume']pe_values[0]['impliedVolatility']pe_values[0]['totalBuyQuantity']pe_values[0]['totalSellQuantity']
def get_strike_price_data(request):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    strike_price = request.GET.get('strike_price')
    today = datetime.date.today()
    # page = get_option_data(symbol)

    # try:
    #     dajs = json.loads(page.text)
    #     expiry_dt = dajs['records']['expiryDates'][0]

    #     ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt ]

    #     pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt ]

    #     ce_df = pd.DataFrame(ce_values, columns=['strikePrice', 'changeinOpenInterest', 'totalTradedVolume', 'impliedVolatility', 'totalBuyQuantity', 'totalSellQuantity'])
    #     pe_df = pd.DataFrame(pe_values, columns=['strikePrice', 'changeinOpenInterest', 'totalTradedVolume', 'impliedVolatility', 'totalBuyQuantity', 'totalSellQuantity'])
    #     ce_df['strikePrice'] = ce_df['strikePrice'].astype(int)
    #     index_quote_lastPrice = int(dajs['records']['underlyingValue'])
    #     ce_df_sort = ce_df.iloc[(ce_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
    #     pe_df_sort = pe_df.iloc[(pe_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
    #     cr1 = ce_df_sort[0] - 3
    #     cr2 = ce_df_sort[0] + 4
    #     pr1 = pe_df_sort[0] - 3
    #     pr2 = pe_df_sort[0] + 4
    #     ce_dt = ce_df[cr1:cr2]
    #     pe_dt = pe_df[pr1:pr2]
    #     filtered_ce = [item for item in ce_values if item['strikePrice'] in ce_dt['strikePrice'].values]
    #     filtered_pe = [item for item in pe_values if item['strikePrice'] in pe_dt['strikePrice'].values]
    #     date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
    #     combined_filtered_list = []

    #     for i in filtered_ce:
    #         combined_filtered_list.append([i,filtered_pe[filtered_ce.index(i)]])

    #     for data in combined_filtered_list:
            
    #         if StrikeData.objects.filter(time=date_time_obj,strikePrice=combined_filtered_list[0]['strikePrice'],symbol=symbol).first() is None:
    #             strike_data = StrikeData.objects.create(symbol=symbol,time=date_time_obj, strikePrice=data, ce_coi=combined_filtered_list[0]["changeinOpenInterest"], ce_volume=combined_filtered_list[0]["totalTradedVolume"], ce_iv=combined_filtered_list[0]["impliedVolatility"], ce_tbq=combined_filtered_list[0]["totalBuyQuantity"], ce_tsq=combined_filtered_list[0]["totalSellQuantity"], pe_coi=combined_filtered_list[1]["changeinOpenInterest"], pe_volume=combined_filtered_list[1]["totalTradedVolume"], pe_iv=combined_filtered_list[1]["impliedVolatility"], pe_tbq=combined_filtered_list[1]["totalBuyQuantity"], pe_tsq=combined_filtered_list[1]["totalSellQuantity"])
    #             strike_data.save()

    # except Exception as e:
    #     print(e)

    result = get_strikePrice_data(request)
    

    return JsonResponse(result, safe=False)


def get_strike_price_list(request):
    symbol = request.GET.get('symbol') or "NIFTY"
    page = get_option_data(symbol)
    try:
        dajs = json.loads(page.text)
        get_strike_price_list = dajs['records']['strikePrices']
        return get_strike_price_list
    except Exception as e:
        print(e)
        return None
    

