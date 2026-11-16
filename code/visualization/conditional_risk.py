from pathlib import Path
import sys
import numpy as np,pandas as pd,geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PIL import Image
import fitz
R=Path(__file__).resolve().parents[2]
O=R/'build/conditional_risk'
for folder in ['figures','qa']: (O/folder).mkdir(parents=True,exist_ok=True)
S=R/'source_data/main_figures/conditional_risk';d=pd.read_csv(S/'risk.csv');ledger=pd.read_csv(S/'risk_background.csv');s=pd.read_csv(S/'risk_summary.csv').set_index('crop')
C=['MAIZE','RICE','SOY','WHEAT'];names=['Maize','Rice','Soybean','Wheat'];colors=['#0072B2','#009E73','#CC79A7','#D55E00']
world=gpd.read_file('zip://'+str(R/'source_data/basemap/ne_50m_admin_0_countries.zip'));world=world[world.ADM0_A3.ne('ATA')]
plt.rcParams.update({'font.family':'Arial','font.size':7,'axes.titlesize':7.8,'axes.labelsize':7,'xtick.labelsize':6,'ytick.labelsize':6,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
H=205.0;H0=205.0
from_top=lambda y:1-(1-y)*H0/H
from_bottom=lambda y:y*H0/H
fig=plt.figure(figsize=(180/25.4,H/25.4))
maps=fig.add_gridspec(2,2,left=.04,right=.98,bottom=from_top(.50),top=from_top(.90),wspace=.08,hspace=.21)
bottom=fig.add_gridspec(1,2,left=.11,right=.98,bottom=from_bottom(.09),top=from_bottom(.345),wspace=.70)
axs=np.array([[fig.add_subplot(maps[i,j]) for j in range(2)] for i in range(2)]+[[fig.add_subplot(bottom[0,j]) for j in range(2)]])
fig.suptitle('2026–2027 El Niño: conditional 2027 harvest risks',fontsize=8,fontweight='bold',y=from_top(.985))
fig.text(.5,from_top(.955),'ENSO outlook available 8 November 2026',ha='center',fontsize=6.5)
mapjoins=[]
for ax,crop,name,label in zip(axs[:2].flat,C,names,'abcd'):
    z=world.merge(ledger[ledger.crop.eq(crop)][['iso3','background_class']],left_on='ADM0_A3',right_on='iso3',how='left');g=d[d.crop.eq(crop)]
    z=z.merge(g[['iso3','map_conservative_visual_value_pp','probability_allocation_incomplete','mix_direction']],on='iso3',how='left')
    z.plot(ax=ax,color='white',edgecolor='#b8b8b8',linewidth=.15,aspect=None)
    for state,col in {'OUTSIDE_HORIZON':'#d1d1d1','INSUFFICIENT_DATA':'#858585','OTHER_EXCLUDED':'#f0f0f0'}.items():
        zz=z[z.background_class.eq(state)]
        if len(zz):zz.plot(ax=ax,color=col,edgecolor='white',linewidth=.15,aspect=None)
    valid=z[z.map_conservative_visual_value_pp.notna()];valid.plot(ax=ax,column='map_conservative_visual_value_pp',vmin=-25,vmax=25,cmap='RdBu_r',edgecolor='.45',linewidth=.15,aspect=None)
    points=valid[valid.mix_direction.eq('HIGHER')].geometry.representative_point();ax.scatter(points.x,points.y,marker='^',s=3,color='.2',linewidths=0)
    points=valid[valid.mix_direction.eq('LOWER')].geometry.representative_point();ax.scatter(points.x,points.y,marker='v',s=3,color='.2',linewidths=0)
    points=valid[valid.mix_direction.eq('UNCHANGED') & ~valid.probability_allocation_incomplete.fillna(False)].geometry.representative_point();ax.scatter(points.x,points.y,marker='o',s=5,facecolors='none',edgecolors='.25',linewidths=.45)
    points=valid[valid.probability_allocation_incomplete.fillna(False)].geometry.representative_point();ax.scatter(points.x,points.y,marker='D',s=13,facecolors='none',edgecolors='.15',linewidths=.5)
    ax.set(xlim=(-180,180),ylim=(-58,85));ax.set_aspect('auto');ax.set_xticks([]);ax.set_yticks([])
    ax.set_title(f'{label}  {name} · {len(g)} systems\nReference world production: {g.WorldQ.sum():.1f}%',loc='left',fontweight='bold',pad=6,fontsize=7.4)
    for sp in ax.spines.values():sp.set_visible(False)
    mapjoins.extend(dict(system_id=r.system_id,crop=crop) for r in g.itertuples() if r.iso3 in set(world.ADM0_A3))
pd.DataFrame(mapjoins).to_csv(O/'figures/MAPPED_200_IDS.csv',index=False)
coverage_handles=[Patch(facecolor='#d1d1d1',label='Beyond outlook period'),Patch(facecolor='#858585',label='Insufficient data'),Patch(facecolor='#f0f0f0',label='Other excluded'),Patch(facecolor='white',edgecolor='.6',label='No candidate')]
risk_handles=[Line2D([],[],marker='^',ls='',ms=2.5,color='.2',label='Higher risk'),Line2D([],[],marker='v',ls='',ms=2.5,color='.2',label='Lower risk'),Line2D([],[],marker='D',ls='',ms=3,mfc='none',color='.2',label='Phase-probability bounds'),Line2D([],[],marker='o',ls='',ms=3,mfc='none',color='.25',label='Zero estimated change')]
fig.text(.09,from_top(.477),'Coverage',ha='left',va='center',fontsize=5.4,fontweight='bold')
fig.legend(handles=coverage_handles,loc='center',bbox_to_anchor=(.57,from_top(.477)),ncol=4,frameon=False,fontsize=5.2,columnspacing=.9,handlelength=1.1)
fig.text(.09,from_top(.455),'Risk marks',ha='left',va='center',fontsize=5.4,fontweight='bold')
fig.legend(handles=risk_handles,loc='center',bbox_to_anchor=(.55,from_top(.455)),ncol=4,frameon=False,fontsize=5.2,columnspacing=1.1,handlelength=1.1)
cax=fig.add_axes([.24,from_top(.43),.52,.012*H0/H]);fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(-25,25),cmap='RdBu_r'),cax=cax,orientation='horizontal');cax.tick_params(labelsize=5.5,pad=4);cax.set_xlabel('Change in severe-low-yield probability (percentage points)',fontsize=6,labelpad=1)

