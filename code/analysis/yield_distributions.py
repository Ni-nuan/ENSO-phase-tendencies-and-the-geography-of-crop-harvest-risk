"""Original historical distribution functions; caller supplies qualified records."""
import numpy as np
import pandas as pd

def ids(s):return set(str(s).split('|')) if pd.notna(s) and str(s) else set()

def rho(x,y):
 z=pd.DataFrame({'x':x,'y':y}).dropna()
 return z.x.rank().corr(z.y.rank()) if len(z)>=3 and z.x.nunique()>1 and z.y.nunique()>1 else np.nan

def metrics(s):
 y=np.asarray(s.dropna(),dtype=float);n=len(y)
 r={'n':n,'mean':np.mean(y) if n else np.nan,'median':np.median(y) if n else np.nan,'SD':np.std(y,ddof=1) if n>=2 else np.nan,'min':np.min(y) if n else np.nan,'max':np.max(y) if n else np.nan}
 for name,p in [('q25',.25),('q75',.75),('q10',.10),('q90',.90)]:r[name]=np.quantile(y,p,method='linear') if n>=(20 if name in ['q10','q90'] else 8) else np.nan
 r['IQR']=r['q75']-r['q25']
 for t in [5,10,15]:
  for k,mask in [('tail',y<=-t),('upper',y>=t)]:r[f'{k}{t}_N']=int(mask.sum());r[f'{k}{t}']=float(mask.mean()) if n else np.nan
 r['negative_N']=int(sum(y<0));r['negative_fraction']=np.mean(y<0) if n else np.nan
 r['clear_direction_changes']=int(np.sum(np.sign(y[1:])!=np.sign(y[:-1]))) if n>=2 else 0
 return r
