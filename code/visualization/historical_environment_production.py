"""Render the stored figure-level results without fitting models."""
from pathlib import Path
import sys
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import fitz
R=Path(__file__).resolve().parents[2]
O=R/'build/historical_environment_production'
for folder in ['figures','qa']: (O/folder).mkdir(parents=True,exist_ok=True)
S=R/'source_data/main_figures/historical_environment_production';read=lambda k:pd.read_csv(S/(k+'.csv'))
C=['MAIZE','RICE','SOY','WHEAT'];names=['Maize','Rice','Soybean','Wheat'];factors=['P','T','VPD','SM','SW']
factor_names=['Precipitation','Temperature','Atmospheric\ndryness (VPD)','Soil\nmoisture','Shortwave\nradiation']
cropcolors=['#0072B2','#009E73','#CC79A7','#D55E00'];markers=['o','s','^','D'];envcolors=['#0072B2','#D55E00']
models={'Observed yield':('#0072B2','o'),'Full historical model':('#009E73','s'),'Five-weather contribution':('#CC79A7','^')}
plt.rcParams.update({'font.family':'Arial','font.size':7,'axes.titlesize':7.8,'axes.labelsize':7,'xtick.labelsize':6,'ytick.labelsize':6,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
def title(ax,label,text):ax.set_title(label+'  '+text,loc='left',fontweight='bold',pad=6)
def grid(rows=2,height=6.3):
    fig,axs=plt.subplots(rows,2,figsize=(180/25.4,height));fig.subplots_adjust(left=.115,right=.98,bottom=.10,top=.95,wspace=.34,hspace=.56);return fig,axs
def save(fig,axes,n,letters=None):
    axes=list(np.asarray(axes,dtype=object).flat);fig.canvas.draw()
    groups=dict(row_groups=[['a','b'],['d','e'],['g','h'],['j','k']],column_groups=[['a','d','g','j'],['b','e','h','k'],['c','f','i','l']]) if n==1 else {}

    import json
    manifest=[]
    for letter,ax in zip(list(letters or 'abcdefghijkl'[:len(axes)]),axes):
        manifest.append(dict(panel=letter,xlabel=ax.get_xlabel(),ylabel=ax.get_ylabel(),xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),scatters=[c.get_offsets().filled(float('nan')).tolist() if hasattr(c.get_offsets(),'filled') else c.get_offsets().tolist() for c in ax.collections if hasattr(c,'get_offsets') and c.get_offsets().shape[0]>1],scatter_sizes=[c.get_sizes().tolist() for c in ax.collections if hasattr(c,'get_offsets') and c.get_offsets().shape[0]>1 and hasattr(c,'get_sizes')],images=[im.get_array().tolist() for im in ax.images],lines=[dict(x=list(map(float,l.get_xdata())),y=list(map(float,l.get_ydata()))) for l in ax.lines],bars=[dict(x=p.get_x(),y=p.get_y(),width=p.get_width(),height=p.get_height()) for p in ax.patches if isinstance(p,Rectangle)]))
    (O/f'qa/FIGURE_{n}_ARTISTS.json').write_text(json.dumps(manifest,indent=2,default=lambda x:x.item()),encoding='utf8')
    fig.savefig(O/f'figures/Figure_{n}.png',dpi=300)
    fig.savefig(O/f'figures/Figure_{n}.pdf')
    fig.savefig(O/f'figures/Figure_{n}.svg')
    Image.open(O/f'figures/Figure_{n}.png').convert('L').save(O/f'qa/Figure_{n}_grayscale.png')
    with fitz.open(O/f'figures/Figure_{n}.pdf') as doc:doc[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(str(O/f'qa/Figure_{n}_PDF_preview.png'))
    plt.close(fig)
def boxes(ax,arrays,labels,colors,horizontal=False,show_points=False):
    for i,(values,color) in enumerate(zip(arrays,colors)):
        values=np.asarray(values,dtype=float);values=values[np.isfinite(values)]
        ax.boxplot([values],positions=[i],orientation='horizontal' if horizontal else 'vertical',widths=.42,whis=(0,100),showfliers=False,showmeans=True,patch_artist=True,
            boxprops=dict(facecolor=color,alpha=.16,edgecolor=color),medianprops=dict(color=color,linewidth=1.5),whiskerprops=dict(color=color,linewidth=.8),capprops=dict(color=color,linewidth=.8),meanprops=dict(marker='D',markersize=4,markerfacecolor=color,markeredgecolor='white',markeredgewidth=.4))
        if show_points:
            jitter=np.linspace(-.12,.12,len(values))
            marker=markers[i] if len(arrays)==4 else ['o','s'][i]
            if horizontal:ax.scatter(values,i+jitter,s=6,color=color,marker=marker,alpha=.42,zorder=3,edgecolors='none')
            else:ax.scatter(i+jitter,values,s=6,color=color,marker=marker,alpha=.42,zorder=3,edgecolors='none')
    if horizontal:ax.set(yticks=range(len(labels)),yticklabels=labels)
    else:ax.set(xticks=range(len(labels)),xticklabels=labels)

phase=read("phase_annual")

# Fig2: readable summaries of the exact former points; all underlying rows retained.
fig,axs=grid(2,150/25.4);a=read('Figure2_b');x=np.arange(len(a));labels=a.crop.map(dict(zip(C,names)))+' '+a.phase.map({'EN':'El Niño','LN':'La Niña'})
ax=axs[0,0]
for i,r in enumerate(a.itertuples()):
    j=C.index(r.crop);xx=[100*r.blind_zero_sign_same_fraction_event_mean,100*r.phase_zero_sign_same_fraction_event_mean]
    ax.plot(xx,[i,i],c='.7',lw=.65,zorder=1);ax.plot(xx[0],i,'o',mfc='white',mec='.4',ms=3.6,zorder=2);ax.plot(xx[1],i,marker=markers[j],c=cropcolors[j],ms=3.8,zorder=3)
ax.invert_yaxis()
ax.set(yticks=x,yticklabels=labels,xlabel='Yield-direction agreement (%)');ax.legend(handles=[plt.Line2D([],[],marker='o',ls='',mfc='white',mec='.4',ms=3.6,label='All other events'),plt.Line2D([],[],marker='o',ls='',color='.25',ms=3.6,label='Same-phase events')],fontsize=5.6,frameon=False,loc='upper left',bbox_to_anchor=(0,-.21),ncol=2);title(ax,'a','Direction agreement across ENSO events');ax.set(xlim=(0,100),xticks=[0,25,50,75,100]);ax.text(.035,.98,'Same-phase: 46.8–54.7%\nAll-event: 42.1–49.2%',transform=ax.transAxes,va='top',fontsize=5.7,linespacing=1.25)
ex=read('exceptions');ex=ex[ex.material_tendency&ex.all_delete_sign&ex.all_delete_eligible];ax=axs[0,1];barrows=[]
for i,(sign,label) in enumerate([(1,'Higher long-term\nmean yield'),(-1,'Lower long-term\nmean yield')]):
    g=ex[ex.delta_mean*sign>0];opposite=int(g.opposite_event_n.gt(0).sum());none=len(g)-opposite
    ax.barh(i,opposite,color='#D55E00',height=.46,label='Opposite event present' if i==0 else None);ax.barh(i,none,left=opposite,color='#d7d7d7',height=.46,label='No opposite event' if i==0 else None)
    ax.text(opposite/2,i,str(opposite),ha='center',va='center',fontsize=7,color='white');ax.text(opposite+none/2,i,str(none),ha='center',va='center',fontsize=7)
    barrows.append(dict(direction=label.replace('\n',' '),opposite=opposite,no_opposite=none,total=len(g)))
ax.set(yticks=[0,1],yticklabels=['Higher mean\nyield','Lower mean\nyield'],xlabel='Stable country–crop–phase histories',xlim=(0,165),ylim=(-.6,2.0));ax.legend(fontsize=5.8,frameon=False,loc='upper left');title(ax,'b','Opposite events: 213 of 276 histories')
g=read('phase');counts=np.zeros((3,3),dtype=int)
for r in g.itertuples():counts[int(np.sign(r.delta_tail10_LN))+1,int(np.sign(r.delta_tail10_EN))+1]+=1
ax=axs[1,0];ax.imshow(counts,cmap='Blues',vmin=0,vmax=counts.max(),aspect='auto',origin='lower');ax.set(xticks=range(3),yticks=range(3),xticklabels=['Lower','Same','Higher'],yticklabels=['Lower','Same','Higher'],xlabel='El Niño low-yield frequency\nrelative to neutral years',ylabel='La Niña low-yield frequency\nrelative to neutral years')
for i in range(3):
    for j in range(3):ax.text(j,i,str(counts[i,j]),ha='center',va='center',fontsize=10,color='white' if counts[i,j]>.6*counts.max() else '.15')
ax.add_patch(Rectangle((1.5,1.5),1,1,fill=False,edgecolor='#D55E00',linewidth=2));title(ax,'c','Severe low yield in both phases')
ax=axs[1,1];r=read('Figure2_d_upper');arrays=[r.loc[r.crop.eq(c),'phase_map_rho'].dropna().values for c in C]
boxes(ax,arrays,[f'{n} (n={len(v)})' for n,v in zip(names,arrays)],cropcolors,horizontal=True,show_points=True);ax.axvline(0,c='.5',lw=.6);ax.set(xlabel='Yield-ranking similarity\nwith other same-phase events',xlim=(-1,1));title(ax,'d','Yield geography differs between events')
save(fig,axs,2)

# Fig3: show actual country distributions before model-contribution summaries.
fig,axs=grid(4,225/25.4);fig.subplots_adjust(hspace=.61);d=phase[(phase.crop=='SOY')&phase.phase.eq('EN')&phase.main_eligible]
for j,(field,ylab) in enumerate([('delta_mean','Yield difference from neutral years (pp)'),('delta_tail10','Severe-low-yield frequency\nchange from neutral years (pp)')]):
    arrays=[d.loc[d.cluster.eq(k),field].values for k in [2,3]];ax=axs[0,j];boxes(ax,arrays,['Cooler / longer\n11 systems','Warmer\n23 systems'],envcolors,show_points=True);ax.axhline(0,c='.5',lw=.6);ax.set_ylabel(ylab);title(ax,'ab'[j],['Soybean: different yield distributions','Soybean: contrasting low-yield tails'][j])
ax=axs[1,0];d=read('strength_systems');d=d[(d.crop=='WHEAT')&d.phase.eq('LN')&d.both_strength_supported];arrays=[d.loc[d.cluster.eq(k),'strong_minus_ordinary_mean'].values for k in [1,2]]
boxes(ax,arrays,['Cooler / less\nirrigated (39)','Warmer /\ndrier (29)'],envcolors,horizontal=True,show_points=True);ax.axvline(0,c='.5',lw=.6);ax.set_xlabel('Strong − ordinary La Niña yield (pp)');title(ax,'c','Wheat: strength responses vary within groups')
ax=axs[1,1];d=read('factor_display');arr=np.array([d[(d.crop==c)&d.phase.eq(p)].set_index('factor').loc[factors,'RI'].values for c in C for p in ['EN','LN']]);ax.imshow(arr,cmap='Blues',vmin=0,vmax=60,aspect='auto')
ax.set(xticks=range(5),xticklabels=factor_names,yticks=range(8),yticklabels=[n+' · '+p for n in names for p in ['El Niño','La Niña']]);plt.setp(ax.get_xticklabels(),rotation=0,ha='center',fontsize=5.6);title(ax,'d','Historical model: weather shares (%)')
for i in range(8):
    for j in range(5):ax.text(j,i,f'{arr[i,j]:.0f}',ha='center',va='center',fontsize=5.8,color='white' if arr[i,j]>35 else '.15')
g=read('factor_changes');ax=axs[2,0];change=np.array([g[(g.crop==c)&g.weight.eq('EQUAL_SYSTEM')].set_index('factor').loc[factors,'DeltaRI'].values for c in C]);ax.imshow(change,cmap='PuOr',vmin=-7,vmax=7,aspect='auto')
ax.set(xticks=range(5),xticklabels=factor_names,yticks=range(4),yticklabels=names);plt.setp(ax.get_xticklabels(),rotation=0,ha='center',fontsize=5.6);title(ax,'e','Contribution-share changes (pp)\n2002–2022 minus 1984–2001')
for i in range(4):
    for j in range(5):ax.text(j,i,f'{change[i,j]:+.1f}',ha='center',va='center',fontsize=6,color='white' if abs(change[i,j])>4.7 else '.15')
ax=axs[2,1];h=g[(g.crop=='SOY')&g.factor.isin(['VPD','SM'])]
for j,factor in enumerate(['VPD','SM']):
    z=h[h.factor.eq(factor)].set_index('weight');v=z.loc[['EQUAL_SYSTEM','FIXED_PRODUCTION'],'DeltaRI'].to_numpy()
    ax.plot(v,[1-j,1-j],c='.6',lw=.8);ax.plot(v[0],1-j,marker='o',ms=4,mfc='white',mec='.2',ls='');ax.plot(v[1],1-j,marker='D',ms=4,c='.2',ls='')
ax.axvline(0,c='.65',lw=.6);ax.set(yticks=[1,0],yticklabels=['Atmospheric\ndryness (VPD)','Soil moisture'],xlabel='Contribution-share change (pp)',xlim=(-6.5,7),ylim=(-.8,1.55))
ax.legend(handles=[plt.Line2D([],[],marker='o',ls='',mfc='white',mec='.2',ms=3.5,label='Equal countries'),plt.Line2D([],[],marker='D',ls='',c='.2',ms=3.5,label='Fixed production weights')],fontsize=5.4,frameon=False,loc='lower left',bbox_to_anchor=(0,-.02),ncol=1)
title(ax,'f','Soybean: opposite VPD share changes')
w=read('wheat_display');country=read('DISPLAY_FIG3_G_COUNTRY51');ax=axs[3,0]
arrays=[country.loc[country.cluster.eq(k),'DeltaD'].values for k in [1,2]]
boxes(ax,arrays,['Cooler / less\nirrigated (25)','Warmer /\ndrier (26)'],envcolors,horizontal=True,show_points=True)
ax.axvline(0,c='.65',lw=.6);ax.set_xlabel('2002–2022 minus 1984–2001\nVPD–soil-moisture share gap (pp)');title(ax,'g','Wheat: changes within each environment')
ax=axs[3,1]
for i,(field,lab) in enumerate([('strong_minus_ordinary_Y_source','Observed yield'),('strong_minus_ordinary_weather_signed','Five-weather contribution'),('strong_minus_ordinary_prediction_Y','Full historical model')]):
    ax.bar(np.arange(2)+(i-1)*.22,w[field],width=.20,color=models[lab][0],label=lab)
ax.axhline(0,c='.5',lw=.6);ax.set(xticks=[0,1],xticklabels=['Cooler / less\nirrigated (25)','Warmer /\ndrier (26)'],ylabel='Strong − ordinary La Niña (pp)');ax.legend(fontsize=5.6,frameon=False,loc='upper right');title(ax,'h','Wheat: stronger-event yields still differ')
save(fig,axs,3)

# Fig5 preserves the coherent accounting and examples; abbreviations move to Methods.
fig,axs=grid(3,190/25.4);p=read('Figure5_MAJOR150')
ax=axs[0,0];bubbles=read('DISPLAY_FIG5_A_BUBBLES');selected=bubbles.low_producers.ge(2)
for take in [False,True]:
    z=bubbles[selected.eq(take)]
    ax.scatter(z.low_producers,z.high_producers,s=5*z.groups,c='#0072B2' if take else 'white',alpha=.55 if take else .8,edgecolors='white' if take else '.6',linewidths=.3 if take else .55)
ax.set(xlabel='Low-yield producers (yield ≤ −2%)',ylabel='High-yield producers (yield ≥ +2%)');title(ax,'a','Coexisting low and high yields')
ax.legend(handles=[ax.scatter([],[],s=5*n,c='#0072B2',alpha=.55,label=str(n)) for n in [1,5,10]],title='Groups per bubble',title_fontsize=5.6,fontsize=5.6,frameon=False,loc='upper left',labelspacing=.4)
ax.text(.585,.98,'≥2 low-yield producers: 79/150\n≥1 high-yield producer: 61/79',transform=ax.transAxes,va='top',fontsize=5.6,linespacing=1.25)
ax=axs[0,1];selected=p.material_Y_down_N.ge(2)
for take in [False,True]:
    z=p[selected.eq(take)];ax.scatter(z.Y_common_pct,z.Q_common_pct,s=10,c='#0072B2' if take else 'white',alpha=.6 if take else .8,edgecolors='none' if take else '.7',linewidths=.5)
ax.plot([-50,50],[-50,50],'--',c='.6',lw=.6);ax.axhline(0,c='.65',lw=.6);ax.axvline(0,c='.65',lw=.6);ax.axhline(-2,c='.6',lw=.5,ls=':');ax.axvline(-2,c='.6',lw=.5,ls=':')
ax.set(xlabel='Yield contribution at fixed area (%)',ylabel='Reported production anomaly (%)');title(ax,'b','Coincident low yields and covered output')
ax.text(.035,.98,'Within the same 79 groups:\nYield contribution ≤−2%: 32/79\nReported production ≤−2%: 38/79',transform=ax.transAxes,va='top',fontsize=5.6,linespacing=1.25)
cases=read('production_cases')
for year,ax,label in [(1988,axs[1,0],'c'),(2000,axs[1,1],'d')]:
    z=cases[cases.harvest_year==year].iloc[0];vals=np.array([z.Y_contribution_t,z.A_including_interaction_t,z.raw_Q_minus_YA_t,z.Q_common_gap_t])/1e6
    ax.bar(range(4),vals,color=['#0072B2','#E69F00','#999999','#333333']);ax.axhline(0,c='.5',lw=.6);ax.set(xticks=range(4),xticklabels=['Yield\ncomponent','Area + yield\ninteraction','Reporting\ndifference','Reported\nproduction'],ylabel='Production difference\n(million tonnes)');ax.tick_params(axis='x',labelsize=5.8);title(ax,label,f'Maize {year}: {z.actual_world_coverage_pct:.1f}% world coverage')
ax=axs[2,0];z=read('crosscrop');ax.scatter(z.Y_a,z.Y_b,s=7,c='#0072B2',alpha=.35);ax.axhline(0,c='.65',lw=.6);ax.axvline(0,c='.65',lw=.6);ax.axhline(-2,c='.6',lw=.5,ls=':');ax.axvline(-2,c='.6',lw=.5,ls=':');ax.set(xlabel='First crop yield anomaly (%)',ylabel='Second crop yield anomaly (%)');title(ax,'e','271 crop pairs within the same country')
ax=axs[2,1];same=z[z.both_Y_down];ax.bar(['Both crops have\nlow production','Only one crop has\nlow production'],[int(same.both_Q_down.sum()),int(same.both_Y_down_but_only_one_Q_down.sum())],color=['#0072B2','#E69F00']);ax.set(ylabel='Pairs with low yields\nin both crops (n=45)');title(ax,'f','Production outcomes can diverge')
save(fig,axs,5)
print('Only Figures2/3/5 rendered by this entry point; Figure4 retained. All data and cohort definitions inherited.')