# All 200 frozen visual values, accompanied by their original allocation bounds.
ax=axs[2,0];marks=[];boxrows=[];weighted=[]
for crop,name,color,y in zip(C,names,colors,[6,4,2,0]):
    g=d[d.crop.eq(crop)].sort_values('system_id');v=g.map_conservative_visual_value_pp.to_numpy()
    lo=g.MIX_severe10_change_lo_pp.to_numpy();hi=g.MIX_severe10_change_hi_pp.to_numpy()
    q=np.quantile(v,[0,.25,.5,.75,1]);boxrows.append(dict(crop=crop,n=len(g),minimum=q[0],q25=q[1],median=q[2],q75=q[3],maximum=q[4]))
    ax.bxp([dict(med=q[2],q1=q[1],q3=q[3],whislo=q[0],whishi=q[4],fliers=[])],positions=[y],vert=False,widths=.53,showfliers=False,patch_artist=True,boxprops=dict(facecolor=color+'20',edgecolor=color,linewidth=.7),medianprops=dict(color=color,linewidth=1.2),whiskerprops=dict(color=color,linewidth=.6),capprops=dict(color=color,linewidth=.6),manage_ticks=False)
    offsets=np.linspace(-.21,.21,len(g));offsets=offsets[np.random.default_rng(42).permutation(len(g))]
    for r,yy in zip(g.itertuples(),y+offsets):
        ax.plot([r.MIX_severe10_change_lo_pp,r.MIX_severe10_change_hi_pp],[yy,yy],color=color,alpha=.45,lw=.55)
        ax.scatter(r.map_conservative_visual_value_pp,yy,s=4,color=color,alpha=.60,zorder=3)
        marks.append(dict(system_id=r.system_id,crop=crop,x_visual=r.map_conservative_visual_value_pp,lo=r.MIX_severe10_change_lo_pp,hi=r.MIX_severe10_change_hi_pp,y=yy))
    w=s.loc[crop];wy=y-.65
    ax.plot([w.weighted_mean_lo_pp,w.weighted_mean_hi_pp],[wy,wy],color='.15',lw=1.1)
    ax.scatter([w.weighted_mean_lo_pp,w.weighted_mean_hi_pp],[wy,wy],marker='D',s=13,facecolors='white',edgecolors='.15',linewidths=.7,zorder=4)
    weighted.append(dict(crop=crop,lo=w.weighted_mean_lo_pp,hi=w.weighted_mean_hi_pp,worldQ=w.fixed_worldQ_pct))
