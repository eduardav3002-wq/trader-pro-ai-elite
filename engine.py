import numpy as np
import pandas as pd

REQUIRED = ('open','high','low','close')

def demo_data(n=180):
    rng = np.random.default_rng(27)
    close = 128000 + np.cumsum(rng.normal(0, 18, n))
    opening = np.r_[close[0], close[:-1]]
    return pd.DataFrame({'datetime':pd.date_range('2026-11-20 09:00',periods=n,freq='5min'), 'open':opening, 'high':np.maximum(opening,close)+rng.uniform(2,13,n), 'low':np.minimum(opening,close)-rng.uniform(2,13,n), 'close':close})

def analyze(df):
    df = df.copy()
    if not set(REQUIRED).issubset(df.columns):
        raise ValueError('O CSV precisa das colunas open, high, low, close.')
    for c in REQUIRED:
        df[c] = pd.to_numeric(df[c],errors='coerce')
    df = df.dropna(subset=list(REQUIRED)).reset_index(drop=True)
    if len(df)<35: raise ValueError('São necessários pelo menos 35 candles.')
    if ((df.high < df[['open','close','low']].max(axis=1)) | (df.low > df[['open','close']].min(axis=1))).any():
        raise ValueError('Alguns candles têm máximas ou mínimas inconsistentes.')
    df['ema9']=df.close.ewm(span=9,adjust=False).mean()
    df['ema21']=df.close.ewm(span=21,adjust=False).mean()
    d=df.close.diff()
    gains=d.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    losses=(-d.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rs=gains/losses.replace(0,np.nan)
    df['rsi']=(100-100/(1+rs)).where(losses.ne(0),100).fillna(50)
    prev=df.close.shift()
    tr=pd.concat([df.high-df.low,(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    df['atr']=tr.rolling(14,min_periods=14).mean()
    spread=(df.ema9-df.ema21).abs()
    sideways=(spread < df.atr*0.20)
    df['trend']=np.select([df.ema9>df.ema21,df.ema9<df.ema21],['ALTA','BAIXA'],default='NEUTRA')
    df['condition']=np.where(sideways,'POSSÍVEL LATERALIZAÇÃO','MOVIMENTO')
    buy=(df.ema9>df.ema21)&df.rsi.between(52,67)&(~sideways)
    sell=(df.ema9<df.ema21)&df.rsi.between(33,48)&(~sideways)
    df['signal']=np.select([buy,sell],['COMPRA','VENDA'],default='AGUARDAR')
    df.loc[:33,'signal']='AGUARDAR'  # warm-up conservador
    df['stop']=np.select([df.signal.eq('COMPRA'),df.signal.eq('VENDA')],[df.close-1.5*df.atr,df.close+1.5*df.atr],default=np.nan)
    df['target']=np.select([df.signal.eq('COMPRA'),df.signal.eq('VENDA')],[df.close+2*df.atr,df.close-2*df.atr],default=np.nan)
    return df
