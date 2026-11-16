"""Original retrospective event-history metrics, not prospective forecast certification."""
import re
import numpy as np
import pandas as pd

def years(s):return [int(y) for y in re.findall(r'\d{4}',str(s))]

def ids(s):return set(re.findall(r'(?:EN|LN)_\d{6}_\d{6}',str(s)))

def rho(x,y):
 x=np.asarray(x,float);y=np.asarray(y,float);ok=np.isfinite(x)&np.isfinite(y);x=x[ok];y=y[ok]
 return pd.Series(x).rank().corr(pd.Series(y).rank()) if len(x)>1 and np.ptp(x)>0 and np.ptp(y)>0 else np.nan

def segments(y):
 z=sorted(set(y));return sum(i==0 or v!=z[i-1]+1 for i,v in enumerate(z))

def metrics(pred,obs,q=None):
 p=np.asarray(pred,float);y=np.asarray(obs,float);q=np.ones(len(y)) if q is None else np.asarray(q,float)
 ok=np.isfinite(p)&np.isfinite(y)&np.isfinite(q)&(q>=0);p=p[ok];y=y[ok];q=q[ok]
 clear=(abs(p)>=2)&(abs(y)>=2);same=(np.sign(p)==np.sign(y))&(p!=0)&(y!=0);cs=clear&same
 den=q.sum()
 return dict(N=len(y),zero_sign_same_fraction=float(np.average(same,weights=q)) if den else np.nan,
  explicit_zero_N=int(((p==0)|(y==0)).sum()),clear_N=int(clear.sum()),clear_same_N=int(cs.sum()),clear_opposite_N=int((clear&~same).sum()),uncertain_N=int((~clear).sum()),
  clear_same_fraction=float(q[cs].sum()/q[clear].sum()) if q[clear].sum() else np.nan,
  clear_same_of_all=float(q[cs].sum()/den) if den else np.nan,clear_fraction=float(q[clear].sum()/den) if den else np.nan,
  median_signed_error_pp=float(np.median(p-y)) if len(y) else np.nan,median_absolute_error_pp=float(np.median(abs(p-y))) if len(y) else np.nan,
  mean_absolute_error_pp=float(np.average(abs(p-y),weights=q)) if den else np.nan)