ax.axvline(0,color='.65',lw=.7,zorder=0)
ax.set(yticks=[6,4,2,0],yticklabels=[f'{n} ({int(s.loc[c,"systems"])})' for c,n in zip(C,names)],xlabel='Severe-low-yield probability change (pp)',xlim=(-26,26),ylim=(-1.3,8.0))
ax.tick_params(axis='y',length=0,pad=3,labelsize=6)
ax.set_title('e  System risks and production weighting',loc='left',fontweight='bold',pad=6)
ax.legend(handles=[Line2D([],[],marker='o',ls='',color='.45',ms=2.5,label='Country–crop systems'),Line2D([],[],marker='D',ls='',mfc='white',mec='.15',ms=3,label='Production-weighted risk change')],loc='upper right',frameon=False,fontsize=5.2,handletextpad=.5,borderpad=.1,labelspacing=.3)
pd.DataFrame(marks).to_csv(O/'figures/BOX_200_MARKS.csv',index=False)
pd.DataFrame(boxrows).to_csv(O/'figures/BOX_DISPLAY_SUMMARIES.csv',index=False)
pd.DataFrame(weighted).to_csv(O/'figures/WEIGHTED_BOUND_MARKS.csv',index=False)
examples=['ARG×MAIZE','ZAF×MAIZE','BRA×SOY','AUS×RICE','IDN×RICE','COL×RICE','USA×WHEAT','EGY×WHEAT'];ex=d.set_index('system_id').loc[examples].reset_index();ex.to_csv(O/'figures/EXAMPLE_SOURCE.csv',index=False)
labels=['Argentina · maize','South Africa · maize','Brazil · soybean','Australia · rice','Indonesia · rice','Colombia · rice','United States · wheat','Egypt · wheat'];ax=axs[2,1];drawrules=[]
for i,r in enumerate(ex.itertuples()):
    exact=abs(r.event_mix_risk_hi_pct-r.event_mix_risk_lo_pct)<1e-9
    drawrules.append(dict(system_id=r.system_id,baseline=r.historical_severe_risk_pct,scenario_lo=r.event_mix_risk_lo_pct,scenario_hi=r.event_mix_risk_hi_pct,connector='grey dashed: baseline to lower endpoint',blue_mark='filled circle' if exact else 'capped allocation interval'))
    ax.plot([r.historical_severe_risk_pct,r.event_mix_risk_lo_pct],[i,i],color='.65',lw=.7,ls='--',zorder=1)
    if exact:
        ax.scatter(r.event_mix_risk_lo_pct,i,s=12,marker='o',color='#0072B2',zorder=4)
    else:
        ax.plot([r.event_mix_risk_lo_pct,r.event_mix_risk_hi_pct],[i,i],color='#0072B2',lw=1.4,marker='|',markersize=6,markeredgewidth=1.1)
    ax.scatter(r.historical_severe_risk_pct,i,s=16,facecolors='white',edgecolors='.2',linewidths=.7,zorder=3)
ax.set(yticks=range(len(ex)),yticklabels=labels,xlabel='Severe-low-yield probability (%)',xlim=(-2,45),ylim=(-.6,8.6));ax.tick_params(axis='y',labelsize=5.8)
ax.set_title('f  Historical and ENSO-scenario risk',loc='left',fontweight='bold',pad=6)
ax.legend(handles=[Line2D([],[],marker='o',ls='',mfc='white',mec='.2',ms=3,label='Historical baseline'),Line2D([],[],marker='o',ls='',color='#0072B2',ms=3,label='ENSO scenario'),Line2D([],[],color='#0072B2',lw=1.4,marker='|',ms=5,label='Scenario allocation bounds'),Line2D([],[],color='.65',lw=.7,ls='--',label='Baseline–scenario link')],loc='upper right',frameon=False,fontsize=5.3)
pd.DataFrame(drawrules).to_csv(O/'figures/EXAMPLE_DRAW_RULES.csv',index=False)
fig.canvas.draw()
fig.savefig(O/'figures/Figure_6.png',dpi=300)
fig.savefig(O/'figures/Figure_6.pdf')
fig.savefig(O/'figures/Figure_6.svg')
Image.open(O/'figures/Figure_6.png').convert('L').save(O/'qa/Figure_6_grayscale.png')
with fitz.open(O/'figures/Figure_6.pdf') as doc:doc[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(str(O/'qa/Figure_6_PDF_preview.png'))
print('Revised figure6: four frozen maps, all200 distribution entries, original eight examples')
