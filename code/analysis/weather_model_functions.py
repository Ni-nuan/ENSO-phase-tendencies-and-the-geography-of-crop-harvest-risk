"""Original system/trend and forest fitting functions; model refitting is not run on import."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
WEATHER=['P','T','VPD','SM','SW']
CONTEXT=['P_background','T_background','irrigation_share','season_length','T_background_missing']
PARAMS=dict(n_estimators=100,max_depth=5,min_samples_leaf=20,max_features=1.0,random_state=20261108,n_jobs=2)

def nuisance_fit(g,target):
 records=[];out=np.empty(len(g))
 for sid,inds in g.groupby('system_id').indices.items():
  t=g.harvest_year.to_numpy()[inds];y=g[target].to_numpy()[inds];mean=t.mean();A=np.column_stack([np.ones(len(t)),t-mean]);b=np.linalg.lstsq(A,y,rcond=None)[0]
  out[inds]=A@b;records.append(dict(system_id=sid,mean_year=mean,intercept=b[0],trend=b[1],N=len(t)))
 return out,pd.DataFrame(records)

def fit(g,target='Y',weather=WEATHER):
 fills={}
 for c in CONTEXT:
  fills[c]=float(g[['system_id',c]].drop_duplicates('system_id')[c].median())
  assert np.isfinite(fills[c]),c
  g[c]=g[c].fillna(fills[c])
 base,nu=nuisance_fit(g,target);counts=g.system_id.value_counts();w=g.system_id.map(lambda s:len(g)/(len(counts)*counts[s])).to_numpy()
 model=RandomForestRegressor(**PARAMS).fit(g[weather+CONTEXT],g[target]-base,sample_weight=w)
 model.static_fill_=fills
 return model,nu,base,w

def nu_predict(g,nu):
 merged=g[['system_id','harvest_year']].merge(nu,on='system_id',validate='many_to_one',how='left');assert merged.intercept.notna().all()
 return (merged.intercept+merged.trend*(merged.harvest_year-merged.mean_year)).to_numpy()

from pathlib import Path
import os,time
O=Path(os.environ.get("ENSO_OUTPUT_ROOT",Path(__file__).resolve().parents[2]/"build/weather_model"))
META=['system_id','crop','harvest_year','calendar_class','WorldQ','Y','Y_LOESS','physical_event_ids','cluster','membership_retention']

def explain(g,model,nu,base,label,features,background=None):
 import shap
 import shap
 import shap
 start=time.time();X=g[features]
 if background is None: ex=shap.TreeExplainer(model,feature_perturbation='tree_path_dependent')
 else:ex=shap.TreeExplainer(model,data=background[features],feature_perturbation='interventional')
 sv=ex.shap_values(X,check_additivity=False);expected=np.asarray(ex.expected_value).item()
 pred=model.predict(X);error=np.max(np.abs(sv.sum(axis=1)+expected-pred));assert error<1e-5,(label,error)
 result=g[META+WEATHER+CONTEXT].copy();result['variant']=label;result['prediction_residual']=pred;result['prediction_Y']=pred+base;result['expected_value']=expected;result['system_trend_reference']=base
 for i,f in enumerate(features):result['shap_'+f]=sv[:,i]
 for f in WEATHER:
  if 'shap_'+f not in result:result['shap_'+f]=0.0
 O.mkdir(parents=True,exist_ok=True)
 result.to_parquet(O/f'ANNUAL_SHAP_{label}_{g.crop.iloc[0]}.parquet',index=False)
 print(label,g.crop.iloc[0],len(g),'seconds',round(time.time()-start,1),'reconstruction',error,flush=True)
 return result,error
