from django.db import models


class CEStockData(models.Model):
    changeinOpenInterest = models.IntegerField(null=True, blank=True)
    strikePrice = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.strikePrice)

    class Meta:
        db_table = 'ce_stock_data'

class PEStockData(models.Model):
    changeinOpenInterest = models.IntegerField(null=True, blank=True)
    strikePrice = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.strikePrice)

    class Meta:
        db_table = 'pe_stock_data'

class IntradayData(models.Model):
    call = models.IntegerField(null=True, blank=True) #sum of all change in open interest for call option
    put = models.IntegerField(null=True, blank=True)  # sum of all change in open interest for put option
    diff = models.IntegerField(null=True, blank=True) # diff of call and put
    time = models.DateTimeField(blank=True, null=True)
    signal = models.CharField(max_length=50, blank=False, null=True)

    def __str__(self):
        return self.signal

    class Meta:
        db_table = 'intraday_data'