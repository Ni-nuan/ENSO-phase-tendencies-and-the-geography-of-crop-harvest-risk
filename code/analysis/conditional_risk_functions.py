"""Original trend reference, weighted summaries and phase shrinkage functions.
Callers must supply the dated outlook, qualified histories and allocation constraints.
This module does not retrieve current outlooks or rebuild system eligibility.
"""
import numpy as np

def ref(g,target,cutoff):
    h=g[g.harvest_year.between(cutoff-9,cutoff)]
    if len(h)<8:return np.nan,h
    val=np.linalg.lstsq(np.column_stack([np.ones(len(h)),h.harvest_year.to_numpy()-target]),h.yield_t_ha.to_numpy(),rcond=None)[0][0]
    return val if val>0 else np.nan,h

def summary(v,w,terc):
    order=np.argsort(v);vv=v[order];cw=np.cumsum(w[order]/w.sum())
    return dict(center_pct=float(np.dot(v,w)),q10_pct=float(vv[min(np.searchsorted(cw,.1),len(vv)-1)]),q90_pct=float(vv[min(np.searchsorted(cw,.9),len(vv)-1)]),p_negative=float(w[v<=0].sum()),p_severe10=float(w[v<=-10].sum()),p_tercile=float(w[v<=terc].sum()))

def weights(v,ph,alpha):
    return {s:((ph==s).astype(float)+alpha/len(v))/((ph==s).sum()+alpha) for s in ['EN','LN','NEUTRAL']}
